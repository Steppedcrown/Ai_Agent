"""
Agent loop that generates Elden Ring: Shadow of the Erdtree JSON data files.

Two-agent pattern:
  1. Generator agent — uses the fetch_url tool to pull real data from the Fextralife
     wiki, then produces accurate JSON for each table. Never relies on training
     knowledge alone.
  2. Validator agent — checks FK integrity, schema compliance, item counts, and
     factual accuracy; flags any hallucinated or invented entries as a hard FAIL.

Tables are processed in foreign-key dependency order so that referenced IDs
always exist before they are needed.

Usage:
    pip install anthropic requests python-dotenv
    export ANTHROPIC_API_KEY=your-key
    python generate_data.py
    python generate_data.py --clear       # delete all JSON files in data/ first
    python generate_data.py --overwrite   # regenerate all tables, overwriting existing files
"""

import argparse
import json
import os
import re
from pathlib import Path

import requests as _requests
from dotenv import load_dotenv
import anthropic

load_dotenv(Path(__file__).parent / ".env", override=True)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATA_DIR = Path(__file__).parent / "API" / "data"
SCHEMA_PATH = Path(__file__).parent / "API" / "schema.sql"

# Starting point for all DLC content — agents navigate from here
WIKI_URL = "https://eldenring.wiki.fextralife.com/Shadow+of+the+Erdtree#newcontent"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Web-fetch tool — gives the generator access to live wiki data
# ---------------------------------------------------------------------------

FETCH_TOOL = {
    "name": "fetch_url",
    "description": (
        "Fetch the text content of a webpage. You MUST use this tool to retrieve "
        "real game data from the Elden Ring Fextralife wiki before generating any "
        "entries. Do NOT rely on training knowledge alone — every item name, "
        "description, and stat must come from actual wiki content to avoid hallucination."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL to fetch.",
            }
        },
        "required": ["url"],
    },
}

GENERATOR_SYSTEM = (
    "You are a precise data-extraction agent for an Elden Ring: Shadow of the Erdtree "
    "database. Your only job is to fetch real data from the Fextralife wiki using the "
    "fetch_url tool and return it as accurate, schema-compliant JSON. "
    "NEVER invent, guess, or hallucinate game data. "
    "If you are uncertain about any value, fetch the relevant wiki page to verify it. "
    "The wiki is the single source of truth — not your training data."
)

VALIDATOR_SYSTEM = (
    "You are a strict data-validation agent for an Elden Ring: Shadow of the Erdtree "
    "database. Reject any entry whose name does not correspond to a real, confirmed "
    "Shadow of the Erdtree item. Hallucinated or invented names are always a hard FAIL."
)


