import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

import httpx
from mcp.server.fastmcp import FastMCP

_VECTORDB_ENABLED = os.environ.get("VECTORDB_ENABLED", "").lower() in ("1", "true", "yes")
if _VECTORDB_ENABLED:
    from VectorDB.search import semantic_search as _semantic_search, VALID_ENTITY_TYPES
else:
    _semantic_search = None
    VALID_ENTITY_TYPES = set()

mcp = FastMCP("elden-ring-mcp")
_API = os.environ.get("MCP_API_URL", "http://localhost:8000")


def _get(path: str, **params) -> dict:
    filtered = {k: v for k, v in params.items() if v is not None and v != ""}
    r = httpx.get(f"{_API}{path}", params=filtered)
    r.raise_for_status()
    return r.json()


# ── Bosses ────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_bosses(search: str = "") -> dict:
    """List bosses from Elden Ring: Shadow of the Erdtree, optionally filtered by name.

    Args:
        search: Partial name to search for (case-insensitive). Leave empty to list all.
    Returns a dict with 'data' list of boss objects (id, title, description, runes, location_id).
    """
    return _get("/bosses", search=search, limit=500)


@mcp.tool()
def get_boss(boss_id: int) -> dict:
    """Return detailed information about a single boss by ID.

    Args:
        boss_id: Numeric boss ID (use list_bosses to find IDs).
    Returns a dict with 'data' containing id, title, description, runes, game_id, location_id.
    """
    return _get(f"/bosses/{boss_id}")


# ── Locations ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_locations(search: str = "") -> dict:
    """List the major regions / locations in the Land of Shadow DLC.

    Args:
        search: Partial location name to search for. Leave empty to list all.
    Returns a dict with 'data' list of location objects (id, title, description,
    prev_location_id, next_location_id).
    """
    return _get("/locations", search=search, limit=500)


@mcp.tool()
def get_location(location_id: int) -> dict:
    """Return detailed information about a single location by ID.

    Args:
        location_id: Numeric location ID (use list_locations to find IDs).
    Returns a dict with 'data' containing id, title, description, and adjacent location IDs.
    """
    return _get(f"/locations/{location_id}")


# ── NPCs ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_npcs(search: str = "") -> dict:
    """List NPCs and questline characters in the Shadow of the Erdtree DLC.

    Args:
        search: Partial NPC name to search for. Leave empty to list all.
    Returns a dict with 'data' list of NPC objects (id, title, quest_description, initial_location_id).
    """
    return _get("/npcs", search=search, limit=500)


@mcp.tool()
def get_npc(npc_id: int) -> dict:
    """Return detailed information about a single NPC by ID.

    Args:
        npc_id: Numeric NPC ID (use list_npcs to find IDs).
    Returns a dict with 'data' containing id, title, quest_description, and initial_location_id.
    """
    return _get(f"/npcs/{npc_id}")


# ── Dungeons ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_dungeons(search: str = "") -> dict:
    """List dungeons and legacy dungeons found in the Shadow of the Erdtree DLC.

    Args:
        search: Partial dungeon name to search for. Leave empty to list all.
    Returns a dict with 'data' list of dungeon objects (id, title, location_id, is_legacy, boss_id).
    """
    return _get("/dungeons", search=search, limit=500)


@mcp.tool()
def get_dungeon(dungeon_id: int) -> dict:
    """Return detailed information about a single dungeon by ID.

    Args:
        dungeon_id: Numeric dungeon ID (use list_dungeons to find IDs).
    Returns a dict with 'data' containing id, title, location_id, is_legacy flag, and boss_id.
    """
    return _get(f"/dungeons/{dungeon_id}")


# ── Remembrances ──────────────────────────────────────────────────────────────

@mcp.tool()
def list_remembrances(search: str = "") -> dict:
    """List boss remembrances dropped by major bosses in Shadow of the Erdtree.

    Args:
        search: Partial remembrance title to search for. Leave empty to list all.
    Returns a dict with 'data' list of remembrance objects (id, title, description, boss_id, runes).
    """
    return _get("/remembrances", search=search, limit=500)


@mcp.tool()
def get_remembrance(remembrance_id: int) -> dict:
    """Return detailed information about a single remembrance by ID.

    Args:
        remembrance_id: Numeric remembrance ID (use list_remembrances to find IDs).
    Returns a dict with 'data' containing id, title, description, boss_id, and rune value.
    """
    return _get(f"/remembrances/{remembrance_id}")


