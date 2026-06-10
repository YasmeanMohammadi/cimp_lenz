"""Document JSON model helpers for parsed PDF output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"page_number": self.page_number, "text": self.text}


@dataclass(frozen=True)
class EvidenceSentence:
    sentence_id: str
    page_number: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"sentence_id": self.sentence_id, "page_number": self.page_number, "text": self.text}


@dataclass(frozen=True)
class ParserMetadata:
    parser_name: str
    parser_version: str | None
    parsed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "parsed_at": self.parsed_at,
        }


@dataclass(frozen=True)
class ParsedDocument:
    pdf_number: str
    paper: dict[str, Any]
    paper_id: str
    pdf_hash: str
    source_pdf_path: str
    pages: list[ParsedPage]
    sentences: list[EvidenceSentence]
    parser_metadata: ParserMetadata
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdf_number": self.pdf_number,
            "paper": self.paper,
            "paper_id": self.paper_id,
            "pdf_hash": self.pdf_hash,
            "source_pdf_path": self.source_pdf_path,
            "pages": [page.to_dict() for page in self.pages],
            "sentences": [sentence.to_dict() for sentence in self.sentences],
            "parser_metadata": self.parser_metadata.to_dict(),
            "warnings": list(self.warnings),
        }
