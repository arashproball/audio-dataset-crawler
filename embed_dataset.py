from src.analysis.embedding import AudioEmbeddingModel
from src.analysis.embedding_service import EmbeddingService
from src.database.connection import SessionLocal


with SessionLocal() as session:
    embedding_model = AudioEmbeddingModel()

    service = EmbeddingService(
        session=session,
        embedding_model=embedding_model,
    )

    processed = service.generate_missing_embeddings()

    print(f"Embeddings generated: {processed}")