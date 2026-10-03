
from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the embedding model once per running process."""
    return SentenceTransformer(MODEL_NAME)


def topic_similarity_score(topic_a: str, topic_b: str) -> float:
    """Return cosine similarity between two topic descriptions."""
    if not topic_a.strip() or not topic_b.strip():
        return 0.0

    model = _get_model()

    embeddings = model.encode(
        [topic_a, topic_b],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    # Normalized embeddings make their dot product cosine similarity.
    return float(embeddings[0] @ embeddings[1])