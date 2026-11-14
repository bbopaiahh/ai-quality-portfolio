import json
from pathlib import Path
from typing import List, Optional

from models.requirement import Requirement


class RequirementRepository:
    """
    Persistent repository for Requirement objects.

    Requirements are stored in JSON format.

    The repository keeps historical versions while exposing
    the latest version of each Requirement ID through get_all()
    and get_by_id().
    """

    DEFAULT_STORAGE_PATH = (
        "data/requirement_repository.json"
    )

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
    ):
        self.storage_path = Path(storage_path)

        self._ensure_storage()

    def save(
        self,
        requirement: Requirement,
    ) -> Requirement:
        """
        Save a completely new Requirement.

        A Requirement ID must not already exist.
        Use save_version() when storing a new version.
        """

        if not isinstance(requirement, Requirement):
            raise TypeError(
                "requirement must be a Requirement instance."
            )

        requirements = self._load()

        existing = [
            item
            for item in requirements
            if item.requirement_id
            == requirement.requirement_id
        ]

        if existing:
            raise ValueError(
                f"Requirement ID already exists: "
                f"{requirement.requirement_id}"
            )

        requirements.append(requirement)

        self._save_all(requirements)

        return requirement

    def save_many(
        self,
        requirements: List[Requirement],
    ) -> List[Requirement]:
        """
        Save multiple completely new Requirements.

        The operation is atomic from the repository perspective:
        validation is performed before anything is written.
        """

        if not requirements:
            return []

        for requirement in requirements:
            if not isinstance(
                requirement,
                Requirement,
            ):
                raise TypeError(
                    "All items must be Requirement instances."
                )

        existing_requirements = self._load()

        existing_ids = {
            requirement.requirement_id
            for requirement in existing_requirements
        }

        incoming_ids = set()

        for requirement in requirements:
            requirement_id = requirement.requirement_id

            if requirement_id in existing_ids:
                raise ValueError(
                    f"Requirement ID already exists: "
                    f"{requirement_id}"
                )

            if requirement_id in incoming_ids:
                raise ValueError(
                    f"Duplicate Requirement ID in input: "
                    f"{requirement_id}"
                )

            incoming_ids.add(requirement_id)

        existing_requirements.extend(requirements)

        self._save_all(existing_requirements)

        return requirements

    def save_version(
        self,
        requirement: Requirement,
    ) -> Requirement:
        """
        Save a new version of an existing Requirement.

        The Requirement ID must already exist.

        The new version must be exactly one greater than
        the latest stored version.
        """

        if not isinstance(requirement, Requirement):
            raise TypeError(
                "requirement must be a Requirement instance."
            )

        requirements = self._load()

        matching = [
            item
            for item in requirements
            if item.requirement_id
            == requirement.requirement_id
        ]

        if not matching:
            raise ValueError(
                "Cannot create a new version for a "
                "Requirement ID that does not exist: "
                f"{requirement.requirement_id}"
            )

        latest_version = max(
            item.version
            for item in matching
        )

        expected_version = latest_version + 1

        if requirement.version != expected_version:
            raise ValueError(
                "Invalid requirement version. "
                f"Expected v{expected_version}, "
                f"received v{requirement.version}."
            )

        requirements.append(requirement)

        self._save_all(requirements)

        return requirement

    def get_by_id(
        self,
        requirement_id: str,
    ) -> Optional[Requirement]:
        """
        Return the latest version of a Requirement by ID.
        """

        requirements = self._load()

        matching = [
            requirement
            for requirement in requirements
            if requirement.requirement_id
            == requirement_id
        ]

        if not matching:
            return None

        return max(
            matching,
            key=lambda requirement: requirement.version,
        )

    def get_all(self) -> List[Requirement]:
        """
        Return the latest version of every Requirement ID.

        Historical versions remain stored internally but are not
        returned by this method.
        """

        requirements = self._load()

        latest = {}

        for requirement in requirements:
            requirement_id = requirement.requirement_id

            current = latest.get(requirement_id)

            if (
                current is None
                or requirement.version > current.version
            ):
                latest[requirement_id] = requirement

        return list(latest.values())

    def get_history(
        self,
        requirement_id: str,
    ) -> List[Requirement]:
        """
        Return all stored versions of a Requirement ID.
        """

        requirements = self._load()

        history = [
            requirement
            for requirement in requirements
            if requirement.requirement_id
            == requirement_id
        ]

        return sorted(
            history,
            key=lambda requirement: requirement.version,
        )

    def search(
        self,
        query: str,
    ) -> List[Requirement]:
        """
        Search the latest Requirement versions.

        Search covers:
        - Requirement ID
        - Module
        - Requirement text
        - Requirement type
        - Priority
        - Source document
        - Source reference
        - Status
        """

        if not query or not query.strip():
            return self.get_all()

        search_text = query.strip().casefold()

        results = []

        for requirement in self.get_all():

            searchable_values = [
                requirement.requirement_id,
                requirement.module,
                requirement.requirement,
                requirement.requirement_type,
                requirement.priority,
                requirement.source_document,
                requirement.source_reference,
                requirement.status,
            ]

            searchable_text = " ".join(
                str(value or "")
                for value in searchable_values
            ).casefold()

            if search_text in searchable_text:
                results.append(requirement)

        return results

    def update(
        self,
        requirement: Requirement,
    ) -> Requirement:
        """
        Replace an already stored Requirement version.

        This method does not automatically increment the version.
        Use save_version() when creating a new version.
        """

        if not isinstance(requirement, Requirement):
            raise TypeError(
                "requirement must be a Requirement instance."
            )

        requirements = self._load()

        target_index = None

        for index, existing in enumerate(requirements):
            if (
                existing.requirement_id
                == requirement.requirement_id
                and existing.version
                == requirement.version
            ):
                target_index = index
                break

        if target_index is None:
            raise ValueError(
                "Requirement version not found: "
                f"{requirement.requirement_id} "
                f"v{requirement.version}"
            )

        requirements[target_index] = requirement

        self._save_all(requirements)

        return requirement

    def delete(
        self,
        requirement_id: str,
    ) -> bool:
        """
        Delete all stored versions of a Requirement ID.

        Returns True when at least one record was removed.
        """

        requirements = self._load()

        filtered = [
            requirement
            for requirement in requirements
            if requirement.requirement_id
            != requirement_id
        ]

        if len(filtered) == len(requirements):
            return False

        self._save_all(filtered)

        return True

    def clear(self) -> None:
        """
        Remove all Requirement records.
        """

        self._save_all([])

    def count(self) -> int:
        """
        Return the number of stored Requirement records,
        including historical versions.
        """

        return len(self._load())

    def active_count(self) -> int:
        """
        Return the number of latest active Requirements.
        """

        return sum(
            1
            for requirement in self.get_all()
            if requirement.status == "ACTIVE"
        )

    def _ensure_storage(self) -> None:
        """
        Ensure the repository directory and JSON storage file exist.
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

    def _load(self) -> List[Requirement]:
        """
        Load all Requirement records from JSON storage.
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
                "Requirement repository contains invalid JSON."
            ) from exc

        if not isinstance(data, list):
            raise RuntimeError(
                "Requirement repository must contain a JSON list."
            )

        return [
            Requirement.from_dict(item)
            for item in data
        ]

    def _save_all(
        self,
        requirements: List[Requirement],
    ) -> None:
        """
        Persist all Requirement records to JSON.
        """

        self._ensure_storage()

        data = [
            requirement.to_dict()
            for requirement in requirements
        ]

        self.storage_path.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )