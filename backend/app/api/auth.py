"""Auth routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..api.deps import audit_log, get_current_user, get_workspace
from ..core.db import get_db
from ..core.security import create_access_token, hash_password, verify_password
from ..models import User
from ..schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut, WorkspaceOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), name=payload.name)
    db.add(user)
    db.flush()
    workspace = get_workspace(user, db)
    token = create_access_token(user.id)
    audit_log(db, user, workspace, "auth.register")
    db.commit()
    return AuthResponse(token=token, user=UserOut.model_validate(user),
                        workspace=WorkspaceOut.model_validate(workspace))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    workspace = get_workspace(user, db)
    token = create_access_token(user.id)
    audit_log(db, user, workspace, "auth.login", ip=request.client.host if request.client else None)
    db.commit()
    return AuthResponse(token=token, user=UserOut.model_validate(user),
                        workspace=WorkspaceOut.model_validate(workspace))


@router.get("/me", response_model=AuthResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_workspace(user, db)
    return AuthResponse(token="", user=UserOut.model_validate(user),
                        workspace=WorkspaceOut.model_validate(workspace))
