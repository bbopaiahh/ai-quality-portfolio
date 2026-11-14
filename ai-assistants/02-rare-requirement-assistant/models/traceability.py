from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Traceability:
    """
    Represents a relationship between a Requirement
    and a Test Case.

    A single Traceability record answers:

        Which Test Case covers which Requirement?

    Example:

        REQ001 -> TC001
    """

    requirement_id: str
    test_case_id: str

    relationship_type: str = "COVERED"
    status: str = "ACTIVE"

    created_at: datetime = field(
        default_factory=datetime.now
    )

    updated_at: datetime = field(
        default_factory=datetime.now
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Traceability object into a dictionary
        suitable for JSON persistence.
        """

        data = asdict(self)

        data["created_at"] = (
            self.created_at.isoformat()
        )

        data["updated_at"] = (
            self.updated_at.isoformat()
        )

        return data

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "Traceability":
        """
        Create a Traceability object from a dictionary.
        """

        data = dict(data)

        if isinstance(
            data.get("created_at"),
            str,
        ):
            data["created_at"] = datetime.fromisoformat(
                data["created_at"]
            )

        if isinstance(
            data.get("updated_at"),
            str,
        ):
            data["updated_at"] = datetime.fromisoformat(
                data["updated_at"]
            )

        return cls(**data)

    def deactivate(self) -> "Traceability":
        """
        Create a copy of the mapping marked as inactive.
        """

        return Traceability(
            requirement_id=self.requirement_id,
            test_case_id=self.test_case_id,
            relationship_type=self.relationship_type,
            status="INACTIVE",
            created_at=self.created_at,
            updated_at=datetime.now(),
        )

    def activate(self) -> "Traceability":
        """
        Create a copy of the mapping marked as active.
        """

        return Traceability(
            requirement_id=self.requirement_id,
            test_case_id=self.test_case_id,
            relationship_type=self.relationship_type,
            status="ACTIVE",
            created_at=self.created_at,
            updated_at=datetime.now(),
        )

    def mark_for_review(self) -> "Traceability":
        """
        Create a copy of the mapping marked for review.
        """

        return Traceability(
            requirement_id=self.requirement_id,
            test_case_id=self.test_case_id,
            relationship_type=self.relationship_type,
            status="REVIEW",
            created_at=self.created_at,
            updated_at=datetime.now(),
        )