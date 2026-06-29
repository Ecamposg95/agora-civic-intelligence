"""Privacy notice schemas (Pydantic v2) — SPA-4 AC-7.2."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PrivacyNoticeCreate(BaseModel):
    """Payload to create a new versioned aviso de privacidad."""

    organization_id: Optional[str] = Field(
        default=None,
        description="NULL = global (platform-level) notice; set to restrict to a tenant.",
    )
    version: str = Field(max_length=40)
    body: str = Field(min_length=1)
    is_active: bool = True


class PrivacyNoticeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str]
    version: str
    body: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PrivacyAcceptanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    registro_id: str
    notice_id: str
    aviso_version: str
    accepted_at: datetime
