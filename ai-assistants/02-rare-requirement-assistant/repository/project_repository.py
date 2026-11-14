"""Local project registry and isolated workspace directory management."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from models.project import Project


PROJECT_REPOSITORY_FILES = {
    "test_cases": "test_case_repository.json",
    "requirements": "requirement_repository.json",
    "traceability": "traceability_repository.json",
}


class ProjectRepository:
    """Store project metadata and provide a contained directory per project.

    The repository is deliberately independent of the current requirement,
    test-case, and traceability repositories. App integration and migration of
    existing live JSON data are separate steps after this component is tested.
    """

    def __init__(
        self,
        registry_path: str | Path = "data/projects.json",
        workspace_root: str | Path | None = None,
    ) -> None:
        self.registry_path = Path(registry_path).resolve()
        self.workspace_root = Path(
            workspace_root
            if workspace_root is not None
            else self.registry_path.parent / "projects"
        ).resolve()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._write_projects([])

    def list_projects(self) -> list[Project]:
        return self._read_projects()

    def get_project(self, project_id: str) -> Project | None:
        return next(
            (project for project in self._read_projects()
             if project.project_id == project_id),
            None,
        )

    def create_project(
        self,
        name: str,
        description: str = "",
    ) -> Project:
        normalized_name = " ".join((name or "").split())
        if not normalized_name:
            raise ValueError("Project name cannot be empty.")

        projects = self._read_projects()
        if any(project.name.casefold() == normalized_name.casefold()
               for project in projects):
            raise ValueError("A project with this name already exists.")

        now = datetime.now(timezone.utc).isoformat()
        project = Project(
            project_id=str(uuid4()),
            name=normalized_name,
            description=(description or "").strip(),
            created_at=now,
            updated_at=now,
        )
        project_directory = self._project_directory(project.project_id)
        project_directory.mkdir(parents=False, exist_ok=False)
        self._write_projects([*projects, project])
        return project

    def get_workspace_path(self, project_id: str) -> Path:
        if self.get_project(project_id) is None:
            raise KeyError(f"Unknown project: {project_id}")
        path = self._project_directory(project_id)
        if not path.is_dir():
            raise FileNotFoundError(
                f"Workspace directory is missing for project {project_id}."
            )
        return path

    def get_repository_storage_paths(self, project_id: str) -> dict[str, Path]:
        """Return the project-owned JSON paths without touching the legacy data."""
        repository_directory = self.get_workspace_path(project_id) / "repositories"
        return {
            key: repository_directory / filename
            for key, filename in PROJECT_REPOSITORY_FILES.items()
        }

    def _project_directory(self, project_id: str) -> Path:
        # IDs are generated UUIDs; still reject path syntax at this boundary.
        if not project_id or Path(project_id).name != project_id:
            raise ValueError("Invalid project identifier.")
        path = (self.workspace_root / project_id).resolve()
        if path.parent != self.workspace_root:
            raise ValueError("Project workspace path escapes its configured root.")
        return path

    def _read_projects(self) -> list[Project]:
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Project registry is not valid JSON: {self.registry_path}"
            ) from exc
        if not isinstance(payload, list):
            raise ValueError("Project registry must contain a JSON list.")
        return [Project.from_dict(item) for item in payload]

    def _write_projects(self, projects: list[Project]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.registry_path.parent,
                prefix=f".{self.registry_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    [project.to_dict() for project in projects],
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.registry_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