# ── Weapon Classes ────────────────────────────────────────────────────────────

@mcp.tool()
def list_weapon_classes(search: str = "") -> dict:
    """List weapon classes in Shadow of the Erdtree (includes all 33 classes).

    Args:
        search: Partial class name to search for. Leave empty to list all.
    Returns a dict with 'data' list of weapon class objects (id, class_name).
    """
    return _get("/weapon-classes", search=search, limit=500)


@mcp.tool()
def get_weapon_class(weapon_class_id: int) -> dict:
    """Return information about a single weapon class by ID.

    Args:
        weapon_class_id: Numeric weapon class ID (use list_weapon_classes to find IDs).
    Returns a dict with 'data' containing id and class_name.
    """
    return _get(f"/weapon-classes/{weapon_class_id}")


# ── Weapons ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_weapons(search: str = "") -> dict:
    """List weapons obtainable in Shadow of the Erdtree.

    Args:
        search: Partial weapon name to search for. Leave empty to list all.
    Returns a dict with 'data' list of weapon objects (id, title, description, class_id,
    is_somber, and source FK: remembrance_id / boss_id / location_id / dungeon_id / npc_id).
    """
    return _get("/weapons", search=search, limit=500)


@mcp.tool()
def get_weapon(weapon_id: int) -> dict:
    """Return detailed information about a single weapon by ID.

    Args:
        weapon_id: Numeric weapon ID (use list_weapons to find IDs).
    Returns a dict with 'data' containing id, title, description, class_id, is_somber flag,
    and source FKs (remembrance_id, boss_id, location_id, dungeon_id, npc_id).
    """
    return _get(f"/weapons/{weapon_id}")


# ── Spells ────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_spells(search: str = "") -> dict:
    """List sorceries and incantations introduced in Shadow of the Erdtree.

    Args:
        search: Partial spell name to search for. Leave empty to list all.
    Returns a dict with 'data' list of spell objects (id, title, description, and source FKs).
    """
    return _get("/spells", search=search, limit=500)


@mcp.tool()
def get_spell(spell_id: int) -> dict:
    """Return detailed information about a single spell by ID.

    Args:
        spell_id: Numeric spell ID (use list_spells to find IDs).
    Returns a dict with 'data' containing id, title, description, and source FKs
    (remembrance_id, boss_id, location_id, dungeon_id, npc_id).
    """
    return _get(f"/spells/{spell_id}")


# ── Skills (Ashes of War) ─────────────────────────────────────────────────────

@mcp.tool()
def list_skills(search: str = "") -> dict:
    """List Ashes of War / weapon skills introduced in Shadow of the Erdtree.

    Args:
        search: Partial skill name to search for. Leave empty to list all.
    Returns a dict with 'data' list of skill objects (id, title, description, fp_cost, and source FKs).
    """
    return _get("/skills", search=search, limit=500)


@mcp.tool()
def get_skill(skill_id: int) -> dict:
    """Return detailed information about a single skill / Ash of War by ID.

    Args:
        skill_id: Numeric skill ID (use list_skills to find IDs).
    Returns a dict with 'data' containing id, title, description, fp_cost, and source FKs
    (remembrance_id, boss_id, location_id, dungeon_id, npc_id).
    """
    return _get(f"/skills/{skill_id}")


# ── Consumables ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_consumables(search: str = "") -> dict:
    """List consumable items obtainable in Shadow of the Erdtree (e.g. crafted throwing pots,
    boluses, and other single-use or limited supplies).

    Args:
        search: Partial item name to search for. Leave empty to list all.
    Returns a dict with 'data' list of consumable objects (id, title, description,
    and source FKs: location_id, dungeon_id, npc_id, boss_id).
    """
    return _get("/consumables", search=search, limit=500)


@mcp.tool()
def get_consumable(consumable_id: int) -> dict:
    """Return detailed information about a single consumable item by ID.

    Args:
        consumable_id: Numeric consumable ID (use list_consumables to find IDs).
    Returns a dict with 'data' containing id, title, description, and source FKs
    (location_id, dungeon_id, npc_id, boss_id).
    """
    return _get(f"/consumables/{consumable_id}")


# ── Talismans ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_talismans(search: str = "") -> dict:
    """List talismans introduced in Shadow of the Erdtree that grant passive bonuses.

    Args:
        search: Partial talisman name to search for. Leave empty to list all.
    Returns a dict with 'data' list of talisman objects (id, title, description,
    and source FKs: location_id, dungeon_id, npc_id, boss_id, remembrance_id).
    """
    return _get("/talismans", search=search, limit=500)


