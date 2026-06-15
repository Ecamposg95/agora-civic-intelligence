"""Health check response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness / readiness payload."""

    status: str = "ok"
    service: str
    version: str
    environment: str
