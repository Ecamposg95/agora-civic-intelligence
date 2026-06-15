"""Pagination query parameters (limit/offset)."""

from fastapi import Query


class PaginationParams:
    """Common limit/offset pagination parameters."""

    def __init__(
        self,
        limit: int = Query(50, ge=1, le=200, description="Max items to return"),
        offset: int = Query(0, ge=0, description="Items to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset


Pagination = PaginationParams
