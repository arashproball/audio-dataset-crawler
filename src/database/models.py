from datetime import datetime
from pgvector.sqlalchemy import Vector

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.database.connection import Base


class AudioItemModel(Base):
    __tablename__ = "audio_items"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "audio_url",
            name="uq_audio_source_audio_url",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    content_id: Mapped[int | None]

    title: Mapped[str | None]

    content_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    audio_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    published_at: Mapped[str | None] = mapped_column(
        String,
    )

    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
    )

    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
    )

    speaker: Mapped[str | None] = mapped_column(
        Text,
    )

    audio_title: Mapped[str | None] = mapped_column(
        Text,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    pages_crawled: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    items_found: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    items_inserted: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    items_updated: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    errors: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )