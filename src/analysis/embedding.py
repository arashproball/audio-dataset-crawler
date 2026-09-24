from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-small"


class AudioEmbeddingModel:

    def __init__(self):
        self.model = SentenceTransformer(
            MODEL_NAME
        )

    @staticmethod
    def build_text(item) -> str:
        parts = []

        if item.title:
            parts.append(item.title)

        if item.audio_title:
            parts.append(item.audio_title)

        if item.speaker:
            parts.append(item.speaker)

        if item.tags:
            parts.extend(item.tags)

        return " | ".join(parts)

    def encode(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()