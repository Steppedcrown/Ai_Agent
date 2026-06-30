from .client import get_collection

VALID_ENTITY_TYPES = {
    "bosses", "locations", "npcs", "remembrances",
    "reusable_items", "skills", "spells", "summons", "weapons", "dungeons",
}


def semantic_search(query: str, entity_type: str = "", n_results: int = 5) -> list[dict]:
    """Return top-n entities semantically similar to query.

    Args:
        query:       Natural-language search string.
        entity_type: Optional filter — one of the VALID_ENTITY_TYPES strings.
                     Empty string searches across all entity types.
        n_results:   Maximum number of results to return.

    Returns a list of dicts with keys: score, entity_type, entity_id, title,
    document, plus any extra metadata fields (runes, fp_cost, etc.).
    """
    collection = get_collection()
    where = {"entity_type": entity_type} if entity_type in VALID_ENTITY_TYPES else None

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count() or 1),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Chroma cosine distance: 0 = identical, 2 = opposite → convert to [0,1] similarity
        hits.append({
            "score": round(1 - dist, 4),
            "entity_type": meta.get("entity_type"),
            "entity_id": meta.get("entity_id"),
            "title": meta.get("title"),
            "document": doc,
            **{k: v for k, v in meta.items() if k not in ("entity_type", "entity_id", "title")},
        })

    return hits
