import json
from pathlib import Path
from .client import get_collection

_DATA_DIR = Path(__file__).parent.parent / "API" / "data"

# (entity_type, filename, description_field)
# description_field=None means title-only embedding
_SOURCES = [
    ("bosses",         "bosses.json",         "description"),
    ("locations",      "locations.json",       "description"),
    ("npcs",           "npcs.json",            "quest_description"),
    ("remembrances",   "remembrances.json",    "description"),
    ("reusable_items", "reusable_items.json",  "description"),
    ("skills",         "skills.json",          "description"),
    ("spells",         "spells.json",          "description"),
    ("summons",        "summons.json",         "description"),
    ("weapons",        "weapons.json",         "description"),
    ("dungeons",       "dungeons.json",        None),
]

# Scalar metadata fields to carry through to search results per entity type
_EXTRA_META: dict[str, list[str]] = {
    "bosses":         ["runes", "location_id"],
    "remembrances":   ["runes", "boss_id"],
    "weapons":        ["is_somber", "class_id"],
    "skills":         ["fp_cost"],
    "spells":         [],
    "summons":        ["fp_cost", "hp_cost"],
    "reusable_items": ["fp_cost"],
    "npcs":           ["initial_location_id"],
    "locations":      [],
    "dungeons":       ["is_legacy", "boss_id"],
}


def populate(force: bool = False) -> int:
    """Embed and upsert all game entities into the Chroma collection.

    Skips if the collection is already populated unless force=True.
    Returns the number of documents upserted.
    """
    collection = get_collection()
    if not force and collection.count() > 0:
        print(f"Chroma already contains {collection.count()} documents — skipping populate.")
        return 0

    total = 0
    for entity_type, filename, desc_field in _SOURCES:
        path = _DATA_DIR / filename
        if not path.exists():
            continue

        entities = json.loads(path.read_text(encoding="utf-8"))
        ids, documents, metadatas = [], [], []

        for entity in entities:
            title = entity.get("title") or ""
            desc = entity.get(desc_field, "") if desc_field else ""
            document = f"{title}\n{desc}".strip() if desc else title
            if not document:
                continue

            doc_id = f"{entity_type}_{entity['id']}"
            meta: dict = {
                "entity_type": entity_type,
                "entity_id": entity["id"],
                "title": title,
            }
            for field in _EXTRA_META.get(entity_type, []):
                val = entity.get(field)
                # Chroma metadata values must be str, int, float, or bool
                if val is not None:
                    meta[field] = val

            ids.append(doc_id)
            documents.append(document)
            metadatas.append(meta)

        if ids:
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            total += len(ids)
            print(f"  Upserted {len(ids)} {entity_type}.")

    print(f"Chroma populated: {total} documents total.")
    return total
