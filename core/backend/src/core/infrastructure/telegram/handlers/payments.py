"""Generic payment handlers for Telegram Stars payments.

These handlers process Telegram payment callbacks and can be reused
across different TMA applications.
"""

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from core.infrastructure.database.models.enums import PaymentProvider
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = Router()


@router.pre_checkout_query()
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, services, bot):
    """
    Handle pre-checkout query for Telegram Stars payments.

    This handler is called when user confirms payment in Telegram
    but before the actual payment is processed. It validates the payment
    and approves/rejects the checkout.

    Args:
        pre_checkout_query: Telegram pre-checkout query event
        services: RequestsService instance (injected by middleware)
        bot: Bot instance (injected by middleware)

    Flow:
        1. Extract payment ID from invoice payload
        2. Validate payment exists in database
        3. Verify payment belongs to requesting user
        4. Process pre-checkout callback via payment service
        5. Approve or reject the checkout

    Payload format:
        invoice_payload: "payment_{uuid}"
    """
    try:
        logger.info(
            f"Pre-checkout query received: {pre_checkout_query.id} for payload: {pre_checkout_query.invoice_payload}"
        )

        # Extract payment ID from the payload
        if not pre_checkout_query.invoice_payload.startswith("payment_"):
            logger.error(f"Invalid payment payload: {pre_checkout_query.invoice_payload}")
            await pre_checkout_query.answer(ok=False, error_message="Invalid payment reference")
            return

        try:
            payment_id = pre_checkout_query.invoice_payload.replace("payment_", "")
            # Validate that it looks like a UUID (basic check)
            if len(payment_id) != 36 or payment_id.count("-") != 4:
                raise ValueError(f"Payment ID doesn't look like a UUID: {payment_id}")
        except ValueError as e:
            logger.error(f"Could not parse payment ID from payload: {pre_checkout_query.invoice_payload} - {e}")
            await pre_checkout_query.answer(ok=False, error_message="Invalid payment reference")
            return

        # Check if payment exists and is valid
        payment = await services.repo.payments.get_by_id(payment_id)
        if not payment:
            logger.error(f"Payment {payment_id} not found")
            await pre_checkout_query.answer(ok=False, error_message="Payment not found")
            return

        # Check if payment is for the correct user
        # Need to fetch user record to get telegram_id for comparison
        user = await services.users.get_user_by_id(payment.user_id)
        if not user:
            logger.error(f"User not found for payment {payment_id}")
            await pre_checkout_query.answer(ok=False, error_message="User not found")
            return

        if user.telegram_id != pre_checkout_query.from_user.id:
            logger.error(f"Payment {payment_id} does not belong to user {pre_checkout_query.from_user.id}")
            await pre_checkout_query.answer(ok=False, error_message="Unauthorized payment")
            return

        # Process the pre-checkout callback through payments service
        payload = {
            "pre_checkout_query": {
                "id": pre_checkout_query.id,
                "from": pre_checkout_query.from_user.model_dump(),
                "currency": pre_checkout_query.currency,
                "total_amount": pre_checkout_query.total_amount,
                "invoice_payload": pre_checkout_query.invoice_payload,
            },
            "payload": pre_checkout_query.invoice_payload,
        }

        await services.payments.process_callback(payload, PaymentProvider.TELEGRAM_STARS.value)

        # Approve the payment
        await pre_checkout_query.answer(ok=True)
        logger.info(f"Pre-checkout query {pre_checkout_query.id} approved for payment {payment_id}")

    except Exception as e:
        logger.error(f"Error handling pre-checkout query {pre_checkout_query.id}: {e}")
        await pre_checkout_query.answer(ok=False, error_message="Payment processing error")


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, services):
    """
    Handle successful Telegram Stars payment.

    This handler is called after the payment is successfully processed by Telegram.
    It finalizes the payment in the database and grants the purchased items/subscriptions.

    Args:
        message: Message containing successful_payment data
        services: RequestsService instance (injected by middleware)

    Flow:
        1. Extract payment ID from invoice payload
        2. Check if this is a subscription renewal (recurring_used flag)
        3. Process successful payment callback via payment service
        4. Service handles: payment status update, subscription creation, balance updates

    Payload format:
        successful_payment.invoice_payload: "payment_{uuid}"
        successful_payment.recurring_used: bool (True for auto-renewals)
    """
    try:
        successful_payment = message.successful_payment
        logger.info(
            f"Successful payment received for user {message.from_user.id}: {successful_payment.invoice_payload}"
        )
        logger.info(
            f"Full successful_payment details: currency={successful_payment.currency}, "
            f"amount={successful_payment.total_amount}, "
            f"charge_id={getattr(successful_payment, 'telegram_payment_charge_id', 'N/A')}"
        )

        # Extract payment ID from the payload
        if not successful_payment.invoice_payload.startswith("payment_"):
            logger.error(f"Invalid payment payload: {successful_payment.invoice_payload}")
            return

        try:
            payment_id = successful_payment.invoice_payload.replace("payment_", "")
            # Validate that it looks like a UUID (basic check)
            if len(payment_id) != 36 or payment_id.count("-") != 4:
                raise ValueError(f"Payment ID doesn't look like a UUID: {payment_id}")
        except ValueError as e:
            logger.error(f"Could not parse payment ID from payload: {successful_payment.invoice_payload} - {e}")
            return

        # Check if this is a renewal payment
        # Telegram sends recurring_used flag for subscription renewals
        is_renewal = getattr(successful_payment, "recurring_used", False)

        # Process the successful payment callback through payments service
        payload = {
            "successful_payment": {
                "currency": successful_payment.currency,
                "total_amount": successful_payment.total_amount,
                "invoice_payload": successful_payment.invoice_payload,
                "telegram_payment_charge_id": successful_payment.telegram_payment_charge_id,
                "provider_payment_charge_id": successful_payment.provider_payment_charge_id,
                "recurring_used": is_renewal,  # Include renewal flag
            },
            "payload": successful_payment.invoice_payload,
            "from_user": message.from_user.model_dump(),
            "recurring_used": is_renewal,  # Also at top level for easier access
        }

        await services.payments.process_callback(payload, PaymentProvider.TELEGRAM_STARS.value)

        # TODO: Make better confirmation message to user
        # # Send appropriate confirmation message based on payment type
        # if is_renewal:
        #     confirmation_msg = (
        #         "🔄 Subscription renewed! Your Telegram Stars subscription has been automatically renewed.\n\n"
        #         "Thank you for continuing to use our service! ⭐"
        #     )
        # else:
        #     confirmation_msg = (
        #         "🎉 Payment successful! Your purchase has been processed.\n\n"
        #         "Thank you for using Telegram Stars! ⭐"
        #     )

        # await message.answer(confirmation_msg)

        logger.info(f"Successful payment processed for payment {payment_id}")

    except Exception as e:
        logger.error(f"Error handling successful payment for user {message.from_user.id}: {e}", exc_info=True)
        logger.error(
            f"Payment details: {successful_payment.invoice_payload}, "
            f"charge_id: {getattr(successful_payment, 'telegram_payment_charge_id', 'N/A')}"
        )
        await message.answer(
            "❌ There was an error processing your payment confirmation. "
            "Please contact support if your payment was charged but you didn't receive your purchase."
        )