@mcp.tool()
def get_talisman(talisman_id: int) -> dict:
    """Return detailed information about a single talisman by ID.

    Args:
        talisman_id: Numeric talisman ID (use list_talismans to find IDs).
    Returns a dict with 'data' containing id, title, description, and source FKs
    (location_id, dungeon_id, npc_id, boss_id, remembrance_id).
    """
    return _get(f"/talismans/{talisman_id}")


# ── Armor Sets ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_armor_sets(search: str = "") -> dict:
    """List armor sets introduced in Shadow of the Erdtree.

    Args:
        search: Partial armor set name to search for. Leave empty to list all.
    Returns a dict with 'data' list of armor set objects (id, title, description,
    and source FKs: location_id, dungeon_id, npc_id, boss_id).
    """
    return _get("/armor-sets", search=search, limit=500)


@mcp.tool()
def get_armor_set(armor_set_id: int) -> dict:
    """Return detailed information about a single armor set by ID.

    Args:
        armor_set_id: Numeric armor set ID (use list_armor_sets to find IDs).
    Returns a dict with 'data' containing id, title, description, and source FKs
    (location_id, dungeon_id, npc_id, boss_id).
    """
    return _get(f"/armor-sets/{armor_set_id}")


# ── Armor Pieces ──────────────────────────────────────────────────────────────

@mcp.tool()
def list_armor_pieces(search: str = "") -> dict:
    """List individual armor pieces (helms, chest pieces, gauntlets, leg armor) from
    Shadow of the Erdtree.

    Args:
        search: Partial armor piece name to search for. Leave empty to list all.
    Returns a dict with 'data' list of armor piece objects (id, title, description,
    slot, set_id).
    """
    return _get("/armor-pieces", search=search, limit=500)


@mcp.tool()
def get_armor_piece(armor_piece_id: int) -> dict:
    """Return detailed information about a single armor piece by ID.

    Args:
        armor_piece_id: Numeric armor piece ID (use list_armor_pieces to find IDs).
    Returns a dict with 'data' containing id, title, description, slot, and set_id.
    """
    return _get(f"/armor-pieces/{armor_piece_id}")


# ── Summons (Spirit Ashes) ────────────────────────────────────────────────────

@mcp.tool()
def list_summons(search: str = "") -> dict:
    """List spirit ash summons obtainable in Shadow of the Erdtree.

    Args:
        search: Partial summon name to search for. Leave empty to list all.
    Returns a dict with 'data' list of summon objects (id, title, description,
    fp_cost, hp_cost, source FKs).
    """
    return _get("/summons", search=search, limit=500)


@mcp.tool()
def get_summon(summon_id: int) -> dict:
    """Return detailed information about a single spirit ash summon by ID.

    Args:
        summon_id: Numeric summon ID (use list_summons to find IDs).
    Returns a dict with 'data' containing id, title, description, fp_cost, hp_cost,
    and source FKs (boss_id, location_id, dungeon_id, npc_id).
    """
    return _get(f"/summons/{summon_id}")


# ── Vector / Semantic Search ──────────────────────────────────────────────────

@mcp.tool()
def semantic_search(query: str, entity_type: str = "", n_results: int = 5) -> list:
    """Search across all Elden Ring DLC data using semantic similarity.

    Use this when the user asks a conceptual or descriptive question that doesn't
    map cleanly to a specific boss or item name — e.g. "what weapons scale with
    intelligence", "fire-resistant bosses", "NPCs with tragic questlines", or
    "skills good for strength builds".

    Args:
        query:       Natural-language description of what to search for.
        entity_type: Optional. Restrict results to one entity type. Must be one of:
                     bosses, locations, npcs, remembrances, consumables, talismans,
                     armor_sets, armor_pieces, skills, spells, summons, weapons, dungeons.
                     Leave empty to search across all types.
        n_results:   Number of results to return (default 5, max 20).

    Returns a list of matching entities, each with: score (0–1 similarity),
    entity_type, entity_id, title, document (text used for embedding), and
    any extra metadata (runes, fp_cost, etc.).
    """
    if not _VECTORDB_ENABLED or _semantic_search is None:
        return [{"error": "Vector search is disabled. Set VECTORDB_ENABLED=1 to enable it."}]
    n_results = min(max(1, n_results), 20)
    return _semantic_search(query, entity_type=entity_type, n_results=n_results)


if __name__ == "__main__":
    mcp.run()
