"""
Regression tests for admin notification spam prevention.

Date: December 2025
Severity: High
Root cause: Time-based `is_new` check caused admin notification spam on network retries.
Fix: Changed to state-based check (`last_activity_date is None`).

These tests ensure the bug where multiple process_start calls would spam
admin notifications does not recur.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.regression
class TestIsNewAdminSpamFix:
    """Regression tests for admin notification spam prevention."""

    async def test_multiple_process_start_calls_send_one_admin_notification(
        self, authenticated_client: AsyncClient, mock_arq_enqueue
    ):
        """
        Multiple process_start calls should send ONE admin notification.

        Bug: Time-based `is_new` check caused admin notification spam on network retries.
        Fix: Changed to state-based check (`last_activity_date is None`).

        Before fix: Each process_start call would check `is_new` based on time,
                   causing multiple admin notifications if calls happened quickly.
        After fix: Only first call sends notification (state-based check).
        """
        # First call - creates user and sends notification
        await authenticated_client.get("/users/me")
        response = await authenticated_client.post(
            "/process_start",
            json={"referal_id": "r-first", "timezone": "UTC"},
        )
        assert response.status_code == 200

        # Count admin broadcast jobs after first call
        admin_jobs = [j for j in mock_arq_enqueue if j["job_name"] == "admin_broadcast_job"]
        first_call_count = len(admin_jobs)

        # Second call - should NOT spam admin
        response = await authenticated_client.post(
            "/process_start",
            json={"referal_id": "r-second", "timezone": "UTC"},
        )
        assert response.status_code == 200

        # Count admin broadcast jobs after second call
        admin_jobs = [j for j in mock_arq_enqueue if j["job_name"] == "admin_broadcast_job"]
        second_call_count = len(admin_jobs)

        # Second call should NOT add more admin notifications
        assert second_call_count == first_call_count, (
            f"Admin notification spam detected! "
            f"Expected {first_call_count} notifications, got {second_call_count}. "
            "This regression indicates is_new check is time-based instead of state-based."
        )

    async def test_posthog_new_user_event_sent_once(self, authenticated_client: AsyncClient, mock_posthog):
        """
        PostHog 'new_user_registered' event sent once, not spammed.

        Similar to admin notification test, but for analytics tracking.
        Ensures we don't inflate user registration metrics.
        """
        # First call - creates user and sends event
        await authenticated_client.get("/users/me")
        await authenticated_client.post(
            "/process_start",
            json={"referal_id": "r-test", "timezone": "UTC"},
        )

        # Count new_user_registered events
        new_user_events = [e for e in mock_posthog if e["event"] == "new_user_registered"]
        first_count = len(new_user_events)

        # Second call - should NOT send another event
        await authenticated_client.post(
            "/process_start",
            json={"referal_id": "r-test-again", "timezone": "UTC"},
        )

        # Count again
        new_user_events = [e for e in mock_posthog if e["event"] == "new_user_registered"]
        second_count = len(new_user_events)

        assert second_count == first_count, (
            f"PostHog event spam detected! "
            f"Expected {first_count} new_user_registered events, got {second_count}. "
            "This would inflate user registration metrics."
        )

    async def test_user_without_referal_also_works(self, authenticated_client: AsyncClient, mock_arq_enqueue):
        """
        Users without referal codes get exactly ONE admin notification.

        Regression test ensuring the fix works regardless of referal presence.
        """
        # First call without referal
        await authenticated_client.get("/users/me")
        await authenticated_client.post(
            "/process_start",
            json={"timezone": "UTC"},
        )

        admin_jobs = [j for j in mock_arq_enqueue if j["job_name"] == "admin_broadcast_job"]
        first_count = len(admin_jobs)

        # Second call without referal
        await authenticated_client.post(
            "/process_start",
            json={"timezone": "UTC"},
        )

        admin_jobs = [j for j in mock_arq_enqueue if j["job_name"] == "admin_broadcast_job"]
        second_count = len(admin_jobs)

        assert second_count == first_count, (
            f"Admin notification spam for non-referal users! Expected {first_count}, got {second_count}."
        )
