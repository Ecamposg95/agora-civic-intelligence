"""Authentication API schemas (Pydantic v2)."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenWithUser(Token):
    user: UserRead
