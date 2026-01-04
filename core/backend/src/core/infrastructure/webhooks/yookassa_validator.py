"""YooKassa webhook signature validator."""

import hashlib
import hmac

from fastapi import HTTPException


class YooKassaWebhookValidator:
    """Validate YooKassa webhook signatures."""

    def __init__(self, api_secret: str):
        self.api_secret = api_secret

    def validate_signature(self, payload: dict, signature_header: str | None) -> bool:
        """
        Validate YooKassa webhook signature.

        YooKassa sends signature in Authorization header as: "Bearer <signature>"
        The signature is HMAC-SHA256 of: "{notification_type}&{object_id}&{object_status}"

        Args:
            payload: The webhook payload dictionary
            signature_header: The Authorization header value

        Returns:
            True if signature is valid

        Raises:
            HTTPException: If signature is missing or invalid
        """
        if not signature_header:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # Extract signature (remove "Bearer " prefix)
        signature = signature_header.replace("Bearer ", "").strip()

        # Build canonical string (YooKassa format)
        try:
            notification_type = payload.get("type", "")
            obj = payload.get("object", {})
            object_id = obj.get("id", "")
            object_status = obj.get("status", "")

            canonical_string = f"{notification_type}&{object_id}&{object_status}"
        except (KeyError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {e}")

        # Compute expected signature
        expected_signature = hmac.new(
            self.api_secret.encode("utf-8"), canonical_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Constant-time comparison (prevent timing attacks)
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        return True
