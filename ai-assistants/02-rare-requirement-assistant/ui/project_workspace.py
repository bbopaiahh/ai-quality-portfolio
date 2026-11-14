"""Streamlit controls for selecting a project-owned data workspace."""

from __future__ import annotations

import streamlit as st

from repository.project_repository import ProjectRepository


SELECTION_KEY = "rare_project_workspace_id"
PENDING_SELECTION_KEY = "rare_project_workspace_pending_id"
LEGACY_WORKSPACE_LABEL = "Current shared workspace"


def render_project_workspace_selector(
    project_repository: ProjectRepository,
) -> str | None:
    """Render the workspace selector and return its selected project ID.

    ``None`` deliberately means the existing shared workspace, preserving the
    application's current storage behavior unless a user selects a project.
    """
    try:
        projects = project_repository.list_projects()
    except (OSError, ValueError) as exc:
        st.sidebar.error(f"Project list unavailable: {exc}")
        return None

    project_names = {project.project_id: project.name for project in projects}

    pending_project_id = st.session_state.pop(PENDING_SELECTION_KEY, None)
    if pending_project_id in project_names:
        st.session_state[SELECTION_KEY] = pending_project_id

    selected_project_id = st.session_state.get(SELECTION_KEY)
    if selected_project_id is not None and selected_project_id not in project_names:
        st.session_state[SELECTION_KEY] = None

    with st.sidebar:
        st.subheader("Project workspace")
        st.selectbox(
            "Choose where this session stores its requirements and test cases",
            options=[None, *project_names],
            format_func=lambda project_id: (
                LEGACY_WORKSPACE_LABEL
                if project_id is None
                else project_names.get(project_id, "Unknown project")
            ),
            key=SELECTION_KEY,
        )

        with st.expander("Create a separate project"):
            with st.form("rare_create_project_form", clear_on_submit=True):
                project_name = st.text_input(
                    "Project name",
                    key="rare_new_project_name",
                )
                project_description = st.text_area(
                    "Description (optional)",
                    key="rare_new_project_description",
                )
                submitted = st.form_submit_button(
                    "Create project",
                    key="rare_create_project_submit",
                )

            if submitted:
                try:
                    project = project_repository.create_project(
                        project_name,
                        project_description,
                    )
                except (OSError, ValueError) as exc:
                    st.error(f"Could not create project: {exc}")
                else:
                    st.session_state[PENDING_SELECTION_KEY] = project.project_id
                    st.rerun()

    return st.session_state.get(SELECTION_KEY)
