from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Requirement:
    """
    Represents a single business or functional requirement
    extracted from a source document.

    Requirement IDs are assigned by RARE and are independent
    of Test Case IDs.
    """

    requirement_id: str
    module: str
    requirement: str
    requirement_type: str
    priority: str

    source_document: Optional[str] = None
    source_reference: Optional[str] = None

    version: int = 1
    status: str = "ACTIVE"

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the requirement into a dictionary suitable
        for JSON persistence.
        """
        data = asdict(self)

        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Requirement":
        """
        Create a Requirement object from a dictionary.
        """

        data = dict(data)

        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(
                data["created_at"]
            )

        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(
                data["updated_at"]
            )

        return cls(**data)

    def create_new_version(
        self,
        *,
        module: Optional[str] = None,
        requirement: Optional[str] = None,
        requirement_type: Optional[str] = None,
        priority: Optional[str] = None,
        source_document: Optional[str] = None,
        source_reference: Optional[str] = None,
        status: str = "ACTIVE",
    ) -> "Requirement":
        """
        Create a new version of the requirement while preserving
        the same Requirement ID.
        """

        now = datetime.now()

        return Requirement(
            requirement_id=self.requirement_id,
            module=(
                module
                if module is not None
                else self.module
            ),
            requirement=(
                requirement
                if requirement is not None
                else self.requirement
            ),
            requirement_type=(
                requirement_type
                if requirement_type is not None
                else self.requirement_type
            ),
            priority=(
                priority
                if priority is not None
                else self.priority
            ),
            source_document=(
                source_document
                if source_document is not None
                else self.source_document
            ),
            source_reference=(
                source_reference
                if source_reference is not None
                else self.source_reference
            ),
            version=self.version + 1,
            status=status,
            created_at=self.created_at,
            updated_at=now,
        )

    def retire(self) -> "Requirement":
        """
        Create a new retired version of this requirement.
        """
        return self.create_new_version(
            status="RETIRED"
        )

    def activate(self) -> "Requirement":
        """
        Create a new active version of this requirement.
        """
        return self.create_new_version(
            status="ACTIVE"
        )

    def review(self) -> "Requirement":
        """
        Create a new version marked for review.
        """
        return self.create_new_version(
            status="REVIEW"
        )