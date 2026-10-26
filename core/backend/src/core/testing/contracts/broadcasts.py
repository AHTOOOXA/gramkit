"""Base test class for the core admin broadcasts API contract tests.

Covers every endpoint of ``core.infrastructure.fastapi.routers.admin_broadcasts``
(served under ``/admin`` through ``routers.admin``):

  GET   /admin/broadcasts                     (A)
  POST  /admin/broadcasts                     (A)  ('both' -> 2 rows)
  POST  /admin/broadcasts/media               (A, multipart)
  POST  /admin/broadcasts/format              (A)
  POST  /admin/broadcasts/preview             (A)
  POST  /admin/broadcasts/send-now            (O)
  GET   /admin/broadcasts/{id}/stats          (A)
  GET   /admin/broadcasts/{id}                (A, after static; 404 if missing)
  PATCH /admin/broadcasts/{id}                (A)
  POST  /admin/broadcasts/{id}/cancel         (A)

plus a route-shadowing guard (the static sub-paths reach their own handlers, not the
dynamic ``/broadcasts/{id}``) and the audit rows of the mutating endpoints.

Rule: the Owner-gated endpoint (send-now) has an ``admin_client`` -> 403 test, and every
endpoint has an ``authenticated_client`` -> 403 test.

Apps inherit this class and provide the fixtures:
- ``authenticated_client``: regular (non-admin) Telegram-authenticated client
- ``admin_client`` / ``owner_client``: from ``core.testing.fixtures`` (need ``test_app``)

The app's ``test_app`` must override ``get_bot`` with ``core.testing.fixtures.api_bot_mock()``
(awaitable sends; media sends return a ``file_id``) — a bare ``MagicMock`` bot makes the
media upload answer 400 — and ``get_arq_pool`` with a mock whose ``enqueue_job`` is an
``AsyncMock`` (send-now enqueues the worker job).

Types and relations are asserted (never hardcoded ids) so the suite stays parallel-safe.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from core.services import broadcasts as broadcasts_service


def _future_deadline() -> str:
    return (datetime.now(UTC) + timedelta(days=3)).isoformat()


def _text_create_body(time_slot: str = "morning") -> dict:
    return {
        "message_type": "text",
        "time_slot": time_slot,
        "deadline": _future_deadline(),
        "priority": 80,
        "message_text": "Hello world",
        "has_text_formatting": False,
        "keyboard_type": "none",
    }


async def _create_text_broadcast(admin_client: AsyncClient, time_slot: str = "morning") -> int:
    resp = await admin_client.post("/admin/broadcasts", json=_text_create_body(time_slot))
    assert resp.status_code == 200, resp.text
    return resp.json()["ids"][0]


async def _audit_rows(client: AsyncClient, action: str, target_id: str | None) -> list[dict]:
    """Audit rows of ``action`` for one target (``target_id=None``: rows without a target)."""
    resp = await client.get(f"/admin/audit-log?action={action}&page_size=100")
    assert resp.status_code == 200, resp.text
    return [row for row in resp.json()["items"] if row["target_id"] == target_id]


class BaseBroadcastTests:
    """Base class for core admin broadcasts API contract tests."""

    # =========================================================================
    # List
    # =========================================================================

    @pytest.mark.contract
    async def test_list_shape(self, admin_client: AsyncClient):
        resp = await admin_client.get("/admin/broadcasts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["active"], list)
        assert isinstance(data["completed"], list)
        assert isinstance(data["active_by_time_slot"], dict)

    @pytest.mark.contract
    async def test_list_lists_a_new_row_as_active(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)
        data = (await admin_client.get("/admin/broadcasts")).json()
        assert broadcast_id in [row["id"] for row in data["active"]]
        assert broadcast_id not in [row["id"] for row in data["completed"]]

    @pytest.mark.contract
    async def test_list_puts_an_expired_row_under_completed(self, admin_client: AsyncClient):
        body = {**_text_create_body(), "deadline": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()}
        broadcast_id = (await admin_client.post("/admin/broadcasts", json=body)).json()["ids"][0]

        data = (await admin_client.get("/admin/broadcasts")).json()
        detail = (await admin_client.get(f"/admin/broadcasts/{broadcast_id}")).json()

        assert broadcast_id in [row["id"] for row in data["completed"]]
        assert broadcast_id not in [row["id"] for row in data["active"]]
        assert detail["is_active"] is False

    @pytest.mark.contract
    async def test_list_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/admin/broadcasts")
        assert resp.status_code == 403

    # =========================================================================
    # Create
    # =========================================================================

    @pytest.mark.contract
    async def test_create_single_row(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts", json=_text_create_body("morning"))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ids"]) == 1
        assert isinstance(data["ids"][0], int)

    @pytest.mark.contract
    async def test_create_both_makes_two_rows(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts", json=_text_create_body("both"))
        assert resp.status_code == 200
        ids = resp.json()["ids"]
        assert len(ids) == 2
        assert ids[0] != ids[1]

    @pytest.mark.contract
    async def test_create_text_without_text_rejected(self, admin_client: AsyncClient):
        body = _text_create_body()
        body["message_text"] = ""
        resp = await admin_client.post("/admin/broadcasts", json=body)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Text broadcast requires message_text"

    @pytest.mark.contract
    async def test_create_media_without_file_id_rejected(self, admin_client: AsyncClient):
        body = {**_text_create_body(), "message_type": "photo", "message_text": None}
        resp = await admin_client.post("/admin/broadcasts", json=body)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "photo broadcast requires media_file_id"

    @pytest.mark.contract
    async def test_create_writes_audit_row(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts", json=_text_create_body("both"))
        ids = resp.json()["ids"]

        rows = await _audit_rows(admin_client, "broadcast_create", ",".join(str(i) for i in ids))

        assert len(rows) == 1
        assert rows[0]["target_type"] == "broadcast"
        assert rows[0]["actor_role"] == "admin"
        assert rows[0]["detail"]["ids"] == ids
        assert rows[0]["detail"]["rows_created"] == 2

    @pytest.mark.contract
    async def test_create_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/admin/broadcasts", json=_text_create_body())
        assert resp.status_code == 403

    # =========================================================================
    # Format
    # =========================================================================

    @pytest.mark.contract
    async def test_format_entities_to_html(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts/format",
            json={"text": "bold text", "entities": [{"type": "bold", "offset": 0, "length": 4}]},
        )
        assert resp.status_code == 200
        assert resp.json()["html"] == "<b>bold</b> text"

    @pytest.mark.contract
    async def test_format_without_entities_passes_through(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts/format", json={"text": "plain"})
        assert resp.status_code == 200
        assert resp.json()["html"] == "plain"

    @pytest.mark.contract
    async def test_format_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/admin/broadcasts/format", json={"text": "x"})
        assert resp.status_code == 403

    # =========================================================================
    # Media upload (multipart)
    # =========================================================================

    @pytest.mark.contract
    async def test_media_upload_mints_file_id(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts/media",
            data={"message_type": "photo"},
            files={"file": ("pic.jpg", b"\xff\xd8\xff\xe0fakejpeg", "image/jpeg")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["file_id"]
        assert data["message_type"] == "photo"

    @pytest.mark.contract
    async def test_media_bad_type_rejected(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts/media",
            data={"message_type": "sticker"},
            files={"file": ("x.bin", b"data", "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Unsupported media type: sticker"

    @pytest.mark.contract
    async def test_media_empty_file_rejected(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts/media",
            data={"message_type": "photo"},
            files={"file": ("pic.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Empty file"

    @pytest.mark.contract
    async def test_media_over_the_telegram_limit_rejected(self, admin_client: AsyncClient, monkeypatch):
        monkeypatch.setitem(broadcasts_service.UPLOAD_LIMITS, "photo", 4)
        resp = await admin_client.post(
            "/admin/broadcasts/media",
            data={"message_type": "photo"},
            files={"file": ("pic.jpg", b"12345", "image/jpeg")},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"].startswith("File too large")

    @pytest.mark.contract
    async def test_media_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/admin/broadcasts/media",
            data={"message_type": "photo"},
            files={"file": ("pic.jpg", b"data", "image/jpeg")},
        )
        assert resp.status_code == 403

    # =========================================================================
    # Preview
    # =========================================================================

    @pytest.mark.contract
    async def test_preview_text(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts/preview",
            json={"message_type": "text", "message_text": "preview me", "keyboard_type": "main"},
        )
        assert resp.status_code == 200
        assert resp.json()["sent"] is True

    @pytest.mark.contract
    async def test_preview_text_without_text_rejected(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts/preview", json={"message_type": "text"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Text message requires message_text"

    @pytest.mark.contract
    async def test_preview_media_without_file_id_rejected(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts/preview", json={"message_type": "video"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Media message requires media_file_id"

    @pytest.mark.contract
    async def test_preview_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/admin/broadcasts/preview", json={"message_type": "text", "message_text": "x"}
        )
        assert resp.status_code == 403

    # =========================================================================
    # Send now (OwnerUser)
    # =========================================================================

    @pytest.mark.contract
    async def test_send_now_owner_queues(self, owner_client: AsyncClient):
        resp = await owner_client.post(
            "/admin/broadcasts/send-now",
            json={"message_type": "text", "message_text": "blast", "keyboard_type": "none"},
        )
        assert resp.status_code == 200
        assert resp.json()["queued"] is True

    @pytest.mark.contract
    async def test_send_now_saved_row_writes_audit_row(self, owner_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(owner_client)

        resp = await owner_client.post("/admin/broadcasts/send-now", json={"broadcast_id": broadcast_id})
        assert resp.status_code == 200

        rows = await _audit_rows(owner_client, "broadcast_send_now", str(broadcast_id))
        assert len(rows) == 1
        assert rows[0]["actor_role"] == "owner"
        assert rows[0]["target_type"] == "broadcast"
        assert rows[0]["detail"]["from_broadcast_id"] == broadcast_id

    @pytest.mark.contract
    async def test_send_now_unknown_broadcast_404(self, owner_client: AsyncClient):
        resp = await owner_client.post("/admin/broadcasts/send-now", json={"broadcast_id": 99999999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Broadcast not found"

    @pytest.mark.contract
    async def test_send_now_without_content_rejected(self, owner_client: AsyncClient):
        resp = await owner_client.post("/admin/broadcasts/send-now", json={})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "send-now requires broadcast_id or message_type"

    @pytest.mark.contract
    async def test_send_now_admin_forbidden(self, admin_client: AsyncClient):
        """send-now is OwnerUser-gated — a plain admin must get 403."""
        resp = await admin_client.post(
            "/admin/broadcasts/send-now",
            json={"message_type": "text", "message_text": "blast"},
        )
        assert resp.status_code == 403

    @pytest.mark.contract
    async def test_send_now_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/admin/broadcasts/send-now", json={"message_type": "text", "message_text": "x"}
        )
        assert resp.status_code == 403

    # =========================================================================
    # Detail, stats, edit, cancel
    # =========================================================================

    @pytest.mark.contract
    async def test_detail_shape(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)
        resp = await admin_client.get(f"/admin/broadcasts/{broadcast_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == broadcast_id
        assert data["message_type"] == "text"
        assert data["is_active"] is True
        assert data["stats"]["sent_count"] == 0
        assert data["stats"]["cycles_run"] == 0

    @pytest.mark.contract
    async def test_detail_missing_404(self, admin_client: AsyncClient):
        resp = await admin_client.get("/admin/broadcasts/99999999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Broadcast not found"

    @pytest.mark.contract
    async def test_detail_non_admin_forbidden(self, authenticated_client: AsyncClient, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)
        resp = await authenticated_client.get(f"/admin/broadcasts/{broadcast_id}")
        assert resp.status_code == 403

    @pytest.mark.contract
    async def test_stats_shape(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)
        resp = await admin_client.get(f"/admin/broadcasts/{broadcast_id}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 0
        assert data["success_count"] == 0
        assert data["last_sent_at"] is None

    @pytest.mark.contract
    async def test_stats_missing_404(self, admin_client: AsyncClient):
        resp = await admin_client.get("/admin/broadcasts/99999999/stats")
        assert resp.status_code == 404

    @pytest.mark.contract
    async def test_stats_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/admin/broadcasts/1/stats")
        assert resp.status_code == 403

    @pytest.mark.contract
    async def test_edit_updates_priority_and_audits(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)

        resp = await admin_client.patch(f"/admin/broadcasts/{broadcast_id}", json={"priority": 200})

        assert resp.status_code == 200
        assert resp.json()["priority"] == 200
        rows = await _audit_rows(admin_client, "broadcast_edit", str(broadcast_id))
        assert len(rows) == 1
        assert rows[0]["detail"]["changed_fields"] == ["priority"]

    @pytest.mark.contract
    async def test_edit_to_media_without_file_id_rejected(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)

        resp = await admin_client.patch(f"/admin/broadcasts/{broadcast_id}", json={"message_type": "photo"})

        assert resp.status_code == 400
        assert resp.json()["detail"] == "photo broadcast requires media_file_id"
        assert (await admin_client.get(f"/admin/broadcasts/{broadcast_id}")).json()["message_type"] == "text"

    @pytest.mark.contract
    @pytest.mark.parametrize("field", ["message_type", "deadline", "priority"])
    async def test_edit_null_for_a_required_field_rejected(self, admin_client: AsyncClient, field: str):
        """An explicit null for a NOT NULL column is a 400, not a failed UPDATE (500)."""
        broadcast_id = await _create_text_broadcast(admin_client)

        resp = await admin_client.patch(f"/admin/broadcasts/{broadcast_id}", json={field: None})

        assert resp.status_code == 400
        assert field in resp.json()["detail"]
        assert (await admin_client.get(f"/admin/broadcasts/{broadcast_id}")).json()[field] is not None

    @pytest.mark.contract
    async def test_edit_text_without_the_flag_keeps_the_formatting(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts",
            json={**_text_create_body(), "message_text": "<b>Hi</b>", "has_text_formatting": True},
        )
        [broadcast_id] = resp.json()["ids"]

        resp = await admin_client.patch(f"/admin/broadcasts/{broadcast_id}", json={"message_text": "<i>Hey</i>"})

        assert resp.status_code == 200
        data = resp.json()
        assert (data["message_text"], data["message_html"], data["has_text_formatting"]) == (
            "<i>Hey</i>",
            "<i>Hey</i>",
            True,
        )

    @pytest.mark.contract
    async def test_edit_can_turn_the_formatting_off(self, admin_client: AsyncClient):
        resp = await admin_client.post(
            "/admin/broadcasts",
            json={**_text_create_body(), "message_text": "<b>Hi</b>", "has_text_formatting": True},
        )
        [broadcast_id] = resp.json()["ids"]

        resp = await admin_client.patch(f"/admin/broadcasts/{broadcast_id}", json={"has_text_formatting": False})

        assert resp.status_code == 200
        assert resp.json()["has_text_formatting"] is False

    @pytest.mark.contract
    async def test_edit_missing_404(self, admin_client: AsyncClient):
        resp = await admin_client.patch("/admin/broadcasts/99999999", json={"priority": 1})
        assert resp.status_code == 404

    @pytest.mark.contract
    async def test_edit_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch("/admin/broadcasts/1", json={"priority": 1})
        assert resp.status_code == 403

    @pytest.mark.contract
    async def test_cancel_sets_inactive_and_audits(self, admin_client: AsyncClient):
        broadcast_id = await _create_text_broadcast(admin_client)

        resp = await admin_client.post(f"/admin/broadcasts/{broadcast_id}/cancel")

        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["completed_at"] is not None
        rows = await _audit_rows(admin_client, "broadcast_cancel", str(broadcast_id))
        assert len(rows) == 1
        assert rows[0]["target_type"] == "broadcast"

    @pytest.mark.contract
    async def test_cancel_again_changes_nothing(self, admin_client: AsyncClient):
        """Cancelling an inactive row returns it as it is: same completed_at, no second audit row."""
        broadcast_id = await _create_text_broadcast(admin_client)
        first = (await admin_client.post(f"/admin/broadcasts/{broadcast_id}/cancel")).json()

        resp = await admin_client.post(f"/admin/broadcasts/{broadcast_id}/cancel")

        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["completed_at"] == first["completed_at"]
        assert len(await _audit_rows(admin_client, "broadcast_cancel", str(broadcast_id))) == 1

    @pytest.mark.contract
    async def test_cancel_of_an_expired_row_changes_nothing(self, admin_client: AsyncClient):
        body = {**_text_create_body(), "deadline": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()}
        broadcast_id = (await admin_client.post("/admin/broadcasts", json=body)).json()["ids"][0]

        resp = await admin_client.post(f"/admin/broadcasts/{broadcast_id}/cancel")

        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["completed_at"] is None
        assert await _audit_rows(admin_client, "broadcast_cancel", str(broadcast_id)) == []

    @pytest.mark.contract
    async def test_cancel_missing_404(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts/99999999/cancel")
        assert resp.status_code == 404

    @pytest.mark.contract
    async def test_cancel_non_admin_forbidden(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/admin/broadcasts/1/cancel")
        assert resp.status_code == 403

    # =========================================================================
    # Route shadowing guard
    # =========================================================================
    # The static /broadcasts/<word> paths must NOT be swallowed by /broadcasts/{id:int}:
    # "format"/"media"/"preview"/"send-now" would parse as a broadcast_id and 422.

    @pytest.mark.contract
    async def test_format_not_shadowed(self, admin_client: AsyncClient):
        resp = await admin_client.post("/admin/broadcasts/format", json={"text": "x"})
        assert resp.status_code == 200  # reached the format handler, not {id}

    @pytest.mark.contract
    async def test_send_now_not_shadowed_for_admin(self, admin_client: AsyncClient):
        # Reaches the OWNER-gated handler (403), NOT a 422 from {id} int-parse of "send-now".
        resp = await admin_client.post("/admin/broadcasts/send-now", json={"message_type": "text", "message_text": "x"})
        assert resp.status_code == 403

    @pytest.mark.contract
    async def test_media_requires_multipart_not_int_parse(self, admin_client: AsyncClient):
        # /media with no body → 422 for the missing multipart fields (the media handler);
        # the upload test above proves the handler itself is reachable.
        resp = await admin_client.post("/admin/broadcasts/media")
        assert resp.status_code == 422
        missing = {tuple(err["loc"]) for err in resp.json()["detail"]}
        assert ("body", "file") in missing
