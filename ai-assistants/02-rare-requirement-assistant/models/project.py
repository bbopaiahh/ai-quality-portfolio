"""Domain-neutral project workspace metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Project:
    """A workspace that owns its documents and QA repositories."""

    project_id: str
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "ACTIVE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            project_id=str(data["project_id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            status=str(data.get("status", "ACTIVE")),
        )
