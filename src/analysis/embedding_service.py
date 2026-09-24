from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import AudioItemModel
from src.analysis.embedding import AudioEmbeddingModel


class EmbeddingService:

    def __init__(
        self,
        session: Session,
        embedding_model: AudioEmbeddingModel,
    ):
        self.session = session
        self.embedding_model = embedding_model

    def generate_missing_embeddings(self) -> int:
        items = self.session.scalars(
            select(AudioItemModel).where(
                AudioItemModel.embedding.is_(None)
            )
        ).all()

        processed = 0

        for item in items:
            text = self.embedding_model.build_text(item)

            if not text.strip():
                continue

            item.embedding = self.embedding_model.encode(text)
            processed += 1

        self.session.commit()

        return processed