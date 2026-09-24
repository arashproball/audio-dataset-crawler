from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import AudioItemModel
from crawlers.base_crawler import AudioItem


class AudioRepository:

    def __init__(self, session: Session):
        self.session = session

    def add_or_update(
            self,
            item: AudioItem,
    ) -> tuple[AudioItemModel, bool]:

        existing = self.session.scalar(
            select(AudioItemModel).where(
                AudioItemModel.source == item.source,
                AudioItemModel.audio_url == item.audio_url,
            )
        )

        if existing is None:
            db_item = AudioItemModel(
                source=item.source,
                content_id=item.content_id,
                title=item.title,
                content_url=item.content_url,
                audio_url=item.audio_url,
                published_at=item.published_at,
                tags=item.tags,
                crawled_at=item.crawled_at,
                image_url=item.image_url,
                speaker=item.speaker,
                audio_title=item.audio_title,
            )

            self.session.add(db_item)
            self.session.flush()

            return db_item, True

        self._fill_missing_fields(
            existing,
            item
        )

        self.session.flush()

        return existing, False

    @staticmethod
    def _fill_missing_fields(
            existing: AudioItemModel,
        item: AudioItem,
    ) -> None:

        fields = [
            "content_id",
            "title",
            "content_url",
            "audio_url",
            "published_at",
            "tags",
            "image_url",
            "speaker",
            "audio_title",
        ]

        for field in fields:
            current_value = getattr(existing, field)
            new_value = getattr(item, field)

            if current_value is None and new_value is not None:
                setattr(existing, field, new_value)