"""Read-only Neo4j connection helpers for ClimateKG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - exercised only when live KG commands are used without dependency.
    GraphDatabase = None  # type: ignore[assignment]


def load_env_file(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs without printing or overriding existing env vars."""
    env_path = Path(path)
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value


def _first_env(names: tuple[str, ...], *, allow_empty: bool = False) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value or (allow_empty and value is not None):
            return value
    return None


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str | None
    password: str | None
    database: str | None = None
    no_auth: bool = False

    @classmethod
    def from_env(cls) -> "Neo4jSettings":
        load_env_file()
        uri = _first_env(("NEO4J_URI", "CLIMATEKG_NEO4J_URI", "CLIMATEKG_URI", "GRAPH_URI", "DB_URI"))
        auth = os.getenv("NEO4J_AUTH")
        no_auth = bool(auth and auth.upper() in {"NO_AUTH", "NONE", "FALSE", "0"})
        user = _first_env(("NEO4J_USER", "NEO4J_USERNAME", "CLIMATEKG_NEO4J_USER", "CLIMATEKG_USER", "GRAPH_USER", "DB_USER"))
        password = _first_env(
            (
                "NEO4J_PASSWORD",
                "NEO4J_PASS",
                "NEO4J_PWD",
                "NEO4J_PASSWD",
                "CLIMATEKG_NEO4J_PASSWORD",
                "CLIMATEKG_PASSWORD",
                "GRAPH_PASSWORD",
                "DB_PASSWORD",
            ),
            allow_empty=True,
        )
        if auth and not no_auth and (not user or not password) and "/" in auth:
            auth_user, auth_password = auth.split("/", 1)
            user = user or auth_user
            password = password or auth_password
        database = _first_env(("NEO4J_DATABASE", "NEO4J_DB", "CLIMATEKG_NEO4J_DATABASE", "CLIMATEKG_DATABASE", "GRAPH_DATABASE", "DB_NAME")) or None
        required = (("NEO4J_URI", uri),) if no_auth else (("NEO4J_URI", uri), ("NEO4J_USER", user), ("NEO4J_PASSWORD", password))
        missing = [name for name, value in required if value is None]
        if missing:
            raise RuntimeError(f"Missing Neo4j environment variables: {', '.join(missing)}")
        return cls(uri=uri or "", user=user, password=password, database=database, no_auth=no_auth)


class ClimateKGClient:
    """Small read-only wrapper around the Neo4j Python driver."""

    def __init__(self, settings: Neo4jSettings | None = None) -> None:
        if GraphDatabase is None:
            raise RuntimeError("The 'neo4j' package is required for ClimateKG commands. Install project dependencies first.")
        self.settings = settings or Neo4jSettings.from_env()
        auth = None if self.settings.no_auth else (self.settings.user, self.settings.password)
        self._driver = GraphDatabase.driver(self.settings.uri, auth=auth)

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "ClimateKGClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def run_read(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._driver.session(database=self.settings.database) as session:
            result = session.execute_read(lambda tx: list(tx.run(query, parameters or {}).data()))
        return result

    def count_by_label(self, labels: Iterable[str]) -> list[dict[str, Any]]:
        rows = []
        for label in labels:
            query = f"MATCH (n:`{label}`) RETURN $label AS kg_node_label, count(n) AS count"
            rows.extend(self.run_read(query, {"label": label}))
        return rows

    def sample_nodes(self, label: str, limit: int = 5) -> list[dict[str, Any]]:
        query = f"""
        MATCH (n:`{label}`)
        RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties
        LIMIT $limit
        """
        return self.run_read(query, {"limit": limit})

    def export_nodes(self, label: str) -> list[dict[str, Any]]:
        query = f"""
        MATCH (n:`{label}`)
        RETURN elementId(n) AS kg_entity_id, labels(n) AS labels, properties(n) AS properties
        """
        return self.run_read(query)
