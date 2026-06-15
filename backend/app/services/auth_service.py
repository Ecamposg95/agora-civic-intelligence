"""Authentication service: credential verification and token issuance."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import Token


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid and the account is usable."""
    user = db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token(user: User) -> Token:
    """Issue a JWT carrying tenant (org) and role claims."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.value,
            "org": user.organization_id,
        },
    )
    return Token(access_token=access_token, expires_in=expires_in)
