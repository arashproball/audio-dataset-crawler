from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import AudioItemModel


class DatasetExporter:

    def __init__(self, session: Session):
        self.session = session

    def load_items(self) -> pd.DataFrame:
        items = self.session.scalars(
            select(AudioItemModel)
        ).all()

        rows = [
            {
                "id": item.id,
                "source": item.source,
                "content_id": item.content_id,
                "title": item.title,
                "content_url": item.content_url,
                "audio_url": item.audio_url,
                "published_at": item.published_at,
                "tags": item.tags,
                "crawled_at": item.crawled_at,
                "image_url": item.image_url,
                "speaker": item.speaker,
                "audio_title": item.audio_title,
            }
            for item in items
        ]

        return pd.DataFrame(rows)

    def export_csv(self, output_path: str):
        df = self.load_items()

        path = Path(output_path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )

    def export_parquet(self, output_path: str):
        df = self.load_items()

        path = Path(output_path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        df.to_parquet(
            path,
            index=False,
        )