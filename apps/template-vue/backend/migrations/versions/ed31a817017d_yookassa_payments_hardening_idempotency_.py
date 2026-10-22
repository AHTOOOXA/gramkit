"""yookassa payments hardening (idempotency, dunning, indexes)

Revision ID: ed31a817017d
Revises: cc1f66a220fd
Create Date: 2026-06-18 12:12:07.421156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed31a817017d'
down_revision: Union[str, None] = 'cc1f66a220fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mirrors the reference app's three hardening migrations, combined (the DDL targets the shared core
    # payments/subscriptions tables). All additive + nullable/defaulted -> backwards compatible.

    # #1 payment idempotency key + partial unique index (allows a dunning retry after FAILED).
    op.add_column('payments', sa.Column('idempotency_key', sa.String(length=64), nullable=True))
    op.create_index(
        'uq_payment_idempotency_key', 'payments', ['idempotency_key'], unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL AND status NOT IN ('FAILED', 'CANCELED')"),
    )

    # #3 dunning columns (server_default backfills existing rows).
    op.add_column('subscriptions', sa.Column('failed_renewal_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('subscriptions', sa.Column('last_renewal_attempt_at', sa.TIMESTAMP(timezone=True), nullable=True))

    # #8 typed payment_method_id, backfilled from recurring_details JSON (json -> use ->>).
    op.add_column('subscriptions', sa.Column('payment_method_id', sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE subscriptions
        SET payment_method_id = recurring_details->>'payment_method_id'
        WHERE payment_method_id IS NULL
          AND recurring_details->>'payment_method_id' IS NOT NULL
        """
    )

    # #4 one live subscription per user: collapse any pre-existing duplicates (keep latest) before
    # creating the partial unique index so it can't fail on dirty data.
    op.execute(
        """
        UPDATE subscriptions s
        SET status = 'EXPIRED', canceled_at = now()
        WHERE s.status IN ('ACTIVE', 'PAST_DUE', 'PENDING')
          AND s.id NOT IN (
            SELECT DISTINCT ON (user_id) id
            FROM subscriptions
            WHERE status IN ('ACTIVE', 'PAST_DUE', 'PENDING')
            ORDER BY user_id, end_date DESC, created_at DESC
          )
        """
    )
    op.create_index(
        'uq_subscription_active_user', 'subscriptions', ['user_id'], unique=True,
        postgresql_where=sa.text("status IN ('ACTIVE', 'PAST_DUE', 'PENDING')"),
    )


def downgrade() -> None:
    op.drop_index('uq_subscription_active_user', table_name='subscriptions', postgresql_where=sa.text("status IN ('ACTIVE', 'PAST_DUE', 'PENDING')"))
    op.drop_column('subscriptions', 'payment_method_id')
    op.drop_column('subscriptions', 'last_renewal_attempt_at')
    op.drop_column('subscriptions', 'failed_renewal_count')
    op.drop_index('uq_payment_idempotency_key', table_name='payments', postgresql_where=sa.text("idempotency_key IS NOT NULL AND status NOT IN ('FAILED', 'CANCELED')"))
    op.drop_column('payments', 'idempotency_key')
