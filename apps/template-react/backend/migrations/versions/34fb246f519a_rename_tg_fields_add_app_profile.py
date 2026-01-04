"""rename_tg_fields_add_app_profile

Revision ID: 34fb246f519a
Revises: 93157a7be162
Create Date: 2025-11-24 15:49:11.111651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34fb246f519a'
down_revision: Union[str, None] = '93157a7be162'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new columns (non-breaking)
    op.add_column('users', sa.Column('display_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))

    # Step 2: Remove old email indexes before adding unique constraint
    op.drop_index('ix_users_email', table_name='users', postgresql_where='email IS NOT NULL')
    op.drop_index('ix_users_email_verified', table_name='users', postgresql_where='email_verified = true')

    # Step 3: Add UNIQUE constraint on email
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # Step 4: Rename TG fields with tg_ prefix
    op.alter_column('users', 'first_name', new_column_name='tg_first_name')
    op.alter_column('users', 'last_name', new_column_name='tg_last_name')
    op.alter_column('users', 'username', new_column_name='tg_username')
    op.alter_column('users', 'is_premium', new_column_name='tg_is_premium')
    op.alter_column('users', 'photo_url', new_column_name='tg_photo_url')
    op.alter_column('users', 'is_bot', new_column_name='tg_is_bot')
    op.alter_column('users', 'added_to_attachment_menu', new_column_name='tg_added_to_attachment_menu')
    op.alter_column('users', 'allows_write_to_pm', new_column_name='tg_allows_write_to_pm')

    # Step 5: Rename app fields to be primary (swap order to avoid conflicts)
    # First rename language_code to tg_language_code
    op.alter_column('users', 'language_code', new_column_name='tg_language_code')
    # Then rename app_language_code to language_code
    op.alter_column('users', 'app_language_code', new_column_name='language_code')
    # Change type of language_code from unlimited VARCHAR to String(10)
    op.alter_column('users', 'language_code',
               existing_type=sa.VARCHAR(),
               type_=sa.String(length=10),
               existing_nullable=True)

    # Rename app_username to username
    op.alter_column('users', 'app_username', new_column_name='username')

    # Step 6: Fix typo in referral_code
    op.alter_column('users', 'referal_code', new_column_name='referral_code')

    # Step 7: Adjust column sizes
    op.alter_column('users', 'timezone',
               existing_type=sa.VARCHAR(length=64),
               type_=sa.String(length=50),
               existing_nullable=True)
    op.alter_column('users', 'tg_photo_url',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.String(length=500),
               existing_nullable=True)

    # Step 8: Add UNIQUE constraint on username (app handle)
    op.create_unique_constraint('uq_users_username', 'users', ['username'])

    # Step 9: Add UNIQUE constraint on referral_code
    op.create_unique_constraint('uq_users_referral_code', 'users', ['referral_code'])

    # Step 10: Populate new fields from existing data
    op.execute("""
        UPDATE users SET
            display_name = COALESCE(
                NULLIF(CONCAT_WS(' ', tg_first_name, tg_last_name), ''),
                username,
                'User'
            ),
            avatar_url = tg_photo_url
        WHERE display_name IS NULL
    """)


def downgrade() -> None:
    # Clear populated fields
    op.execute("UPDATE users SET display_name = NULL, avatar_url = NULL")

    # Drop new unique constraints
    op.drop_constraint('uq_users_referral_code', 'users', type_='unique')
    op.drop_constraint('uq_users_username', 'users', type_='unique')

    # Restore column sizes
    op.alter_column('users', 'tg_photo_url',
               existing_type=sa.String(length=500),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)
    op.alter_column('users', 'timezone',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=64),
               existing_nullable=True)

    # Reverse typo fix
    op.alter_column('users', 'referral_code', new_column_name='referal_code')

    # Reverse app field renames
    op.alter_column('users', 'username', new_column_name='app_username')
    op.alter_column('users', 'language_code',
               existing_type=sa.String(length=10),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.alter_column('users', 'language_code', new_column_name='app_language_code')
    op.alter_column('users', 'tg_language_code', new_column_name='language_code')

    # Reverse TG field renames
    op.alter_column('users', 'tg_allows_write_to_pm', new_column_name='allows_write_to_pm')
    op.alter_column('users', 'tg_added_to_attachment_menu', new_column_name='added_to_attachment_menu')
    op.alter_column('users', 'tg_is_bot', new_column_name='is_bot')
    op.alter_column('users', 'tg_photo_url', new_column_name='photo_url')
    op.alter_column('users', 'tg_is_premium', new_column_name='is_premium')
    op.alter_column('users', 'tg_username', new_column_name='username')
    op.alter_column('users', 'tg_last_name', new_column_name='last_name')
    op.alter_column('users', 'tg_first_name', new_column_name='first_name')

    # Drop unique constraint on email and restore indexes
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.execute("""
        CREATE UNIQUE INDEX ix_users_email_verified
        ON users(LOWER(email))
        WHERE email_verified = true
    """)
    op.execute("""
        CREATE INDEX ix_users_email
        ON users(LOWER(email))
        WHERE email IS NOT NULL
    """)

    # Drop new columns
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'display_name')
