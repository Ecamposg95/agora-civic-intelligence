"""Standard paginated response envelope.

Canonical shape (Golden Rule #7):
    { "items": [...], "total": 0, "limit": 50, "offset": 0 }
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A paginated response."""

    items: List[T]
    total: int
    limit: int
    offset: int
