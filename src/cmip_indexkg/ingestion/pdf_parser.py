"""PDF parsing into page-level text and sentence-level evidence chunks."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cmip_indexkg.evaluation.gold_schema import load_gold_jsonl
from cmip_indexkg.ingestion.document_model import EvidenceSentence, ParsedDocument, ParsedPage, ParserMetadata

_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")
_WHITESPACE_RE = re.compile(r"\s+")
MIN_TEXT_CHARS_WARNING = 500


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_extracted_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    """Split page text into conservative sentence-like evidence chunks."""
    normalized = normalize_extracted_text(text)
    if not normalized:
        return []
    parts = [part.strip() for part in _SENTENCE_END_RE.split(normalized) if part.strip()]
    sentences: list[str] = []
    for part in parts:
        # Keep very long extraction runs usable without table-aware parsing.
        if len(part) <= 1200:
            sentences.append(part)
            continue
        fragments = [frag.strip() for frag in re.split(r"\s{2,}|;\s+", part) if frag.strip()]
        sentences.extend(fragments or [part])
    return sentences


def make_sentence_id(page_number: int, sentence_number: int) -> str:
    return f"p{page_number}-s{sentence_number}"


def sentences_for_pages(pages: list[ParsedPage]) -> list[EvidenceSentence]:
    sentences: list[EvidenceSentence] = []
    for page in pages:
        for index, sentence_text in enumerate(split_sentences(page.text), start=1):
            sentences.append(
                EvidenceSentence(
                    sentence_id=make_sentence_id(page.page_number, index),
                    page_number=page.page_number,
                    text=sentence_text,
                )
            )
    return sentences


def resolve_pdf_path(local_pdf_path: str, gold_path: str | Path, repo_root: str | Path = ".") -> Path:
    """Resolve website-style local PDF paths without modifying gold records."""
    raw = Path(local_pdf_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        root = Path(repo_root)
        gold_parent = Path(gold_path).parent
        candidates.extend([
            root / raw,
            gold_parent / raw,
            gold_parent.parent / raw,
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else raw


def _load_fitz():
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency state.
        raise RuntimeError("PyMuPDF is unavailable") from exc
    return fitz


def _parse_pages_with_pymupdf(pdf_path: Path) -> tuple[list[ParsedPage], ParserMetadata]:
    fitz = _load_fitz()
    pages: list[ParsedPage] = []
    with fitz.open(pdf_path) as doc:
        for page_index in range(doc.page_count):
            page_number = page_index + 1
            text = doc.load_page(page_index).get_text("text")
            pages.append(ParsedPage(page_number=page_number, text=normalize_extracted_text(text)))
    metadata = ParserMetadata(
        parser_name="PyMuPDF",
        parser_version=getattr(fitz, "version", [None])[0] if getattr(fitz, "version", None) else None,
        parsed_at=datetime.now(timezone.utc).isoformat(),
    )
    return pages, metadata


def _parse_pages_with_pdftotext(pdf_path: Path) -> tuple[list[ParsedPage], ParserMetadata]:
    if shutil.which("pdftotext") is None:
        raise RuntimeError(
            "No PDF parser available. Install PyMuPDF with `python -m pip install -e '.[dev]'` "
            "or install Poppler `pdftotext`."
        )
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    raw_pages = result.stdout.split("\f")
    if raw_pages and not raw_pages[-1].strip():
        raw_pages = raw_pages[:-1]
    pages = [
        ParsedPage(page_number=index, text=normalize_extracted_text(text))
        for index, text in enumerate(raw_pages, start=1)
    ]
    metadata = ParserMetadata(
        parser_name="pdftotext",
        parser_version=None,
        parsed_at=datetime.now(timezone.utc).isoformat(),
    )
    return pages, metadata


def parse_pdf_record(record: dict[str, Any], gold_path: str | Path, repo_root: str | Path = ".") -> ParsedDocument:
    pdf_number = record["pdf_number"]
    paper = dict(record.get("paper") or {})
    local_pdf_path = paper.get("local_pdf_path")
    if not local_pdf_path:
        raise FileNotFoundError(f"pdf_number={pdf_number} has no paper.local_pdf_path")

    pdf_path = resolve_pdf_path(str(local_pdf_path), gold_path=gold_path, repo_root=repo_root)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found for pdf_number={pdf_number}: {pdf_path}")

    pdf_hash = compute_sha256(pdf_path)
    warnings: list[str] = []

    try:
        pages, parser_metadata = _parse_pages_with_pymupdf(pdf_path)
    except RuntimeError as exc:
        if str(exc) != "PyMuPDF is unavailable":
            raise
        pages, parser_metadata = _parse_pages_with_pdftotext(pdf_path)
        warnings.append("pymupdf_unavailable_used_pdftotext")

    for page in pages:
        if not page.text:
            warnings.append(f"empty_text_page:{page.page_number}")

    total_chars = sum(len(page.text) for page in pages)
    if total_chars < MIN_TEXT_CHARS_WARNING:
        warnings.append(f"very_short_extraction:{total_chars}_chars")

    sentences = sentences_for_pages(pages)
    return ParsedDocument(
        pdf_number=pdf_number,
        paper=paper,
        paper_id=f"sha256:{pdf_hash}",
        pdf_hash=pdf_hash,
        source_pdf_path=str(pdf_path),
        pages=pages,
        sentences=sentences,
        parser_metadata=parser_metadata,
        warnings=warnings,
    )


def write_parsed_document(document: ParsedDocument, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{document.pdf_number}.parsed.json"
    output_path.write_text(json.dumps(document.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def parse_gold_pdfs(gold_path: str | Path, output_dir: str | Path, summary_output: str | Path, repo_root: str | Path = ".") -> dict[str, Any]:
    records = load_gold_jsonl(gold_path)
    per_paper: list[dict[str, Any]] = []
    total_success = 0
    total_failed = 0

    for record in records:
        pdf_number = record["pdf_number"]
        paper = record.get("paper") or {}
        local_pdf_path = paper.get("local_pdf_path")
        resolved_path = resolve_pdf_path(str(local_pdf_path or ""), gold_path=gold_path, repo_root=repo_root) if local_pdf_path else None
        entry: dict[str, Any] = {
            "pdf_number": pdf_number,
            "source_pdf_path": str(resolved_path) if resolved_path else None,
            "output_path": None,
            "status": "failed",
            "page_count": 0,
            "sentence_count": 0,
            "warnings": [],
            "error": None,
        }
        try:
            if resolved_path is None or not resolved_path.exists():
                entry["warnings"].append("missing_pdf")
            document = parse_pdf_record(record, gold_path=gold_path, repo_root=repo_root)
            output_path = write_parsed_document(document, output_dir)
            entry.update({
                "output_path": str(output_path),
                "status": "parsed",
                "page_count": len(document.pages),
                "sentence_count": len(document.sentences),
                "warnings": document.warnings,
                "pdf_hash": document.pdf_hash,
            })
            total_success += 1
        except Exception as exc:  # Keep batch parsing going and summarize failures.
            entry["error"] = str(exc)
            if "missing_pdf" not in entry["warnings"] and isinstance(exc, FileNotFoundError):
                entry["warnings"].append("missing_pdf")
            total_failed += 1
        per_paper.append(entry)

    summary = {
        "total_papers_requested": len(records),
        "total_parsed_successfully": total_success,
        "total_failed": total_failed,
        "papers": per_paper,
    }
    summary_path = Path(summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
