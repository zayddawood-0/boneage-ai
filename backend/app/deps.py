"""Shared FastAPI dependencies: current user + role-based access control.

Enforces the permission matrix in docs/requirements.md#user-roles server-side
(FR-2) — never rely on the frontend to hide a button instead of this.
"""
from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.get(models.User, int(user_id))
    if user is None:
        raise credentials_error
    return user


def require_roles(*allowed_roles: str) -> Callable[..., models.User]:
    """Dependency factory: 403s unless `current_user.role` is one of `allowed_roles`.

    See the permission matrix in docs/requirements.md#user-roles — pass the
    exact roles allowed for a given endpoint/action.
    """

    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform this action.",
            )
        return current_user

    return dependency
