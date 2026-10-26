"""add promotional_broadcasts

Revision ID: e6f24a8b0c57
Revises: c4d02e6f8a35
Create Date: 2026-10-23 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6f24a8b0c57'
down_revision: Union[str, None] = 'c4d02e6f8a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The DDL of the core PromotionalBroadcast model: created_by_user_id holds the
    # creator's Telegram id; time_slot is a non-native enum (varchar(7), no CHECK).
    op.create_table('promotional_broadcasts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_type', sa.String(length=20), nullable=False),
    sa.Column('message_text', sa.Text(), nullable=True),
    sa.Column('message_html', sa.Text(), nullable=True),
    sa.Column('media_file_id', sa.String(length=255), nullable=True),
    sa.Column('caption', sa.Text(), nullable=True),
    sa.Column('caption_html', sa.Text(), nullable=True),
    sa.Column('media_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('has_text_formatting', sa.Boolean(), nullable=False),
    sa.Column('has_caption_formatting', sa.Boolean(), nullable=False),
    sa.Column('time_slot', sa.Enum('MORNING', 'EVENING', name='notificationtimeslot', native_enum=False), nullable=False),
    sa.Column('deadline', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('keyboard_type', sa.String(length=50), nullable=True),
    sa.Column('keyboard_button_text', sa.String(length=255), nullable=True),
    sa.Column('created_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('sent_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('success_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('fail_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('cycles_run', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('target_filter', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('promotional_broadcasts')
