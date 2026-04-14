"""Projects API router.

Manages functional-safety project lifecycle.  Each project has a
corresponding `AGENTS.md` memory file that the `MemoryMiddleware` loads
to give the agent project-level context.

持久化: 项目数据保存在 BASE_DIR/projects/projects.json，重启不丢失。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import BASE_DIR
from app.models.schemas import ProjectCreate, ProjectResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# JSON-file persistence (lightweight, no DB required for dev)
# ---------------------------------------------------------------------------

_STORE_PATH: Path = BASE_DIR / "projects" / "projects.json"


def _load_projects() -> dict[str, dict[str, Any]]:
    """Load projects from JSON file, return empty dict if missing."""
    if not _STORE_PATH.exists():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_projects(projects: dict[str, dict[str, Any]]) -> None:
    """Persist projects dict to JSON file."""
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(
        json.dumps(projects, ensure_ascii=False, default=str, indent=2),
        encoding="utf-8",
    )


# Load on startup
_projects: dict[str, dict[str, Any]] = _load_projects()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agents_md_path(project_id: str) -> Path:
    return BASE_DIR / "projects" / project_id / "AGENTS.md"


def _create_agents_md(project: dict[str, Any]) -> None:
    path = _agents_md_path(project["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Project: {project['name']}\n\n"
        f"## 项目背景\n"
        f"- 系统: {project['vehicle_system']}\n"
        f"- 描述: {project['description']}\n"
        f"- 适用标准: {project['iso_standard']}\n\n"
        f"## 约束条件\n"
        f"- 适用标准: {project['iso_standard']}\n\n"
        f"## 历史决策\n"
        f"- {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}: 项目创建\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ProjectResponse])
async def list_projects() -> list[ProjectResponse]:
    """Return all projects sorted by creation date descending."""
    return [
        ProjectResponse(**p)
        for p in sorted(_projects.values(), key=lambda x: x["created_at"], reverse=True)
    ]


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(payload: ProjectCreate) -> ProjectResponse:
    """Create a new project and generate its AGENTS.md memory file."""
    now = datetime.now(tz=timezone.utc)
    project: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "description": payload.description,
        "vehicle_system": payload.vehicle_system,
        "iso_standard": payload.iso_standard,
        "metadata": payload.metadata,
        "created_at": now,
        "updated_at": now,
        "analysis_count": 0,
    }
    _projects[project["id"]] = project
    _save_projects(_projects)
    _create_agents_md(project)
    return ProjectResponse(**project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    """Return a single project by ID."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return ProjectResponse(**project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """Delete a project and its associated AGENTS.md."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    agents_md = _agents_md_path(project_id)
    if agents_md.exists():
        agents_md.unlink()
    del _projects[project_id]
    _save_projects(_projects)
