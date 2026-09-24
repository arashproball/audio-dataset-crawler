"""add embedding to audio items

Revision ID: 1089f942620c
Revises: e64389f1b538
Create Date: 2026-09-24 15:14:41.165657

"""
from typing import Sequence, Union
from pgvector.sqlalchemy import Vector
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1089f942620c'
down_revision: Union[str, Sequence[str], None] = 'e64389f1b538'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "audio_items",
        sa.Column(
            "embedding",
            Vector(384),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column(
        "audio_items",
        "embedding",
    )
