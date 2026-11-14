import json
from pathlib import Path
from typing import List, Optional

from models.traceability import Traceability


class TraceabilityRepository:
    """
    Persistent repository for Requirement ↔ Test Case
    traceability records.

    Each traceability record represents a relationship between
    one Requirement ID and one Test Case ID.

    Data is stored in JSON format.
    """

    DEFAULT_STORAGE_PATH = (
        "data/traceability_repository.json"
    )

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
    ):
        self.storage_path = Path(storage_path)

        self._ensure_storage()

    def save(
        self,
        traceability: Traceability,
    ) -> Traceability:
        """
        Save a new traceability relationship.

        Duplicate Requirement ID + Test Case ID mappings
        are rejected.
        """

        self._validate_traceability(traceability)

        records = self._load()

        duplicate = any(
            (
                record.requirement_id
                == traceability.requirement_id
                and record.test_case_id
                == traceability.test_case_id
            )
            for record in records
        )

        if duplicate:
            raise ValueError(
                "Traceability mapping already exists: "
                f"{traceability.requirement_id} -> "
                f"{traceability.test_case_id}"
            )

        records.append(traceability)

        self._save_all(records)

        return traceability

    def save_many(
        self,
        traceabilities: List[Traceability],
    ) -> List[Traceability]:
        """
        Save multiple traceability relationships.

        The operation validates all incoming records before
        persisting them.
        """

        if not traceabilities:
            return []

        for traceability in traceabilities:
            self._validate_traceability(traceability)

        existing_records = self._load()

        existing_pairs = {
            (
                record.requirement_id,
                record.test_case_id,
            )
            for record in existing_records
        }

        incoming_pairs = set()

        for traceability in traceabilities:
            pair = (
                traceability.requirement_id,
                traceability.test_case_id,
            )

            if pair in existing_pairs:
                raise ValueError(
                    "Traceability mapping already exists: "
                    f"{pair[0]} -> {pair[1]}"
                )

            if pair in incoming_pairs:
                raise ValueError(
                    "Duplicate traceability mapping "
                    "in input: "
                    f"{pair[0]} -> {pair[1]}"
                )

            incoming_pairs.add(pair)

        existing_records.extend(traceabilities)

        self._save_all(existing_records)

        return traceabilities

    def get_all(self) -> List[Traceability]:
        """
        Return all traceability relationships.
        """

        return self._load()

    def get_by_requirement(
        self,
        requirement_id: str,
    ) -> List[Traceability]:
        """
        Return all traceability records for a Requirement ID.
        """

        records = self._load()

        return [
            record
            for record in records
            if record.requirement_id
            == requirement_id
        ]

    def get_by_test_case(
        self,
        test_case_id: str,
    ) -> List[Traceability]:
        """
        Return all traceability records for a Test Case ID.
        """

        records = self._load()

        return [
            record
            for record in records
            if record.test_case_id
            == test_case_id
        ]

    def get_mapping(
        self,
        requirement_id: str,
        test_case_id: str,
    ) -> Optional[Traceability]:
        """
        Return a specific Requirement ↔ Test Case mapping.

        Returns None when the mapping does not exist.
        """

        records = self._load()

        for record in records:
            if (
                record.requirement_id
                == requirement_id
                and record.test_case_id
                == test_case_id
            ):
                return record

        return None

    def search(
        self,
        query: str,
    ) -> List[Traceability]:
        """
        Search traceability records by:

        - Requirement ID
        - Test Case ID
        - Relationship Type
        - Status
        """

        if not query or not query.strip():
            return self.get_all()

        search_text = query.strip().casefold()

        results = []

        for record in self._load():

            searchable_values = [
                record.requirement_id,
                record.test_case_id,
                record.relationship_type,
                record.status,
            ]

            searchable_text = " ".join(
                str(value or "")
                for value in searchable_values
            ).casefold()

            if search_text in searchable_text:
                results.append(record)

        return results

    def update(
        self,
        traceability: Traceability,
    ) -> Traceability:
        """
        Update an existing traceability record.
        """

        self._validate_traceability(traceability)

        records = self._load()

        target_index = None

        for index, existing in enumerate(records):
            if (
                existing.requirement_id
                == traceability.requirement_id
                and existing.test_case_id
                == traceability.test_case_id
            ):
                target_index = index
                break

        if target_index is None:
            raise ValueError(
                "Traceability mapping not found: "
                f"{traceability.requirement_id} -> "
                f"{traceability.test_case_id}"
            )

        records[target_index] = traceability

        self._save_all(records)

        return traceability

    def delete(
        self,
        requirement_id: str,
        test_case_id: str,
    ) -> bool:
        """
        Delete a specific Requirement ↔ Test Case mapping.

        Returns True when a record was deleted.
        """

        records = self._load()

        filtered = [
            record
            for record in records
            if not (
                record.requirement_id
                == requirement_id
                and record.test_case_id
                == test_case_id
            )
        ]

        if len(filtered) == len(records):
            return False

        self._save_all(filtered)

        return True

    def delete_by_requirement(
        self,
        requirement_id: str,
    ) -> int:
        """
        Delete all mappings for a Requirement ID.

        Returns the number of deleted records.
        """

        records = self._load()

        filtered = [
            record
            for record in records
            if record.requirement_id
            != requirement_id
        ]

        deleted_count = (
            len(records) - len(filtered)
        )

        if deleted_count > 0:
            self._save_all(filtered)

        return deleted_count

    def delete_by_test_case(
        self,
        test_case_id: str,
    ) -> int:
        """
        Delete all mappings for a Test Case ID.

        Returns the number of deleted records.
        """

        records = self._load()

        filtered = [
            record
            for record in records
            if record.test_case_id
            != test_case_id
        ]

        deleted_count = (
            len(records) - len(filtered)
        )

        if deleted_count > 0:
            self._save_all(filtered)

        return deleted_count

    def count(self) -> int:
        """
        Return the total number of traceability records.
        """

        return len(self._load())

    def clear(self) -> None:
        """
        Remove all traceability records.
        """

        self._save_all([])

    def _validate_traceability(
        self,
        traceability: Traceability,
    ) -> None:
        """
        Validate that the supplied object is a Traceability
        instance.
        """

        if not isinstance(
            traceability,
            Traceability,
        ):
            raise TypeError(
                "traceability must be a Traceability instance."
            )

    def _ensure_storage(self) -> None:
        """
        Ensure the repository directory and JSON storage file
        exist.
        """

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.storage_path.exists():
            self.storage_path.write_text(
                "[]",
                encoding="utf-8",
            )

    def _load(self) -> List[Traceability]:
        """
        Load all traceability records from JSON storage.
        """

        self._ensure_storage()

        try:
            raw_content = self.storage_path.read_text(
                encoding="utf-8"
            )

            if not raw_content.strip():
                return []

            data = json.loads(raw_content)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Traceability repository contains invalid JSON."
            ) from exc

        if not isinstance(data, list):
            raise RuntimeError(
                "Traceability repository must contain "
                "a JSON list."
            )

        return [
            Traceability.from_dict(item)
            for item in data
        ]

    def _save_all(
        self,
        traceabilities: List[Traceability],
    ) -> None:
        """
        Persist all traceability records to JSON.
        """

        self._ensure_storage()

        data = [
            traceability.to_dict()
            for traceability in traceabilities
        ]

        self.storage_path.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )