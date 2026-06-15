"""Organization API schemas (Pydantic v2)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class OrganizationRead(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