def fetch_url(url: str, max_chars: int = 30000) -> str:
    """Fetch a URL and return stripped plain text, truncated to max_chars."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EldenRingDataBot/1.0)"}
    resp = _requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    text = resp.text
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Table definitions — ordered to satisfy FK dependencies.
# max_tokens controls the generator's output budget per table.
# ---------------------------------------------------------------------------

TABLES = [
    {
        "name": "elden_ring",
        "file": "elden_ring.json",
        "max_tokens": 1000,
        "columns": {
            "id": "INTEGER, PK",
            "release_date": "DATE (YYYY-MM-DD)",
            "developer": "VARCHAR(255)",
            "publisher": "VARCHAR(255)",
        },
        "fk_refs": {},
        "hint": (
            "Single entry for the Shadow of the Erdtree DLC. "
            "id=1, release_date=2024-06-21, developer=FromSoftware, "
            "publisher=Bandai Namco Entertainment. No wiki fetching needed."
        ),
    },
    {
        "name": "location",
        "file": "locations.json",
        "max_tokens": 8000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "prev_location_id": "INTEGER, nullable, FK to location(id)",
            "next_location_id": "INTEGER, nullable, FK to location(id)",
        },
        "fk_refs": {"prev_location_id": "location", "next_location_id": "location"},
        "hint": (
            f"Start at {WIKI_URL} to find links to DLC region/location pages, "
            "then fetch those pages for accurate descriptions. "
            "Generate 8-12 major regions from Shadow of the Erdtree. "
            "Include: Gravesite Plain, Scadu Altus, Rauh Ruins, Ancient Ruins of Rauh, "
            "Cerulean Coast, Jagged Peak, Abyssal Woods, Hinterland, Shadow Keep, Enir-Ilim. "
            "prev_location_id / next_location_id form a rough progression chain. "
            "First location: prev=null. Last location: next=null."
        ),
    },
    {
        "name": "npc",
        "file": "npcs.json",
        "max_tokens": 8000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "quest_description": "TEXT",
            "initial_location_id": "INTEGER, FK to location(id)",
        },
        "fk_refs": {"initial_location_id": "location"},
        "hint": (
            f"Fetch {WIKI_URL} then follow links to DLC NPC and quest pages "
            "for accurate quest summaries and starting locations. "
            "Generate all named quest NPCs from the DLC: Needle Knight Leda, Hornsent, "
            "Thiollier, Moore, Ansbach, Freyja, Dryleaf Dane, Igon, and any others. "
            "initial_location_id must reference an id from the locations data."
        ),
    },
    {
        "name": "boss",
        "file": "bosses.json",
        "max_tokens": 12000,
        "columns": {
            "id": "INTEGER, PK",
            "game_id": "INTEGER, nullable, FK to elden_ring(id)",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "runes": "INTEGER",
        },
        "fk_refs": {"game_id": "elden_ring", "location_id": "location"},
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Bosses and filter for "
            "Shadow of the Erdtree DLC entries. "
            "Generate all notable DLC bosses — at minimum: Divine Beast Dancing Lion, "
            "Rellana Twin Moon Knight, Messmer the Impaler, Metyr Mother of Fingers, "
            "Putrescent Knight, Romina Saint of the Bud, Commander Gaius, "
            "Scadutree Avatar, Midra Lord of Frenzied Flame, Bayle the Dread, "
            "Promised Consort Radahn, plus optional field bosses. "
            "game_id=1. location_id must reference the locations data. "
            "runes must be the exact in-game rune reward listed on the wiki."
        ),
    },
    {
        "name": "dungeon",
        "file": "dungeons.json",
        "max_tokens": 10000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "location_id": "INTEGER, FK to location(id)",
            "is_legacy": "BOOLEAN",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
        },
        "fk_refs": {"location_id": "location", "boss_id": "boss"},
        "hint": (
            f"Fetch {WIKI_URL} then follow DLC dungeon and area links for accurate data. "
            "Legacy dungeons (is_legacy=true): Belurat Tower Settlement, Castle Ensis, "
            "Shadow Keep, Enir-Ilim, Stone Coffin Fissure. "
            "Also include catacombs, caves, fissures, and ruin sub-areas (is_legacy=false). "
            "boss_id references the boss found at the end of that dungeon."
        ),
    },
    {
        "name": "remembrance",
        "file": "remembrances.json",
        "max_tokens": 8000,
        "columns": {
            "id": "INTEGER, PK",
            "boss_id": "INTEGER, FK to boss(id)",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "runes": "INTEGER",
        },
        "fk_refs": {"boss_id": "boss"},
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Remembrances and filter for "
            "DLC entries. Only major story bosses drop remembrances. "
            "Include remembrances for: Dancing Lion, Rellana, Messmer, Romina, Midra, "
            "Bayle, Promised Consort Radahn, Metyr, Putrescent Knight, Scadutree Avatar. "
            "boss_id must reference an id from the bosses data. "
            "runes is the sell value from the wiki (typically 30000-50000)."
        ),
    },
    {
        "name": "weapon_class",
        "file": "weapon_classes.json",
        "max_tokens": 4000,
        "columns": {
            "id": "INTEGER, PK",
            "class_name": "VARCHAR(255)",
        },
        "fk_refs": {},
        "hint": (
            "Generate all weapon and shield classes needed for DLC weapons and shields. "
            "Weapon classes: Greatsword, Katana, Light Greatsword, Backhand Blade, "
            "Great Katana, Beast Claw, Throwing Blade, Perfume Bottle, Hand-to-Hand Arts, "
            "Colossal Sword, Curved Sword, Straight Sword, Curved Greatsword, "
            "Thrusting Sword, Heavy Thrusting Sword, Axe, Greataxe, Hammer, Flail, "
            "Spear, Great Spear, Halberd, Reaper, Whip, Fist, Claw, Torch, Staff, Seal. "
            "Shield classes: Small Shield, Medium Shield, Greatshield, Thrusting Shield."
        ),
    },
    {
        "name": "weapon",
        "file": "weapons.json",
        "max_tokens": 32000,
        "columns": {
            "id": "INTEGER, PK",
            "class_id": "INTEGER, FK to weapon_class(id)",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "is_somber": "BOOLEAN",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "class_id": "weapon_class",
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Weapons and "
            "https://eldenring.wiki.fextralife.com/Shields, filtering for items "
            "tagged as Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 70 new DLC weapons AND all 10 new DLC shields "
            "(80 total entries). Do not stop early — fetch multiple pages as needed. "
            "is_somber=true for unique/boss weapons upgraded with Somber Smithing Stones. "
            "remembrance_id is set only if the weapon comes from a remembrance. "
            "Set EXACTLY ONE of boss_id, location_id, dungeon_id, npc_id to indicate "
            "where the weapon is obtained; all others must be null. "
            "All IDs must reference existing data."
        ),
    },
    {
        "name": "spell",
        "file": "spells.json",
        "max_tokens": 24000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Sorceries and "
            "https://eldenring.wiki.fextralife.com/Incantations, filtering for "
            "Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 14 new DLC sorceries AND all 28 new DLC incantations "
            "(42 total entries). Do not stop early. "
            "Fetch individual spell pages for accurate in-game descriptions. "
            "Set EXACTLY ONE source FK (remembrance_id, boss_id, location_id, "
            "dungeon_id, or npc_id). All IDs must reference existing data."
        ),
    },
    {
        "name": "skill",
        "file": "skills.json",
        "max_tokens": 20000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "fp_cost": "INTEGER",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Ashes+of+War and filter for "
            "Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 25 new DLC Ashes of War. Do not stop early. "
            "fp_cost is the exact FP cost from the wiki. "
            "Set EXACTLY ONE source FK. All IDs must reference existing data."
        ),
    },
    {
        "name": "consumable",
        "file": "consumables.json",
        "max_tokens": 16000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "fp_cost": "INTEGER",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            f"Fetch {WIKI_URL} and follow links to DLC consumable and craftable pages. "
            "Also fetch https://eldenring.wiki.fextralife.com/Consumables and "
            "https://eldenring.wiki.fextralife.com/Craftable+Items, filtering for "
            "Shadow of the Erdtree additions. "
            "Include all new consumables and craftables added in the DLC: aromatics, "
            "boluses, pots, greases, arrows, and similar single-use items. "
            "fp_cost=0 for all consumables (they do not cost FP to use). "
            "Set EXACTLY ONE source FK indicating where the item or its recipe is first "
            "obtained. All IDs must reference existing data."
        ),
    },
    {
        "name": "summon",
        "file": "summons.json",
        "max_tokens": 16000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "fp_cost": "INTEGER, nullable",
            "hp_cost": "INTEGER, nullable",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Spirit+Ashes and filter for "
            "Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 20 new DLC Spirit Ashes. Do not stop early. "
            "fp_cost is the FP required to summon (from the wiki). "
            "hp_cost is null for all Spirit Ashes (HP cost only applies to Mimic Tear). "
            "Set EXACTLY ONE source FK. All IDs must reference existing data."
        ),
    },
    {
        "name": "talisman",
        "file": "talismans.json",
        "max_tokens": 24000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Talismans and filter for "
            "Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 39 new DLC talismans. Do not stop early. "
            "Fetch individual talisman pages for accurate in-game descriptions and "
            "effect text. "
            "remembrance_id is set only if the talisman comes from a remembrance. "
            "Set EXACTLY ONE source FK. All IDs must reference existing data."
        ),
    },
    {
        "name": "armor_set",
        "file": "armor_sets.json",
        "max_tokens": 8000,
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
        },
        "fk_refs": {},
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Armor+Sets and filter for "
            "Shadow of the Erdtree DLC additions. "
            "You MUST generate ALL 30 new DLC armor sets. Do not stop early. "
            "Each entry has only id and title (the set name, e.g. 'Blackthorn Set'). "
            "Do NOT include descriptions, FKs, or any other fields."
        ),
    },
    {
        "name": "armor_piece",
        "file": "armor_pieces.json",
        "max_tokens": 64000,
        "columns": {
            "id": "INTEGER, PK",
            "set_id": "INTEGER, nullable, FK to armor_set(id)",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "remembrance_id": "INTEGER, nullable, FK to remembrance(id)",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
            "location_id": "INTEGER, nullable, FK to location(id)",
            "dungeon_id": "INTEGER, nullable, FK to dungeon(id)",
            "npc_id": "INTEGER, nullable, FK to npc(id)",
        },
        "fk_refs": {
            "set_id": "armor_set",
            "remembrance_id": "remembrance",
            "boss_id": "boss",
            "location_id": "location",
            "dungeon_id": "dungeon",
            "npc_id": "npc",
        },
        "hint": (
            "Fetch https://eldenring.wiki.fextralife.com/Armor+Sets and individual "
            "set pages to get every piece for all 30 DLC armor sets. "
            "Each set typically has 4 pieces: Helm, Armor (chest), Gauntlets, Greaves. "
            "Some sets may have fewer — only include pieces that actually exist in-game. "
            "Generate a separate row for every individual piece across all sets. "
            "set_id must reference the matching id from the armor_set data. "
            "Set EXACTLY ONE acquisition FK (location_id, dungeon_id, boss_id, or npc_id) "
            "indicating where the set is obtained; all pieces in the same set share the "
            "same acquisition FK. remembrance_id is null for nearly all armor. "
            "All IDs must reference existing data."
        ),
    },
]

# Junction tables — processed after their parent tables
JUNCTION_TABLES = [
    {
        "name": "spell_class",
        "file": "spell_classes.json",
        "max_tokens": 4000,
        "columns": {
            "spell_id": "INTEGER, FK to spell(id), part of composite PK",
            "class_id": "INTEGER, FK to weapon_class(id), part of composite PK",
        },
        "fk_refs": {"spell_id": "spell", "class_id": "weapon_class"},
        "hint": (
            "Map each spell to its catalyst class using weapon_class ids. "
            "Sorceries map to Staff, incantations map to Seal. "
            "A spell can have multiple classes if it can be cast with either."
        ),
    },
    {
        "name": "skill_weapon_class",
        "file": "skill_weapon_classes.json",
        "max_tokens": 8000,
        "columns": {
            "skill_id": "INTEGER, FK to skill(id), part of composite PK",
            "class_id": "INTEGER, FK to weapon_class(id), part of composite PK",
        },
        "fk_refs": {"skill_id": "skill", "class_id": "weapon_class"},
        "hint": (
            "Map each Ash of War to the weapon classes it can be applied to. "
            "A skill can apply to multiple weapon classes. "
            "Use the wiki pages already fetched to determine compatibility."
        ),
    },
]


def parse_json(text: str):
    """Extract and parse a JSON array or object from an LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()
    for i, ch in enumerate(text):
        if ch in ("[", "{"):
            close = "]" if ch == "[" else "}"
            depth = 0
            for j in range(i, len(text)):
                if text[j] == ch:
                    depth += 1
                elif text[j] == close:
                    depth -= 1
                if depth == 0:
                    return json.loads(text[i : j + 1])
    return json.loads(text)


