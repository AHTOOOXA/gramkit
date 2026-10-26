"""add marketing_links

Revision ID: a8b46d0f2e93
Revises: e6f24a8b0c57
Create Date: 2026-10-23 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8b46d0f2e93'
down_revision: Union[str, None] = 'e6f24a8b0c57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The DDL of the core MarketingLink model (admin marketing links: one acquisition code per
    # external placement). alerts_sent stays JSON (not JSONB), as the model declares it.
    op.create_table('marketing_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('channel', sa.String(length=120), nullable=True),
    sa.Column('price_rub', sa.Float(), nullable=True),
    sa.Column('published_on', sa.Date(), nullable=True),
    sa.Column('created_by', sa.String(length=128), nullable=True),
    sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('alerts_sent', sa.JSON(), server_default='[]', nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )


def downgrade() -> None:
    op.drop_table('marketing_links')
