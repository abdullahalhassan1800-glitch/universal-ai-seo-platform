"""Websites routes (tenant-scoped CRUD)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import audit_log, get_current_user, get_current_workspace, get_website_access
from ..core.db import get_db
from ..models import Project, User, Website, Workspace
from ..schemas import WebsiteCreate, WebsiteOut, WebsiteUpdate

router = APIRouter(tags=["websites"])


@router.get("/websites", response_model=list[WebsiteOut])
def list_websites(workspace: Workspace = Depends(get_current_workspace), db: Session = Depends(get_db)):
    return (
        db.query(Website)
        .filter(Website.workspace_id == workspace.id)
        .order_by(Website.created_at)
        .all()
    )


@router.post("/websites", response_model=WebsiteOut, status_code=201)
def create_website(payload: WebsiteCreate, user: User = Depends(get_current_user),
                   workspace: Workspace = Depends(get_current_workspace), db: Session = Depends(get_db)):
    domain = payload.domain.strip().rstrip("/")
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"
    duplicate = db.query(Website).filter(Website.workspace_id == workspace.id, Website.domain == domain).first()
    if duplicate:
        raise HTTPException(409, "Website with this domain already exists")

    project = None
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if project is None or project.workspace_id != workspace.id:
            raise HTTPException(404, "Project not found")

    website = Website(
        workspace_id=workspace.id,
        project_id=project.id if project else None,
        name=payload.name.strip(),
        domain=domain,
    )
    db.add(website)
    db.flush()
    audit_log(db, user, workspace, "website.create", entity_type="website", entity_id=str(website.id))
    db.commit()
    db.refresh(website)
    return website


@router.get("/websites/{website_id}", response_model=WebsiteOut)
def get_website(website: Website = Depends(get_website_access)):
    return website


@router.patch("/websites/{website_id}", response_model=WebsiteOut)
def update_website(payload: WebsiteUpdate, user: User = Depends(get_current_user),
                   workspace: Workspace = Depends(get_current_workspace),
                   website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    if "domain" in changes and changes["domain"]:
        domain = changes["domain"].strip().rstrip("/")
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"
        changes["domain"] = domain
    for key, value in changes.items():
        setattr(website, key, value)
    db.add(website)
    db.flush()
    audit_log(db, user, workspace, "website.update", entity_type="website", entity_id=str(website.id))
    db.commit()
    db.refresh(website)
    return website


@router.delete("/websites/{website_id}", status_code=204)
def delete_website(user: User = Depends(get_current_user),
                   website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    db.delete(website)
    db.flush()
    audit_log(db, user, None, "website.delete", entity_type="website", entity_id=str(website.id))
    db.commit()
