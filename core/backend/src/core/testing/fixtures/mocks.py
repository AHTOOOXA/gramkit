"""Mock fixtures for external services and internal async operations."""

import pytest


@pytest.fixture
def mock_yookassa(monkeypatch):
    """
    Mock YooKassa SDK responses.

    Use for testing payment creation flows.

    This fixture mocks the YooKassa Payment.create() method to return
    mock payment objects instead of making real API calls.

    Each call to Payment.create() returns a unique payment ID to avoid
    conflicts when running tests in parallel.
    """
    from unittest.mock import MagicMock
    from uuid import uuid4

    # Counter for unique IDs
    call_counter = {"count": 0}

    def mock_create(request):
        """Mock Payment.create() method with unique IDs"""
        call_counter["count"] += 1
        unique_id = f"payment_test_{uuid4().hex[:8]}_{call_counter['count']}"

        # Create a mock payment response with unique ID
        mock_payment = MagicMock()
        mock_payment.id = unique_id
        mock_payment.status = "pending"
        mock_payment.metadata = {"app_payment_id": "1", "is_recurring": "false"}

        # Mock confirmation object
        mock_confirmation = MagicMock()
        mock_confirmation.confirmation_url = f"https://test.yookassa.ru/checkout/{unique_id}"
        mock_payment.confirmation = mock_confirmation

        # Mock payment method for recurring payments
        mock_payment_method = MagicMock()
        mock_payment_method.id = f"payment_method_test_{unique_id}"
        mock_payment.payment_method = mock_payment_method

        return mock_payment

    # Patch YooKassa Payment.create
    from yookassa import Payment as YooKassaPayment

    monkeypatch.setattr(YooKassaPayment, "create", mock_create)

    yield


@pytest.fixture
def mock_arq_enqueue(monkeypatch):
    """
    Mock ARQ job enqueuing to capture background jobs.

    Critical for testing:
    - Admin notifications (queue_admin_broadcast)
    - Background job scheduling
    - Worker job verification

    Returns list of enqueued jobs for assertions.

    Usage:
        async def test_admin_notification(mock_arq_enqueue):
            # ... trigger admin notification
            assert len(mock_arq_enqueue) == 1
            assert mock_arq_enqueue[0]["job_name"] == "admin_broadcast_job"
            assert "New user" in mock_arq_enqueue[0]["args"][0]
    """
    enqueued_jobs = []

    async def mock_enqueue(self, job_name: str, *args, **kwargs):
        """Mock enqueue_job method on WorkerService."""
        enqueued_jobs.append({"job_name": job_name, "args": args, "kwargs": kwargs})

    # Patch WorkerService.enqueue_job
    from core.services.worker import WorkerService

    monkeypatch.setattr(WorkerService, "enqueue_job", mock_enqueue)

    return enqueued_jobs


@pytest.fixture
def mock_posthog(monkeypatch):
    """
    Mock PostHog event tracking.

    Critical for testing:
    - User registration events
    - Referral tracking
    - Analytics event verification

    Returns list of captured events for assertions.

    Usage:
        async def test_posthog_tracking(mock_posthog):
            # ... trigger event
            assert len(mock_posthog) == 1
            assert mock_posthog[0]["event"] == "new_user_registered"
            assert mock_posthog[0]["properties"]["referal_id"] == "r-test"
    """
    captured_events = []

    def mock_capture(distinct_id, event, properties=None):
        """Mock posthog.capture()."""
        captured_events.append({"distinct_id": distinct_id, "event": event, "properties": properties or {}})

    # Patch posthog.capture
    from core.infrastructure.posthog import posthog

    monkeypatch.setattr(posthog, "capture", mock_capture)

    return captured_events


@pytest.fixture
def mock_yookassa_webhook(monkeypatch):
    """
    Mock YooKassa WebhookNotificationFactory for testing webhook processing.

    Critical for testing:
    - Payment success webhooks
    - Payment failure webhooks
    - Webhook idempotency
    - Subscription activation via webhooks

    The mock creates a simple notification object that mimics YooKassa's structure
    and bypasses strict SDK validation.

    Supported webhook events:
    - payment.succeeded
    - payment.canceled
    - payment.waiting_for_capture
    - payment.failed

    Required payload structure:
        {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "provider_payment_id",
                "status": "succeeded",
                "metadata": {"app_payment_id": "internal_uuid"},
                "payment_method": {"id": "method_id", "type": "bank_card"}  # optional
            }
        }

    Limitations:
    - Does not validate payload completeness (focuses on fields used by provider)
    - Does not simulate SDK parsing errors (use mock_yookassa for that)
    - to_dict() returns simplified structure (sufficient for provider_metadata)

    Usage:
        async def test_webhook(mock_yookassa_webhook):
            webhook_payload = {
                "type": "notification",
                "event": "payment.succeeded",
                "object": {
                    "id": "test_123",
                    "status": "succeeded",
                    "metadata": {"app_payment_id": str(payment_id)},
                }
            }
            response = await client.post("/yookassa/webhook", json=webhook_payload)
    """

    class MockNotification:
        """Mock YooKassa notification object."""

        def __init__(self, payload):
            self.event = payload.get("event", "payment.succeeded")
            self.object = MockObject(payload.get("object", {}))

        def to_dict(self):
            """Serialize notification to dict (used for provider_metadata storage)."""
            obj_dict = {
                "id": self.object.id,
                "status": self.object.status,
                "metadata": self.object.metadata,
            }
            # Properly serialize payment_method if present
            if self.object.payment_method:
                obj_dict["payment_method"] = {
                    "id": self.object.payment_method.id,
                    "type": self.object.payment_method.type,
                }
            return {
                "type": "notification",
                "event": self.event,
                "object": obj_dict,
            }

    class MockObject:
        """Mock YooKassa payment object."""

        def __init__(self, obj_data):
            self.id = obj_data.get("id", "test_payment_id")
            self.status = obj_data.get("status", "succeeded")
            self.metadata = obj_data.get("metadata", {})
            # Add payment_method if provided (not dependent on status)
            if "payment_method" in obj_data:
                self.payment_method = MockPaymentMethod(obj_data["payment_method"])
            else:
                self.payment_method = None

    class MockPaymentMethod:
        """Mock YooKassa payment method object."""

        def __init__(self, method_data):
            self.id = method_data.get("id", "test_method_id")
            self.type = method_data.get("type", "bank_card")

    class MockFactory:
        """Mock WebhookNotificationFactory."""

        def create(self, payload):
            return MockNotification(payload)

    # Patch YooKassa WebhookNotificationFactory
    from yookassa.domain.notification import webhook_notification

    original_factory = webhook_notification.WebhookNotificationFactory
    monkeypatch.setattr(webhook_notification, "WebhookNotificationFactory", MockFactory)

    yield

    # Restore original factory
    monkeypatch.setattr(webhook_notification, "WebhookNotificationFactory", original_factory)
