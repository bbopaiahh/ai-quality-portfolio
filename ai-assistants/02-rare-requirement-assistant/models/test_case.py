from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TestCase:
    """
    Represents a single test case in the RARE Test Case Repository.

    This model is the persistent representation of a generated
    Master Test Suite test case.
    """

    test_case_id: str
    module: str
    scenario: str
    test_steps: str
    expected_result: str
    priority: str
    test_type: str
    suite_type: str
    automation_type: str
    pre_condition: str = ""

    # Repository intelligence fields
    requirement_reference: Optional[str] = None
    version: int = 1
    status: str = "ACTIVE"

    # Repository metadata
    source_document: Optional[str] = None
    created_at: datetime = field(
        default_factory=datetime.now
    )
    updated_at: datetime = field(
        default_factory=datetime.now
    )

    def to_dict(self) -> dict:
        """
        Convert the test case into a dictionary.

        This representation will later be used by the
        repository/storage layer.
        """

        return {
            "test_case_id": self.test_case_id,
            "module": self.module,
            "scenario": self.scenario,
            "test_steps": self.test_steps,
            "expected_result": self.expected_result,
            "priority": self.priority,
            "test_type": self.test_type,
            "suite_type": self.suite_type,
            "automation_type": self.automation_type,
            "pre_condition": self.pre_condition,
            "requirement_reference": self.requirement_reference,
            "version": self.version,
            "status": self.status,
            "source_document": self.source_document,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "TestCase":
        """
        Create a TestCase object from a dictionary.

        This will be useful when reading test cases back
        from repository storage.
        """

        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(
                created_at
            )

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(
                updated_at
            )

        return cls(
            test_case_id=data["test_case_id"],
            module=data["module"],
            scenario=data["scenario"],
            test_steps=data["test_steps"],
            expected_result=data["expected_result"],
            priority=data["priority"],
            test_type=data["test_type"],
            suite_type=data["suite_type"],
            automation_type=data["automation_type"],
            pre_condition=data.get("pre_condition", ""),
            requirement_reference=data.get(
                "requirement_reference"
            ),
            version=int(
                data.get("version", 1)
            ),
            status=data.get(
                "status",
                "ACTIVE",
            ),
            source_document=data.get(
                "source_document"
            ),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )

    def create_new_version(
        self,
        **changes,
    ) -> "TestCase":
        """
        Create a new version of the current test case.

        The Test Case ID remains stable while the version
        number increases.

        Example:

            TC001 v1
                ↓
            TC001 v2
        """

        current_data = self.to_dict()

        current_data.update(changes)

        current_data["test_case_id"] = (
            self.test_case_id
        )

        current_data["version"] = (
            self.version + 1
        )

        current_data["created_at"] = (
            self.created_at.isoformat()
        )

        current_data["updated_at"] = (
            datetime.now().isoformat()
        )

        return TestCase.from_dict(
            current_data
        )

    def retire(self) -> "TestCase":
        """
        Create a new version marked as RETIRED.
        """

        return self.create_new_version(
            status="RETIRED"
        )

    def activate(self) -> "TestCase":
        """
        Create a new version marked as ACTIVE.
        """

        return self.create_new_version(
            status="ACTIVE"
        )

    def review(self) -> "TestCase":
        """
        Create a new version marked as REVIEW.
        """

        return self.create_new_version(
            status="REVIEW"
        )