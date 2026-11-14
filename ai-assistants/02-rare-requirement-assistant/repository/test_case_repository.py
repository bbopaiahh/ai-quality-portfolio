import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.test_case import TestCase


class TestCaseRepository:
    """
    Local repository for storing and retrieving RARE test cases.

    The current implementation uses a JSON file as the
    persistence layer.

    This keeps the repository simple while the RARE core
    workflow is being implemented. The storage mechanism
    can later be replaced by SQLite or another database
    without changing the TestCase model.
    """

    REQUIRED_FIELDS = (
        "test_case_id",
        "module",
        "scenario",
        "test_steps",
        "expected_result",
        "priority",
        "test_type",
        "suite_type",
        "automation_type",
    )

    def __init__(
        self,
        storage_path: str = "data/test_case_repository.json",
    ):
        self.storage_path = Path(storage_path)

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.storage_path.exists():
            self._write_data([])

    def save(self, test_case: TestCase) -> TestCase:
        """
        Save a new test case.

        Raises:
            ValueError:
                If the Test Case ID already exists.
        """

        test_cases = self._read_data()

        existing = self.get_by_id(
            test_case.test_case_id
        )

        if existing is not None:
            raise ValueError(
                f"Test Case ID already exists: "
                f"{test_case.test_case_id}"
            )

        test_cases.append(
            test_case.to_dict()
        )

        self._write_data(test_cases)

        return test_case

    def save_many(
        self,
        test_cases: List[TestCase],
    ) -> List[TestCase]:
        """
        Save multiple test cases.

        The operation validates duplicate IDs before
        modifying the repository.
        """

        if not test_cases:
            return []

        existing_cases = self._read_data()

        existing_ids = {
            case["test_case_id"]
            for case in existing_cases
        }

        incoming_ids = set()

        for test_case in test_cases:

            test_case_id = test_case.test_case_id

            if test_case_id in existing_ids:
                raise ValueError(
                    f"Test Case ID already exists: "
                    f"{test_case_id}"
                )

            if test_case_id in incoming_ids:
                raise ValueError(
                    f"Duplicate Test Case ID in "
                    f"batch: {test_case_id}"
                )

            incoming_ids.add(test_case_id)

        existing_cases.extend(
            test_case.to_dict()
            for test_case in test_cases
        )

        self._write_data(existing_cases)

        return test_cases

    def get_by_id(
        self,
        test_case_id: str,
    ) -> Optional[TestCase]:
        """
        Retrieve the latest stored version of a test case
        using its stable Test Case ID.
        """

        test_cases = self._read_data()

        matching_cases = [
            case
            for case in test_cases
            if case.get("test_case_id") == test_case_id
        ]

        if not matching_cases:
            return None

        latest_case = max(
            matching_cases,
            key=lambda case: case.get("version", 1),
        )

        return TestCase.from_dict(
            latest_case
        )

    def get_all(self) -> List[TestCase]:
        """
        Retrieve all stored test cases.

        Only the latest version of each Test Case ID
        is returned.
        """

        test_cases = self._read_data()

        latest_versions = {}

        for case in test_cases:

            test_case_id = case["test_case_id"]
            version = case.get("version", 1)
            existing = latest_versions.get(test_case_id)

            if (
                existing is None
                or version > existing.get("version", 1)
            ):
                latest_versions[test_case_id] = case

        return [
            TestCase.from_dict(case)
            for case in latest_versions.values()
        ]

    def search(
        self,
        query: str,
    ) -> List[TestCase]:
        """
        Search test cases by Test Case ID, module,
        scenario, requirement reference, or source document.
        """

        if not query or not query.strip():
            return self.get_all()

        query = query.strip().lower()

        results = []

        for test_case in self.get_all():

            searchable_values = [
                test_case.test_case_id,
                test_case.module,
                test_case.scenario,
                test_case.requirement_reference,
                test_case.source_document,
            ]

            searchable_text = " ".join(
                str(value or "")
                for value in searchable_values
            ).lower()

            if query in searchable_text:
                results.append(test_case)

        return results

    def update(
        self,
        test_case: TestCase,
    ) -> TestCase:
        """
        Store the next sequential version of an existing test case.

        The stable Test Case ID must already exist, and the incoming
        version must be exactly one greater than the latest stored
        version. This prevents duplicate, skipped, and stale versions
        from being appended to the repository.

        Raises:
            ValueError: If the ID does not exist or the version is not
                the next sequential version.
        """

        if (
            isinstance(test_case.version, bool)
            or not isinstance(test_case.version, int)
            or test_case.version < 1
        ):
            raise ValueError(
                "Test Case version must be a positive integer."
            )

        test_cases = self._read_data()

        matching_cases = [
            case
            for case in test_cases
            if case.get("test_case_id") == test_case.test_case_id
        ]

        if not matching_cases:
            raise ValueError(
                f"Test Case ID not found: "
                f"{test_case.test_case_id}"
            )

        latest_version = max(
            case.get("version", 1)
            for case in matching_cases
        )
        expected_version = latest_version + 1

        if test_case.version != expected_version:
            raise ValueError(
                f"Invalid version for Test Case ID "
                f"{test_case.test_case_id}: expected version "
                f"{expected_version}, received version "
                f"{test_case.version}."
            )

        test_cases.append(test_case.to_dict())
        self._write_data(test_cases)

        return test_case

    def delete(
        self,
        test_case_id: str,
    ) -> None:
        """
        Permanently remove all stored versions of a
        Test Case ID.

        This operation should be used carefully.

        Normal RARE workflow should prefer RETIRED status
        instead of permanent deletion.
        """

        test_cases = self._read_data()

        remaining_cases = [
            case
            for case in test_cases
            if case.get("test_case_id")
            != test_case_id
        ]

        if len(remaining_cases) == len(test_cases):
            raise ValueError(
                f"Test Case ID not found: "
                f"{test_case_id}"
            )

        self._write_data(
            remaining_cases
        )

    def clear(self) -> None:
        """
        Remove all repository data.

        Intended primarily for development and testing.
        """

        self._write_data([])

    def count(self) -> int:
        """
        Return the total number of test case records
        stored in the repository, including historical
        versions.
        """

        return len(
            self._read_data()
        )

    def _read_data(self) -> list:
        """
        Read and validate repository data from JSON.

        Legacy records may omit fields that the TestCase model
        supplies defaults for, including version, status,
        pre_condition, requirement_reference, source_document,
        created_at, and updated_at.
        """

        if not self.storage_path.exists():
            return []

        try:
            with self.storage_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError(
                "Test Case Repository contains invalid JSON "
                "or is not valid UTF-8."
            ) from exc

        if not isinstance(data, list):
            raise RuntimeError(
                "Test Case Repository must contain a JSON list."
            )

        self._validate_records(data)
        return data

    def _validate_records(self, records: list) -> None:
        """
        Reject malformed records and inconsistent version history.

        Validation is read-only: invalid records are never repaired,
        skipped, deleted, or rewritten automatically.
        """

        versions_by_id = {}

        for index, record in enumerate(records):
            location = f"record at index {index}"

            if not isinstance(record, dict):
                raise RuntimeError(
                    f"Invalid Test Case Repository: {location} "
                    "must be a JSON object."
                )

            missing_fields = [
                field
                for field in self.REQUIRED_FIELDS
                if field not in record
            ]
            if missing_fields:
                raise RuntimeError(
                    f"Invalid Test Case Repository: {location} "
                    f"is missing required field(s): "
                    f"{', '.join(missing_fields)}."
                )

            for field in self.REQUIRED_FIELDS:
                value = record[field]
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"Invalid Test Case Repository: {location} "
                        f"has an invalid required field '{field}'; "
                        "a non-empty string is required."
                    )

            test_case_id = record["test_case_id"]

            # Missing version is a supported legacy representation of v1.
            version = record.get("version", 1)
            if (
                isinstance(version, bool)
                or not isinstance(version, int)
                or version < 1
            ):
                raise RuntimeError(
                    f"Invalid Test Case Repository: {location} "
                    f"for Test Case ID '{test_case_id}' has invalid "
                    f"version {version!r}; a positive integer is required."
                )

            for timestamp_field in ("created_at", "updated_at"):
                timestamp = record.get(timestamp_field)

                # Missing/null timestamps retain the model's existing defaults.
                if timestamp is None:
                    continue

                if not isinstance(timestamp, str):
                    raise RuntimeError(
                        f"Invalid Test Case Repository: {location} "
                        f"for Test Case ID '{test_case_id}' has a "
                        f"non-string '{timestamp_field}' timestamp."
                    )

                try:
                    datetime.fromisoformat(timestamp)
                except ValueError as exc:
                    raise RuntimeError(
                        f"Invalid Test Case Repository: {location} "
                        f"for Test Case ID '{test_case_id}' has malformed "
                        f"'{timestamp_field}' timestamp {timestamp!r}."
                    ) from exc

            versions_by_id.setdefault(test_case_id, []).append(version)

        for test_case_id, versions in versions_by_id.items():
            unique_versions = set(versions)

            if len(unique_versions) != len(versions):
                duplicates = sorted(
                    version
                    for version in unique_versions
                    if versions.count(version) > 1
                )
                raise RuntimeError(
                    f"Invalid Test Case Repository: Test Case ID "
                    f"'{test_case_id}' has duplicate historical version(s): "
                    f"{duplicates}."
                )

            expected_versions = set(range(1, len(versions) + 1))
            if unique_versions != expected_versions:
                ordered_versions = sorted(versions)
                raise RuntimeError(
                    f"Invalid Test Case Repository: Test Case ID "
                    f"'{test_case_id}' has non-sequential history "
                    f"{ordered_versions}; expected versions "
                    f"1 through {len(versions)} with no gaps."
                )

    def _write_data(
        self,
        data: list,
    ) -> None:
        """
        Write repository data to JSON.
        """

        temporary_path = None

        try:
            # Keep the temporary file beside the repository file so the
            # final replacement happens on the same filesystem.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.storage_path.parent,
                prefix=f".{self.storage_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(
                    data,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )
                file.flush()
                os.fsync(file.fileno())

            # Publish the new JSON only after it has been written completely.
            os.replace(temporary_path, self.storage_path)
            temporary_path = None

        finally:
            # On a failed write, keep the old repository and remove the temp.
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
