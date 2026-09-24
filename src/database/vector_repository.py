from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import AudioItemModel


class VectorRepository:

    def __init__(self, session: Session):
        self.session = session

    def similarity_search(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[tuple[AudioItemModel, float]]:

        distance = AudioItemModel.embedding.cosine_distance(embedding)

        statement = (
            select(
                AudioItemModel,
                (1 - distance).label("similarity"),
            )
            .where(AudioItemModel.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )

        results = self.session.execute(statement).all()

        return [
            (item, float(similarity))
            for item, similarity in results
        ]