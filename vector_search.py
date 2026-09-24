from src.analysis.embedding import AudioEmbeddingModel
from src.database.connection import SessionLocal
from src.database.vector_repository import VectorRepository


query = "سخنرانی درباره فلسطین و غزه"

embedding_model = AudioEmbeddingModel()

query_embedding = embedding_model.encode(
    "query: " + query
)

with SessionLocal() as session:
    repository = VectorRepository(session)

    results = repository.similarity_search(
        embedding=query_embedding,
        limit=5,
    )

    print()
    print("QUERY:", query)
    print("=" * 80)

    for rank, (item, similarity) in enumerate(results, start=1):
        print()
        print(f"#{rank}")
        print("SIMILARITY:", round(similarity, 4))
        print("SOURCE:", item.source)
        print("TITLE:", item.title)
        print("AUDIO TITLE:", item.audio_title)
        print("SPEAKER:", item.speaker)
        print("URL:", item.content_url)