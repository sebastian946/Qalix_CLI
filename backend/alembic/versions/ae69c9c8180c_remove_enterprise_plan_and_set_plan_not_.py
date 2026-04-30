"""remove_enterprise_plan_and_set_plan_not_null

Revision ID: ae69c9c8180c
Revises: 8169d8a33fe4
Create Date: 2026-04-30 09:08:35.527655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae69c9c8180c'
down_revision: Union[str, Sequence[str], None] = '8169d8a33fe4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set default and backfill any NULLs before enforcing NOT NULL
    op.execute("UPDATE users SET plan = 'FREE' WHERE plan IS NULL OR plan = 'ENTERPRISE'")
    op.execute("UPDATE subscriptions SET plan = 'FREE' WHERE plan = 'ENTERPRISE'")

    # Recreate the plan enum without ENTERPRISE (PostgreSQL does not support DROP VALUE)
    op.execute("ALTER TYPE plan RENAME TO plan_old")
    op.execute("CREATE TYPE plan AS ENUM ('FREE', 'PRO')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN plan TYPE plan "
        "USING plan::text::plan"
    )
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN plan TYPE plan "
        "USING plan::text::plan"
    )
    op.execute("DROP TYPE plan_old")

    # Enforce NOT NULL with default on users.plan
    op.alter_column("users", "plan", nullable=False, server_default="FREE")


def downgrade() -> None:
    op.execute("ALTER TYPE plan RENAME TO plan_old")
    op.execute("CREATE TYPE plan AS ENUM ('FREE', 'PRO', 'ENTERPRISE')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN plan TYPE plan "
        "USING plan::text::plan"
    )
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN plan TYPE plan "
        "USING plan::text::plan"
    )
    op.execute("DROP TYPE plan_old")

    op.alter_column("users", "plan", nullable=True, server_default=None)
