from collections.abc import Collection
from datetime import UTC, datetime

from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.infrastructure.telegram.admin_messages import esc, tags, user_ref, user_tag
from core.schemas.start import StartData, StartParamsRequest
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.base import BaseService
from core.services.users import is_valid_timezone

logger = get_logger(__name__)


class StartService(BaseService):
    def __init__(self, repo, producer, services, bot, internal_referal_ids: Collection[str] = ()):
        super().__init__(repo, producer, services, bot)
        # referal_ids of the app's own links to existing users (notification buttons,
        # broadcasts). They say what brought a user back, not how the user was acquired, so
        # they are never stored as the acquisition source.
        self.internal_referal_ids = frozenset(internal_referal_ids)

    async def process_start(self, user: UserSchema, start_params: StartParamsRequest) -> StartData:
        logger.info(f"Processing start with params: {start_params}")

        # may work multiple times
        logger.info(
            f"User {user.id} opened app, new: {user.is_new}, created_at: {user.created_at}, updated_at: {user.updated_at}"
        )

        referal_id = start_params.referal_id if start_params.referal_id else None
        if user.is_new and not user.is_guest:
            # A user who pressed a bare /start and first opened the app from a notification has
            # no known source — not the notification.
            source = referal_id if referal_id not in self.internal_referal_ids else None
            if source:
                await self.services.users.process_referal(referal_id=source, user_id=user.id)
            logger.info(f"New user {user.id} registered, source: {source} (link: {referal_id})")
            details = [esc(user.language_code or user.tg_language_code or "?")]
            if user.tg_is_premium:
                details.append("⭐ Premium")
            if source:
                details.append(f"src <code>{esc(source)}</code>")
            message = f"👤 New user · {user_ref(user)}\n<i>{' · '.join(details)}</i>\n{tags('newuser', user_tag(user))}"
            await self.services.messages.queue_admin_broadcast(message, silent=True)
            posthog.capture(
                distinct_id=str(user.id),
                event="new_user_registered",
                properties={
                    "$set": {"username": user.username},
                    "$set_once": {"referal_id": source, "invite_code": start_params.invite_code},
                },
            )

        else:
            if referal_id:
                logger.info(f"User {user.id} opened app again, from ref {referal_id}")
            else:
                logger.info(f"User {user.id} opened app again")

            posthog.capture(
                distinct_id=str(user.id),
                event="user_returned",
                properties={
                    "days_since_last_visit": (datetime.now(UTC) - user.updated_at).days if user.updated_at else None,
                    "visit_number": user.total_active_days or 1,
                    "current_streak": user.current_streak,
                    "best_streak": user.best_streak,
                },
            )

        inviter = None
        if start_params.invite_code:
            inviter = await self.services.invites.process_invite(start_params.invite_code, user.id)
            if inviter:
                posthog.capture(
                    distinct_id=str(user.id),
                    event="invite_accepted",
                    properties={
                        "inviter_id": str(inviter.id),
                        "invite_code": start_params.invite_code,
                    },
                )

        if not user.is_guest:
            if user.timezone != start_params.timezone and is_valid_timezone(start_params.timezone):
                user = await self.services.users.update_user(user.id, UpdateUserRequest(timezone=start_params.timezone))

            # Update user streak for daily engagement tracking
            updated_user = await self.services.users.update_user_streak(user.id)
            if updated_user:
                user = updated_user

        # Update PostHog person properties on every visit (after streak update)
        if not user.is_guest:
            has_subscription = await self.services.subscriptions.has_active_subscription(user.id)
            posthog.capture(
                distinct_id=str(user.id),
                event="$set",
                properties={
                    "$set": {
                        "subscription_status": "active" if has_subscription else "free",
                        "current_streak": user.current_streak,
                        "total_active_days": user.total_active_days,
                        "last_seen_at": datetime.now(UTC).isoformat(),
                    },
                    "$set_once": {
                        "signup_date": user.created_at.isoformat() if user.created_at else None,
                    },
                },
            )

        if start_params:
            logger.info(f"Start params: {start_params}")
        return StartData(
            current_user=user,
            inviter=inviter,
            mode=start_params.mode,
        )
