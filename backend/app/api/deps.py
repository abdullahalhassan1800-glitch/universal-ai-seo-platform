"""FastAPI dependencies: auth, tenant isolation, entity access."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import decode_access_token
from ..models import User, Website, Workspace, WorkspaceMember

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_workspace(user: User, db: Session) -> Workspace:
    membership = (
        db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).order_by(WorkspaceMember.created_at).first()
    )
    if membership is not None:
        return db.get(Workspace, membership.workspace_id)
    workspace = Workspace(name=f"{user.name or user.email}'s workspace", plan="free")
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(workspace)
    return workspace


def get_current_workspace(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Workspace:
    return get_workspace(user, db)


def get_website_access(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Website:
    workspace = get_workspace(user, db)
    website = db.get(Website, website_id)
    if website is None or website.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Website not found")
    return website


def audit_log(db: Session, user: User | None, workspace: Workspace | None, action: str,
              entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None,
              ip: str | None = None) -> None:
    from ..models import AuditLog
    db.add(AuditLog(
        user_id=user.id if user else None,
        workspace_id=workspace.id if workspace else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip=ip,
    ))