def load_existing_data() -> dict[str, list[dict]]:
    """Load all previously generated JSON data files."""
    data = {}
    for table in TABLES + JUNCTION_TABLES:
        path = DATA_DIR / table["file"]
        if path.exists():
            with open(path) as f:
                data[table["name"]] = json.load(f)
    return data


def build_context(table: dict, existing_data: dict[str, list[dict]]) -> str:
    """Build a context string showing all referenced table data for the generator."""
    context_parts = []
    for fk_col, ref_table in table["fk_refs"].items():
        if ref_table in existing_data:
            rows = existing_data[ref_table]
            id_title_pairs = [
                f"  id={row['id']}: {row.get('title') or row.get('class_name') or str(row)}"
                for row in rows
            ]
            context_parts.append(
                f"Available {ref_table} records (use ONLY these ids for {fk_col}):\n"
                + "\n".join(id_title_pairs)
            )
    return "\n\n".join(context_parts)


def generate_data(table: dict, existing_data: dict[str, list[dict]]) -> list[dict]:
    """Run the generator agent with web-fetch tool use to produce JSON for a table."""
    schema_desc = "\n".join(f"  {col}: {typ}" for col, typ in table["columns"].items())
    context = build_context(table, existing_data)
    max_tokens = table.get("max_tokens", 16000)

    prompt = f"""Generate accurate JSON data for the "{table['name']}" table from Elden Ring: Shadow of the Erdtree.

WIKI STARTING POINT: {WIKI_URL}
Use the fetch_url tool to retrieve real data from the wiki BEFORE generating any entries.

SCHEMA:
{schema_desc}

{f"AVAILABLE REFERENCE DATA (use ONLY these IDs for FK fields):{chr(10)}{context}" if context else "No foreign key dependencies."}

INSTRUCTIONS:
{table['hint']}

CRITICAL RULES:
- You MUST call fetch_url at least once before producing output. Do NOT skip this.
- Return ONLY a valid JSON array of objects. No markdown, no explanation — raw JSON only.
- Every non-null FK id MUST exactly match an id from the reference data above.
- IDs must be sequential integers starting from 1.
- Descriptions must be lore-accurate and sourced from the wiki.
- Nullable fields must be present and set to null when not applicable — do NOT omit them.
- Boolean fields must be true or false (not 0/1 or strings).
- Do NOT include any fields not listed in the schema.
- Do NOT hallucinate item names, stats, or descriptions. Every entry must be a real game item confirmed on the wiki.

Fetch the relevant wiki pages now, then return the complete JSON array:"""

    messages = [{"role": "user", "content": prompt}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=GENERATOR_SYSTEM,
            tools=[FETCH_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    url = block.input.get("url", "")
                    print(f"    Fetching: {url}")
                    try:
                        content = fetch_url(url)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        })
                    except Exception as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error fetching URL: {exc}",
                            "is_error": True,
                        })
            messages.append({"role": "user", "content": tool_results})

        else:
            text = next((b.text for b in response.content if b.type == "text"), "")
            return parse_json(text)


