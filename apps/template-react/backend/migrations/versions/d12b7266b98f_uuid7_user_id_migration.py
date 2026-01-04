"""uuid7 user_id migration

Revision ID: d12b7266b98f
Revises: e52524211461
Create Date: 2025-11-27 21:30:55.576127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PgUUID


# revision identifiers, used by Alembic.
revision: str = 'd12b7266b98f'
down_revision: Union[str, None] = 'e52524211461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ====================
    # PHASE 1: Add new UUID columns
    # ====================

    # Users table (primary)
    op.add_column('users', sa.Column('user_id_new', PgUUID(as_uuid=True), nullable=True))

    # Core FK tables
    op.add_column('payments', sa.Column('user_id_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('subscriptions', sa.Column('user_id_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('friendships', sa.Column('user_id1_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('friendships', sa.Column('user_id2_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('groups', sa.Column('creator_id_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('group_members', sa.Column('user_id_new', PgUUID(as_uuid=True), nullable=True))
    op.add_column('group_invites', sa.Column('creator_id_new', PgUUID(as_uuid=True), nullable=True))

    # App-specific table (template-react)
    op.add_column('balances', sa.Column('user_id_new', PgUUID(as_uuid=True), nullable=True))

    # Also update referral_code length
    op.alter_column('users', 'referral_code',
                    existing_type=sa.String(32),
                    type_=sa.String(40))

    # ====================
    # PHASE 2: Generate UUIDs for users
    # ====================
    op.execute("""
        UPDATE users
        SET user_id_new = gen_random_uuid()
        WHERE user_id_new IS NULL
    """)

    # ====================
    # PHASE 3: Populate FK columns from mapping
    # ====================
    # Core tables
    op.execute("""
        UPDATE payments p
        SET user_id_new = u.user_id_new
        FROM users u
        WHERE p.user_id = u.user_id
    """)

    op.execute("""
        UPDATE subscriptions s
        SET user_id_new = u.user_id_new
        FROM users u
        WHERE s.user_id = u.user_id
    """)

    op.execute("""
        UPDATE friendships f
        SET user_id1_new = u1.user_id_new,
            user_id2_new = u2.user_id_new
        FROM users u1, users u2
        WHERE f.user_id1 = u1.user_id AND f.user_id2 = u2.user_id
    """)

    op.execute("""
        UPDATE groups g
        SET creator_id_new = u.user_id_new
        FROM users u
        WHERE g.creator_id = u.user_id
    """)

    op.execute("""
        UPDATE group_members gm
        SET user_id_new = u.user_id_new
        FROM users u
        WHERE gm.user_id = u.user_id
    """)

    op.execute("""
        UPDATE group_invites gi
        SET creator_id_new = u.user_id_new
        FROM users u
        WHERE gi.creator_id = u.user_id
    """)

    # App-specific table (template-react)
    op.execute("""
        UPDATE balances b
        SET user_id_new = u.user_id_new
        FROM users u
        WHERE b.user_id = u.user_id
    """)

    # ====================
    # PHASE 4: Drop ALL FK constraints pointing to users
    # ====================
    # Core tables
    op.drop_constraint('payments_user_id_fkey', 'payments', type_='foreignkey')
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_constraint('friendships_user_id1_fkey', 'friendships', type_='foreignkey')
    op.drop_constraint('friendships_user_id2_fkey', 'friendships', type_='foreignkey')
    op.drop_constraint('groups_creator_id_fkey', 'groups', type_='foreignkey')
    op.drop_constraint('group_members_user_id_fkey', 'group_members', type_='foreignkey')
    op.drop_constraint('group_invites_creator_id_fkey', 'group_invites', type_='foreignkey')

    # App-specific table (template-react)
    op.drop_constraint('balances_user_id_fkey', 'balances', type_='foreignkey')

    # ====================
    # PHASE 5: Drop old PK constraints
    # ====================
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.drop_constraint('friendships_pkey', 'friendships', type_='primary')
    op.drop_constraint('group_members_pkey', 'group_members', type_='primary')
    # Note: balances has user_id as PK too
    op.drop_constraint('balances_pkey', 'balances', type_='primary')

    # ====================
    # PHASE 6: Drop old columns
    # ====================
    # Core tables
    op.drop_column('users', 'user_id')
    op.drop_column('payments', 'user_id')
    op.drop_column('subscriptions', 'user_id')
    op.drop_column('friendships', 'user_id1')
    op.drop_column('friendships', 'user_id2')
    op.drop_column('groups', 'creator_id')
    op.drop_column('group_members', 'user_id')
    op.drop_column('group_invites', 'creator_id')

    # App-specific table (template-react)
    op.drop_column('balances', 'user_id')

    # ====================
    # PHASE 7: Rename new columns
    # ====================
    # Core tables
    op.alter_column('users', 'user_id_new', new_column_name='user_id')
    op.alter_column('payments', 'user_id_new', new_column_name='user_id')
    op.alter_column('subscriptions', 'user_id_new', new_column_name='user_id')
    op.alter_column('friendships', 'user_id1_new', new_column_name='user_id1')
    op.alter_column('friendships', 'user_id2_new', new_column_name='user_id2')
    op.alter_column('groups', 'creator_id_new', new_column_name='creator_id')
    op.alter_column('group_members', 'user_id_new', new_column_name='user_id')
    op.alter_column('group_invites', 'creator_id_new', new_column_name='creator_id')

    # App-specific table (template-react)
    op.alter_column('balances', 'user_id_new', new_column_name='user_id')

    # ====================
    # PHASE 8: Set NOT NULL constraints
    # ====================
    # Core tables
    op.alter_column('users', 'user_id', nullable=False)
    op.alter_column('payments', 'user_id', nullable=False)
    op.alter_column('subscriptions', 'user_id', nullable=False)
    op.alter_column('friendships', 'user_id1', nullable=False)
    op.alter_column('friendships', 'user_id2', nullable=False)
    op.alter_column('groups', 'creator_id', nullable=False)
    op.alter_column('group_members', 'user_id', nullable=False)
    op.alter_column('group_invites', 'creator_id', nullable=False)

    # App-specific table (template-react)
    op.alter_column('balances', 'user_id', nullable=False)

    # ====================
    # PHASE 9: Recreate PRIMARY KEY constraints
    # ====================
    op.create_primary_key('users_pkey', 'users', ['user_id'])
    op.create_primary_key('friendships_pkey', 'friendships', ['user_id1', 'user_id2'])
    op.create_primary_key('group_members_pkey', 'group_members', ['group_id', 'user_id'])
    op.create_primary_key('balances_pkey', 'balances', ['user_id'])

    # ====================
    # PHASE 10: Recreate FOREIGN KEY constraints
    # ====================
    # Core tables
    op.create_foreign_key('payments_user_id_fkey', 'payments', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('subscriptions_user_id_fkey', 'subscriptions', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('friendships_user_id1_fkey', 'friendships', 'users', ['user_id1'], ['user_id'])
    op.create_foreign_key('friendships_user_id2_fkey', 'friendships', 'users', ['user_id2'], ['user_id'])
    op.create_foreign_key('groups_creator_id_fkey', 'groups', 'users', ['creator_id'], ['user_id'])
    op.create_foreign_key('group_members_user_id_fkey', 'group_members', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('group_invites_creator_id_fkey', 'group_invites', 'users', ['creator_id'], ['user_id'])

    # App-specific table (template-react)
    op.create_foreign_key('balances_user_id_fkey', 'balances', 'users', ['user_id'], ['user_id'])

    # ====================
    # PHASE 11: Create index for telegram_id lookups
    # ====================
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])


def downgrade() -> None:
    raise NotImplementedError("This migration is not reversible.")
