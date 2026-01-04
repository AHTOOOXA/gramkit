"""rename_user_id_to_id

Revision ID: 7119b088df7c
Revises: 148636cfdfb0
Create Date: 2025-11-29 00:26:17.927035

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7119b088df7c"
down_revision: Union[str, None] = "148636cfdfb0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop all foreign key constraints referencing users.user_id
    op.drop_constraint("balances_user_id_fkey", "balances", type_="foreignkey")
    op.drop_constraint("friendships_user_id1_fkey", "friendships", type_="foreignkey")
    op.drop_constraint("friendships_user_id2_fkey", "friendships", type_="foreignkey")
    op.drop_constraint("group_invites_creator_id_fkey", "group_invites", type_="foreignkey")
    op.drop_constraint("group_members_user_id_fkey", "group_members", type_="foreignkey")
    op.drop_constraint("groups_creator_id_fkey", "groups", type_="foreignkey")
    op.drop_constraint("payments_user_id_fkey", "payments", type_="foreignkey")
    op.drop_constraint("subscriptions_user_id_fkey", "subscriptions", type_="foreignkey")

    # Step 2: Drop the primary key constraint on users.user_id
    op.drop_constraint("users_pkey", "users", type_="primary")

    # Step 3: Rename the column from user_id to id
    op.alter_column("users", "user_id", new_column_name="id")

    # Step 4: Recreate the primary key constraint on users.id
    op.create_primary_key("users_pkey", "users", ["id"])

    # Step 5: Recreate all foreign key constraints pointing to users.id
    op.create_foreign_key("balances_user_id_fkey", "balances", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("friendships_user_id1_fkey", "friendships", "users", ["user_id1"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("friendships_user_id2_fkey", "friendships", "users", ["user_id2"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("group_invites_creator_id_fkey", "group_invites", "users", ["creator_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("group_members_user_id_fkey", "group_members", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("groups_creator_id_fkey", "groups", "users", ["creator_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("payments_user_id_fkey", "payments", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("subscriptions_user_id_fkey", "subscriptions", "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    # Step 1: Drop all foreign key constraints referencing users.id
    op.drop_constraint("balances_user_id_fkey", "balances", type_="foreignkey")
    op.drop_constraint("friendships_user_id1_fkey", "friendships", type_="foreignkey")
    op.drop_constraint("friendships_user_id2_fkey", "friendships", type_="foreignkey")
    op.drop_constraint("group_invites_creator_id_fkey", "group_invites", type_="foreignkey")
    op.drop_constraint("group_members_user_id_fkey", "group_members", type_="foreignkey")
    op.drop_constraint("groups_creator_id_fkey", "groups", type_="foreignkey")
    op.drop_constraint("payments_user_id_fkey", "payments", type_="foreignkey")
    op.drop_constraint("subscriptions_user_id_fkey", "subscriptions", type_="foreignkey")

    # Step 2: Drop the primary key constraint on users.id
    op.drop_constraint("users_pkey", "users", type_="primary")

    # Step 3: Rename the column from id back to user_id
    op.alter_column("users", "id", new_column_name="user_id")

    # Step 4: Recreate the primary key constraint on users.user_id
    op.create_primary_key("users_pkey", "users", ["user_id"])

    # Step 5: Recreate all foreign key constraints pointing to users.user_id
    op.create_foreign_key("balances_user_id_fkey", "balances", "users", ["user_id"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("friendships_user_id1_fkey", "friendships", "users", ["user_id1"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("friendships_user_id2_fkey", "friendships", "users", ["user_id2"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("group_invites_creator_id_fkey", "group_invites", "users", ["creator_id"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("group_members_user_id_fkey", "group_members", "users", ["user_id"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("groups_creator_id_fkey", "groups", "users", ["creator_id"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("payments_user_id_fkey", "payments", "users", ["user_id"], ["user_id"], ondelete="CASCADE")
    op.create_foreign_key("subscriptions_user_id_fkey", "subscriptions", "users", ["user_id"], ["user_id"], ondelete="CASCADE")