def validate_data(
    table: dict, data: list[dict], existing_data: dict[str, list[dict]]
) -> dict:
    """Run the validator agent to check generated data for accuracy and integrity."""
    schema_desc = "\n".join(f"  {col}: {typ}" for col, typ in table["columns"].items())
    context = build_context(table, existing_data)

    prompt = f"""Validate the generated data for the "{table['name']}" table.

SCHEMA:
{schema_desc}

{f"REFERENCE DATA (valid FK targets):{chr(10)}{context}" if context else "No foreign key dependencies."}

GENERATED DATA:
{json.dumps(data, indent=2)}

Check ALL of the following:
1. SCHEMA COMPLIANCE: Every required column is present, correct types, no extra fields, nullable fields present (not omitted).
2. FK INTEGRITY: Every non-null FK value must exactly match an id from the reference data. Flag every broken FK by row id and field name.
3. DATA INTEGRITY: IDs are unique and sequential. No duplicate titles.
4. FACTUAL ACCURACY: Every item name must be a real, confirmed Shadow of the Erdtree game item. Hallucinated or invented names are a hard FAIL.
5. COUNT: Cross-check the number of records against the expected count in the instructions for this table. Too few records is a FAIL.

Respond ONLY with a JSON object:
{{
  "valid": true/false,
  "issues": ["list every issue found — be specific: field name, row id, actual vs expected value"],
  "severity": "pass" | "warn" | "fail"
}}

"pass" = data is accurate, complete, and all FKs are valid.
"warn" = minor issues only (small description inaccuracy, missing optional data) but data is otherwise usable.
"fail" = any of: broken FKs, missing required fields, wrong record count, or any hallucinated/invented item names.

Return ONLY the JSON object:"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=VALIDATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    return parse_json(text)


def save_data(table: dict, data: list[dict]) -> None:
    """Write generated data to a JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / table["file"]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {len(data)} records to {path}")


