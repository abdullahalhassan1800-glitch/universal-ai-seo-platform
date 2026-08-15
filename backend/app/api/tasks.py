"""SEO task routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import get_website_access
from ..core.db import get_db
from ..models import SeoTask, Website
from ..schemas import TaskOut, TaskStatusUpdate
from ..services import task_service

router = APIRouter(tags=["tasks"])

VALID_TRANSITIONS = {"pending", "approved", "rejected", "completed"}


@router.get("/websites/{website_id}/tasks", response_model=list[TaskOut])
def list_tasks(status: str | None = None, website: Website = Depends(get_website_access),
               db: Session = Depends(get_db)):
    query = db.query(SeoTask).filter(SeoTask.website_id == website.id)
    if status:
        query = query.filter(SeoTask.status == status)
    return query.order_by(SeoTask.priority).limit(500).all()


@router.post("/websites/{website_id}/tasks/prioritize", response_model=list[TaskOut])
def prioritize_tasks(website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    return task_service.apply_ai_priorities(db, website.id)


@router.patch("/websites/{website_id}/tasks/{task_id}", response_model=TaskOut)
def update_task_status(payload: TaskStatusUpdate, task_id: uuid.UUID,
                       website: Website = Depends(get_website_access), db: Session = Depends(get_db)):
    task = db.get(SeoTask, task_id)
    if task is None or task.website_id != website.id:
        raise HTTPException(404, "Task not found")
    if payload.status not in VALID_TRANSITIONS:
        raise HTTPException(422, f"Invalid status. Allowed: {sorted(VALID_TRANSITIONS)}")
    task.status = payload.status
    if payload.status == "completed":
        task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task
