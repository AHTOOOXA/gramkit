from core.infrastructure.i18n import t
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.schemas.start import StartData, StartParamsRequest
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.base import BaseService

logger = get_logger(__name__)


class StartService(BaseService):
    async def process_start(self, user: UserSchema, start_params: StartParamsRequest) -> StartData:
        logger.info(f"Processing start with params: {start_params}")

        # may work multiple times
        logger.info(
            f"User {user.id} opened app, new: {user.is_new}, created_at: {user.created_at}, updated_at: {user.updated_at}"
        )

        referal_id = start_params.referal_id if start_params.referal_id else None
        if user.is_new and not user.is_guest:
            if referal_id:
                await self.services.users.process_referal(referal_id=referal_id, user_id=user.id)
            extra_text = ""
            if referal_id:
                extra_text += f"🎉 Источник: {referal_id} "
            # if inviter:  # ugly for now
            #     extra_text += f"invite {inviter.username}"
            logger.info(f"New user {user.id} registered, {extra_text}")  # TODO: add more info to logs
            message = t("admin.new_user_notification", "ru").format(
                username=user.username, user_id=user.id, extra_text=extra_text
            )
            await self.services.messages.queue_admin_broadcast(message)
            posthog.capture(
                distinct_id=user.id,
                event="new_user_registered",
                properties={
                    "$set": {"username": user.username},
                    "$set_once": {"referal_id": referal_id, "invite_code": start_params.invite_code},
                },
            )

        else:
            if referal_id:
                logger.info(f"User {user.id} opened app again, from ref {referal_id}")
            else:
                logger.info(f"User {user.id} opened app again")

        inviter = None
        if start_params.invite_code:
            inviter = await self.services.invites.process_invite(start_params.invite_code, user.id)

        if not user.is_guest:
            if user.timezone != start_params.timezone:
                user = await self.services.users.update_user(user.id, UpdateUserRequest(timezone=start_params.timezone))

            # Update user streak for daily engagement tracking
            updated_user = await self.services.users.update_user_streak(user.id)
            if updated_user:
                user = updated_user

        if start_params:
            logger.info(f"Start params: {start_params}")
        return StartData(
            current_user=user,
            inviter=inviter,
            mode=start_params.mode,
        )
