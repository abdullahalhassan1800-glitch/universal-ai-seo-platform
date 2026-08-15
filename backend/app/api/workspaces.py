"""Workspaces and projects routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import get_current_user, get_current_workspace
from ..core.db import get_db
from ..models import Project, User, Workspace
from ..schemas import ProjectCreate, ProjectOut, WorkspaceOut

router = APIRouter(tags=["workspaces"])


@router.get("/workspace", response_model=WorkspaceOut)
def get_my_workspace(workspace: Workspace = Depends(get_current_workspace)):
    return workspace


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(workspace: Workspace = Depends(get_current_workspace), db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.workspace_id == workspace.id).order_by(Project.created_at).all()


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, workspace: Workspace = Depends(get_current_workspace),
                   db: Session = Depends(get_db)):
    project = Project(workspace_id=workspace.id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, workspace: Workspace = Depends(get_current_workspace),
                   db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None or project.workspace_id != workspace.id:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
