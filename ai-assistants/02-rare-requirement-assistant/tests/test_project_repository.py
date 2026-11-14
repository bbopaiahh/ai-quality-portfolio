import json

import pytest

from repository.project_repository import ProjectRepository


def test_create_list_open_and_isolate_projects(tmp_path):
    repository = ProjectRepository(
        registry_path=tmp_path / "registry" / "projects.json",
        workspace_root=tmp_path / "workspaces",
    )

    first = repository.create_project("  Clinical Requirements  ", "v1")
    second = repository.create_project("Food Delivery")

    assert first.name == "Clinical Requirements"
    assert repository.get_project(first.project_id) == first
    assert [project.project_id for project in repository.list_projects()] == [
        first.project_id,
        second.project_id,
    ]
    assert repository.get_workspace_path(first.project_id) != (
        repository.get_workspace_path(second.project_id)
    )


def test_rejects_empty_and_duplicate_project_names(tmp_path):
    repository = ProjectRepository(
        registry_path=tmp_path / "projects.json",
        workspace_root=tmp_path / "workspaces",
    )
    repository.create_project("Quality Project")

    with pytest.raises(ValueError, match="cannot be empty"):
        repository.create_project("  ")
    with pytest.raises(ValueError, match="already exists"):
        repository.create_project("quality project")


def test_unknown_project_cannot_open_workspace(tmp_path):
    repository = ProjectRepository(
        registry_path=tmp_path / "projects.json",
        workspace_root=tmp_path / "workspaces",
    )

    with pytest.raises(KeyError, match="Unknown project"):
        repository.get_workspace_path("../../outside")


def test_invalid_registry_is_reported_without_overwrite(tmp_path):
    registry = tmp_path / "projects.json"
    registry.write_text("{invalid", encoding="utf-8")
    repository = ProjectRepository(
        registry_path=registry,
        workspace_root=tmp_path / "workspaces",
    )

    with pytest.raises(ValueError, match="not valid JSON"):
        repository.list_projects()
    assert registry.read_text(encoding="utf-8") == "{invalid"


def test_registry_contains_only_project_metadata(tmp_path):
    registry = tmp_path / "projects.json"
    repository = ProjectRepository(
        registry_path=registry,
        workspace_root=tmp_path / "workspaces",
    )
    project = repository.create_project("Generic Project")

    payload = json.loads(registry.read_text(encoding="utf-8"))
    assert payload[0]["project_id"] == project.project_id
    assert "industry" not in payload[0]


def test_repository_storage_paths_are_isolated_per_project(tmp_path):
    repository = ProjectRepository(
        registry_path=tmp_path / "projects.json",
        workspace_root=tmp_path / "workspaces",
    )
    first = repository.create_project("Project One")
    second = repository.create_project("Project Two")

    first_paths = repository.get_repository_storage_paths(first.project_id)
    second_paths = repository.get_repository_storage_paths(second.project_id)

    assert set(first_paths) == {"test_cases", "requirements", "traceability"}
    assert all(path.parent == repository.get_workspace_path(first.project_id) / "repositories"
               for path in first_paths.values())
    assert all(path not in second_paths.values() for path in first_paths.values())
    assert all(not path.exists() for path in first_paths.values())
