"""reviews

Revision ID: 46d3f1af36cd
Revises: 2ff3fefbaf75
Create Date: 2024-11-29 20:05:44.827372

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "46d3f1af36cd"
down_revision = "2ff3fefbaf75"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pdf_file_path", sa.String(), nullable=False),
        sa.Column(
            "ml_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "frontend_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_reports_id"), table_name="reports")
    op.drop_table("reports")
    # ### end Alembic commands ###
