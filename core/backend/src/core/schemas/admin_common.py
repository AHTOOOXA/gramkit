"""Shared admin-panel conventions: generic list params + paginated envelope + RBAC.

This is a new, single convention for ALL admin list endpoints (the rest of the
codebase only does `limit` pass-through). Every list endpoint takes
``AdminListParams`` via ``Depends`` and returns ``AdminListResponse[T]`` so the
frontend has one envelope shape to consume.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class AdminListParams:
    """Query-param dependency for admin list endpoints.

    Consumed via ``Depends`` (FastAPI binds the query params onto __init__). Kept
    as a plain dependency class — same idiom as the other routers' query params —
    so it composes with extra per-endpoint query params on the same handler.

    Note: ``sort_by`` is NEVER trusted directly — each repo whitelists it against
    a ``sortable`` dict in ``apply_admin_list``.
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number."),
        page_size: int = Query(25, ge=1, le=100, description="Rows per page (max 100)."),
        sort_by: str | None = Query(None, description="Column to sort by (whitelisted server-side)."),
        sort_dir: Literal["asc", "desc"] = Query("desc", description="Sort direction."),
        search: str | None = Query(None, description="Free-text search (ILIKE across searchable columns)."),
        date_from: datetime | None = Query(None, description="Inclusive lower bound on the date column."),
        date_to: datetime | None = Query(None, description="Inclusive upper bound on the date column."),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        self.search = search
        self.date_from = date_from
        self.date_to = date_to

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class AdminListResponse(BaseModel, Generic[T]):  # noqa: UP046
    """Uniform paginated envelope for every admin list endpoint."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(cls, items: list[T], total: int, params: AdminListParams) -> AdminListResponse[T]:
        """Build the envelope from the filtered rows, the unpaginated total, and the params."""
        total_pages = math.ceil(total / params.page_size) if params.page_size else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )


class AdminRbacSchema(BaseModel):
    """Effective RBAC capabilities of the requesting admin (resolved server-side)."""

    role: str
    is_admin: bool
    is_owner: bool
    can_perform_destructive: bool

    model_config = ConfigDict(from_attributes=True)
