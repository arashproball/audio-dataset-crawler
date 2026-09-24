"""remove sources and use source directly

Revision ID: e64389f1b538
Revises:
Create Date: 2026-09-24 11:23:52.301963
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e64389f1b538"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add source columns.
    op.add_column(
        "audio_items",
        sa.Column("source", sa.String(), nullable=True),
    )

    op.add_column(
        "crawl_runs",
        sa.Column("source", sa.String(), nullable=True),
    )

    # Copy source names from the existing sources table.
    op.execute(
        """
        UPDATE audio_items
        SET source = sources.name
        FROM sources
        WHERE audio_items.source_id = sources.id
        """
    )

    op.execute(
        """
        UPDATE crawl_runs
        SET source = sources.name
        FROM sources
        WHERE crawl_runs.source_id = sources.id
        """
    )

    # Remove the old unique constraint before removing source_id.
    op.drop_constraint(
        "uq_audio_source_audio_url",
        "audio_items",
        type_="unique",
    )

    # Remove foreign keys.
    op.drop_constraint(
        "audio_items_source_id_fkey",
        "audio_items",
        type_="foreignkey",
    )

    op.drop_constraint(
        "crawl_runs_source_id_fkey",
        "crawl_runs",
        type_="foreignkey",
    )

    # Remove source_id columns.
    op.drop_column(
        "audio_items",
        "source_id",
    )

    op.drop_column(
        "crawl_runs",
        "source_id",
    )

    # source is required in the final schema.
    op.alter_column(
        "audio_items",
        "source",
        nullable=False,
    )

    op.alter_column(
        "crawl_runs",
        "source",
        nullable=False,
    )

    # Change published_at from DATE to String.
    op.alter_column(
        "audio_items",
        "published_at",
        existing_type=sa.DATE(),
        type_=sa.String(),
        existing_nullable=True,
    )

    # Create the new unique constraint.
    op.create_unique_constraint(
        "uq_audio_source_audio_url",
        "audio_items",
        ["source", "audio_url"],
    )

    # sources is no longer needed.
    op.drop_table("sources")


def downgrade() -> None:
    """Downgrade schema."""

    raise NotImplementedError(
        "Downgrade is not supported for this migration."
    )