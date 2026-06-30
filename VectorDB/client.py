from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

_CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_data")
_EF = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

_client: chromadb.PersistentClient | None = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=_CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name="elden_ring",
            embedding_function=_EF,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection
