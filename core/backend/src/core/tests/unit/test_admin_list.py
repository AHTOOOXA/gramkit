"""Business-logic tests for the admin list helper (sort whitelist / no SQL injection).

Pure: builds selects and inspects the COMPILED SQL — no DB needed. The critical
property is that ``sort_by`` is whitelisted: an unknown / malicious column name is
ignored and the default sort is used, so a client can never order by (or inject via)
an arbitrary column.
"""

import pytest
from sqlalchemy import select

from core.infrastructure.database.models import AuditLog
from core.infrastructure.database.repo.admin_list import admin_list_count, apply_admin_list, escape_like
from core.schemas.admin_common import AdminListParams, AdminListResponse

SORTABLE = {
    "created_at": AuditLog.created_at,
    "action": AuditLog.action,
}
SEARCHABLE = [AuditLog.action, AuditLog.target_type]


def _params(**overrides) -> AdminListParams:
    base = dict(page=1, page_size=25, sort_by=None, sort_dir="desc", search=None, date_from=None, date_to=None)
    base.update(overrides)
    return AdminListParams(**base)


@pytest.mark.business_logic
class TestApplyAdminList:
    def test_unknown_sort_column_falls_back_to_default(self):
        """A bogus sort_by is ignored; the first whitelisted column (created_at) is used."""
        stmt = apply_admin_list(select(AuditLog), _params(sort_by="nonexistent"), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "ORDER BY" in sql
        assert "created_at" in sql
        assert "nonexistent" not in sql

    def test_sql_injection_attempt_in_sort_by_is_ignored(self):
        """An injection-shaped sort_by never reaches the SQL — default sort is used."""
        malicious = "id; DROP TABLE admin_audit_logs;--"
        stmt = apply_admin_list(select(AuditLog), _params(sort_by=malicious), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "DROP TABLE" not in sql
        assert "created_at" in sql  # fell back to default

    def test_whitelisted_sort_column_is_honoured(self):
        """A known sort_by (action) is applied with the requested direction."""
        stmt = apply_admin_list(select(AuditLog), _params(sort_by="action", sort_dir="asc"), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "ORDER BY" in sql
        assert "action ASC" in sql

    def test_pagination_applies_limit_and_offset(self):
        """page/page_size map to OFFSET/LIMIT."""
        stmt = apply_admin_list(select(AuditLog), _params(page=3, page_size=10), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql

    def test_search_applies_ilike_across_searchable(self):
        """search produces an OR of case-insensitive LIKE clauses over the searchable columns."""
        stmt = apply_admin_list(select(AuditLog), _params(search="gift"), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()

        # ILIKE renders as `lower(col) like lower(pattern)` in the generic dialect — one per column.
        assert " like " in sql
        assert sql.count(" or ") == len(SEARCHABLE) - 1
        assert "%gift%" in sql

    def test_search_escapes_like_metacharacters(self):
        """``%`` / ``_`` / ``\\`` in the term are escaped and the ILIKE declares the escape char,
        so the term matches literally instead of as a LIKE pattern."""
        stmt = apply_admin_list(select(AuditLog), _params(search="50%_off"), SORTABLE, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "%50\\%\\_off%" in sql
        assert sql.count("ESCAPE") == len(SEARCHABLE)

    @pytest.mark.parametrize(
        ("term", "escaped"),
        [("plain", "plain"), ("50%", "50\\%"), ("a_b", "a\\_b"), ("back\\slash", "back\\\\slash")],
    )
    def test_escape_like(self, term: str, escaped: str):
        assert escape_like(term) == escaped

    def test_count_helper_drops_sort_and_pagination(self):
        """The count select wraps the filtered query without ORDER BY / LIMIT / OFFSET."""
        params = _params(sort_by="action", page=2, page_size=10)
        stmt = admin_list_count(select(AuditLog), params, SEARCHABLE)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "count(" in sql.lower()
        assert "LIMIT" not in sql
        assert "OFFSET" not in sql


@pytest.mark.business_logic
class TestAdminListResponse:
    @pytest.mark.parametrize(
        ("total", "page_size", "expected_pages"),
        [(0, 25, 0), (1, 25, 1), (25, 25, 1), (26, 25, 2), (101, 10, 11)],
    )
    def test_build_computes_total_pages(self, total: int, page_size: int, expected_pages: int):
        """total_pages is ceil(total / page_size); page and page_size are echoed back."""
        params = _params(page=2, page_size=page_size)

        envelope = AdminListResponse[int].build([], total, params)

        assert envelope.total == total
        assert envelope.total_pages == expected_pages
        assert envelope.page == 2
        assert envelope.page_size == page_size
