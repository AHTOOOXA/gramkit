"""Read-only helpers for admin list endpoints (search + date filter + safe sort + paginate).

Pure functions over a SQLAlchemy ``Select`` — no session, no flush, no commit. The
key safety property: ``sort_by`` is ONLY honoured if present in the per-endpoint
``sortable`` whitelist, so a client can never sort by (or inject) an arbitrary
column name.
"""

from __future__ import annotations

from sqlalchemy import Column, Select, func, or_, select

from core.schemas.admin_common import AdminListParams


def apply_admin_list(
    stmt: Select,
    params: AdminListParams,
    sortable: dict[str, Column],
    searchable: list[Column],
    date_column: Column | None = None,
) -> Select:
    """Apply search, date range, whitelisted sort, and pagination to a select.

    Args:
        stmt: Base select (already scoped to the rows the endpoint cares about).
        params: Parsed admin list params (page / sort / search / date range).
        sortable: Whitelist mapping ``sort_by`` value -> the actual Column. The
            FIRST entry is the default sort when ``sort_by`` is missing/unknown.
        searchable: Columns OR-ed together with ILIKE for free-text ``search`` (matched
            literally: ``%`` / ``_`` / ``\\`` in the term are escaped).
        date_column: Column the ``date_from`` / ``date_to`` bounds apply to.

    Returns:
        A new ``Select`` with filters/order/limit/offset applied (input untouched).
    """
    stmt = _apply_filters(stmt, params, searchable, date_column)
    stmt = _apply_order(stmt, params, sortable)
    return stmt.offset(params.offset).limit(params.limit)


def admin_list_count(
    stmt: Select,
    params: AdminListParams,
    searchable: list[Column],
    date_column: Column | None = None,
) -> Select:
    """Build the COUNT(*) select for the filtered rows (before limit/offset).

    Applies the same search + date filters as ``apply_admin_list`` (but not sort or
    pagination) so ``total`` reflects the full filtered result set.
    """
    filtered = _apply_filters(stmt, params, searchable, date_column)
    return select(func.count()).select_from(filtered.order_by(None).subquery())


def escape_like(term: str) -> str:
    """Escape LIKE metacharacters so a search term matches literally (``%`` and ``_`` lose their meaning).

    The backslash (the escape character passed to ``ilike(..., escape="\\")``) is escaped first.
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(
    stmt: Select,
    params: AdminListParams,
    searchable: list[Column],
    date_column: Column | None,
) -> Select:
    if params.search and searchable:
        pattern = f"%{escape_like(params.search)}%"
        stmt = stmt.where(or_(*[col.ilike(pattern, escape="\\") for col in searchable]))

    if date_column is not None:
        if params.date_from is not None:
            stmt = stmt.where(date_column >= params.date_from)
        if params.date_to is not None:
            stmt = stmt.where(date_column <= params.date_to)

    return stmt


def _apply_order(stmt: Select, params: AdminListParams, sortable: dict[str, Column]) -> Select:
    if not sortable:
        return stmt

    # Whitelist: only honour sort_by if it's a known column; else fall back to default.
    column = sortable.get(params.sort_by) if params.sort_by else None
    if column is None:
        column = next(iter(sortable.values()))

    direction = column.desc() if params.sort_dir == "desc" else column.asc()
    return stmt.order_by(direction)
