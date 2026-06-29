"""Authentication API schemas (Pydantic v2)."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    # Accepts an email or a phone number. ``email`` kept as optional alias for
    # backward compatibility with the existing frontend payload.
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _accept_email_alias(cls, data):
        if isinstance(data, dict) and "identifier" not in data and "email" in data:
            data = {**data, "identifier": data["email"]}
        return data


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenWithUser(Token):
    user: UserRead
