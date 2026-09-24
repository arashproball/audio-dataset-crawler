from sqlalchemy import select

from src.analysis.embedding import AudioEmbeddingModel
from src.database.connection import SessionLocal
from src.database.models import AudioItemModel


embedding_model = AudioEmbeddingModel()

with SessionLocal() as session:
    items = session.scalars(
        select(AudioItemModel).limit(5)
    ).all()

    for item in items:
        print("ID:", item.id)
        print("SOURCE:", item.source)
        print("TEXT:", embedding_model.build_text(item))
        print("-" * 80)