def process_table(
    table: dict, existing_data: dict[str, list[dict]], max_retries: int = 2
) -> list[dict]:
    """Generate and validate data for a single table, retrying on failure."""
    print(f"\n{'='*60}")
    print(f"Processing: {table['name']}")
    print(f"{'='*60}")

    data = []
    for attempt in range(1, max_retries + 1):
        print(f"\n  Attempt {attempt}/{max_retries}")

        print("  Generating data (fetching wiki)...")
        data = generate_data(table, existing_data)
        print(f"  Generated {len(data)} records")

        print("  Validating...")
        result = validate_data(table, data, existing_data)

        severity = result.get("severity", "fail")
        issues = result.get("issues", [])

        if severity == "pass":
            print("  Validation: PASS")
            return data
        elif severity == "warn":
            print(f"  Validation: WARN — {len(issues)} minor issue(s)")
            for issue in issues:
                print(f"    - {issue}")
            return data
        else:
            print(f"  Validation: FAIL — {len(issues)} issue(s)")
            for issue in issues:
                print(f"    - {issue}")
            if attempt < max_retries:
                print("  Retrying...")

    print("  Using last generated data despite validation issues")
    return data


def main():
    parser = argparse.ArgumentParser(description="Elden Ring: Shadow of the Erdtree — Data Generator")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--clear",
        action="store_true",
        help="Delete all JSON files in data/ before generating.",
    )
    group.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate all tables even if their JSON files already exist.",
    )
    args = parser.parse_args()

    print("Elden Ring: Shadow of the Erdtree — Data Generator")
    print("=" * 60)

    if args.clear:
        print("--clear: removing all JSON files from data/")
        for f in DATA_DIR.glob("*.json"):
            f.unlink()
            print(f"  Deleted {f.name}")

    existing_data = load_existing_data()
    print(f"Loaded existing data for: {list(existing_data.keys()) or 'none'}")

    all_tables = TABLES + JUNCTION_TABLES

    for table in all_tables:
        if not args.overwrite and not args.clear and table["name"] in existing_data:
            print(
                f"\nSkipping {table['name']} — already exists "
                f"({len(existing_data[table['name']])} records)"
            )
            continue

        data = process_table(table, existing_data)
        save_data(table, data)
        existing_data[table["name"]] = data

    print(f"\n{'='*60}")
    print("Generation complete!")
    print(f"{'='*60}")
    for table in all_tables:
        if table["name"] in existing_data:
            print(f"  {table['name']}: {len(existing_data[table['name']])} records")


if __name__ == "__main__":
    main()
