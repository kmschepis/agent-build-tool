from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

@dataclass
class Frontmatter:
    metadata: dict[str, Any]
    body: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(content: str) -> Frontmatter:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            _, raw_yaml, body = parts[0], parts[1], parts[2]
            import yaml

            metadata = yaml.safe_load(raw_yaml) or {}
            return Frontmatter(metadata=metadata, body=body.lstrip("\n"))
    return Frontmatter(metadata={}, body=content)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
