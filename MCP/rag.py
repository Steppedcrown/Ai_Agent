from __future__ import annotations

import re
import numpy as np
from sentence_transformers import SentenceTransformer

# Loaded once at import time; the model (~80 MB) is cached after first download
_model = SentenceTransformer("all-MiniLM-L6-v2")


def _chunk(text: str) -> list[str]:
    # Split on ## section headers so each chunk is a self-contained section
    parts = re.split(r"\n(?=##\s)", text.strip())
    chunks = [p.strip() for p in parts if p.strip()]
    # Fall back to paragraph splitting if the file has no ## headers
    if len(chunks) <= 1:
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    return chunks


def build_index(text: str) -> tuple[list[str], np.ndarray]:
    """Chunk *text* and return (chunks, L2-normalised embedding matrix)."""
    chunks = _chunk(text)
    embeddings = _model.encode(chunks, normalize_embeddings=True)
    return chunks, embeddings


def retrieve(query: str, chunks: list[str], embeddings: np.ndarray, k: int = 2) -> list[str]:
    """Return the top-k chunks most semantically similar to *query*."""
    q_emb = _model.encode([query], normalize_embeddings=True)
    # Dot product of normalised vectors == cosine similarity
    scores = (embeddings @ q_emb.T).squeeze()
    top_k = min(k, len(chunks))
    indices = np.argsort(scores)[::-1][:top_k]
    return [chunks[i] for i in indices]
