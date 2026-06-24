"""
Agent loop that generates Elden Ring: Shadow of the Erdtree JSON data files.

Two-agent pattern:
  1. Generator agent — produces JSON data for each table using Claude
  2. Validator agent — checks FK integrity, schema compliance, and factual accuracy

Tables are processed in foreign-key dependency order so that referenced IDs
always exist before they're needed.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=your-key
    python generate_data.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import anthropic

load_dotenv(Path(__file__).parent / ".env")

DATA_DIR = Path(__file__).parent / "API" / "data"
SCHEMA_PATH = Path(__file__).parent / "API" / "schema.sql"

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Table definitions: columns, types, FK targets, and generation hints.
# Ordered so that every FK target is generated before the table that uses it.
# ---------------------------------------------------------------------------

TABLES = [
    {
        "name": "elden_ring",
        "file": "elden_ring.json",
        "columns": {
            "id": "INTEGER, PK",
            "release_date": "DATE (YYYY-MM-DD)",
            "developer": "VARCHAR(255)",
            "publisher": "VARCHAR(255)",
        },
        "fk_refs": {},
        "hint": (
            "There is one entry: the Shadow of the Erdtree DLC. "
            "id=1, release_date=2024-06-21, developer=FromSoftware, publisher=Bandai Namco Entertainment."
        ),
    },
    {
        "name": "location",
        "file": "locations.json",
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "prev_location_id": "INTEGER, nullable, FK to location(id)",
            "next_location_id": "INTEGER, nullable, FK to location(id)",
        },
        "fk_refs": {"prev_location_id": "location", "next_location_id": "location"},
        "hint": (
            "Generate 8-12 major locations from Elden Ring: Shadow of the Erdtree DLC. "
            "Include places like Gravesite Plain, Scadu Altus, Rauh Ruins, "
            "Ancient Ruins of Rauh, Cerulean Coast, Jagged Peak, Abyssal Woods, "
            "Hinterland, Shadow Keep, Enir-Ilim. "
            "prev_location_id and next_location_id form a rough progression chain. "
            "The first location should have prev_location_id=null, "
            "and the last should have next_location_id=null."
        ),
    },
    {
        "name": "npc",
        "file": "npcs.json",
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "quest_description": "TEXT",
            "initial_location_id": "INTEGER, FK to location(id)",
        },
        "fk_refs": {"initial_location_id": "location"},
        "hint": (
            "Generate 5-8 NPCs from Shadow of the Erdtree. "
            "Include characters like Needle Knight Leda, Hornsent, Thiollier, "
            "Moore, Ansbach, Freyja, Dryleaf Dane, Igon. "
            "initial_location_id must reference an id from the locations data."
        ),
    },
    {
        "name": "boss",
        "file": "bosses.json",
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
            "Generate 10-15 bosses from Shadow of the Erdtree. "
            "Include: Divine Beast Dancing Lion, Rellana Twin Moon Knight, "
            "Messmer the Impaler, Metyr Mother of Fingers, Putrescent Knight, "
            "Romina Saint of the Bud, Commander Gaius, Scadutree Avatar, "
            "Midra Lord of Frenzied Flame, Bayle the Dread, "
            "Promised Consort Radahn. "
            "game_id should be 1 (the DLC). "
            "location_id must reference an id from the locations data. "
            "Use the actual in-game rune rewards."
        ),
    },
    {
        "name": "dungeon",
        "file": "dungeons.json",
        "columns": {
            "id": "INTEGER, PK",
            "title": "VARCHAR(255)",
            "location_id": "INTEGER, FK to location(id)",
            "is_legacy": "BOOLEAN",
            "boss_id": "INTEGER, nullable, FK to boss(id)",
        },
        "fk_refs": {"location_id": "location", "boss_id": "boss"},
        "hint": (
            "Generate 6-10 dungeons from Shadow of the Erdtree. "
            "Include places like Belurat Tower Settlement, Castle Ensis, "
            "Shadow Keep, Specimen Storehouse, Stone Coffin Fissure, "
            "Ruined Forge Lava Intake, Darklight Catacombs, Fog Rift Catacombs. "
            "is_legacy=true for major legacy dungeons (Belurat, Castle Ensis, Shadow Keep). "
            "boss_id references the boss found at the end of that dungeon."
        ),
    },
    {
        "name": "remembrance",
        "file": "remembrances.json",
        "columns": {
            "id": "INTEGER, PK",
            "boss_id": "INTEGER, FK to boss(id)",
            "title": "VARCHAR(255)",
            "description": "TEXT",
            "runes": "INTEGER",
        },
        "fk_refs": {"boss_id": "boss"},
        "hint": (
            "Generate remembrances for the major bosses that drop them. "
            "Not every boss drops a remembrance — only the significant ones. "
            "Include remembrances for bosses like Dancing Lion, Rellana, Messmer, "
            "Romina, Midra, Bayle, Radahn, Metyr. "
            "boss_id must reference an id from the bosses data. "
            "runes is the sell value of the remembrance item (usually 30000-50000)."
        ),
    },
    {
        "name": "weapon_class",
        "file": "weapon_classes.json",
        "columns": {
            "id": "INTEGER, PK",
            "class_name": "VARCHAR(255)",
        },
        "fk_refs": {},
        "hint": (
            "Generate weapon classes relevant to the DLC. "
            "Include: Greatsword, Katana, Light Greatsword, Backhand Blade, "
            "Great Katana, Thrusting Shield, Beast Claw, Throwing Blade, "
            "Perfume Bottle, Hand-to-Hand Arts, Colossal Sword, Curved Sword, "
            "Straight Sword, Staff, Seal."
        ),
    },
    {
        "name": "weapon",
        "file": "weapons.json",
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
            "Generate 8-12 notable weapons from Shadow of the Erdtree. "
            "Include remembrance weapons and interesting finds. "
            "Examples: Greatsword of Radahn (Light), Poleblade of the Bud, "
            "Star-Lined Sword, Milady, Euporia, Shadow Sunflower Blossom, "
            "Ancient Meteoric Ore Greatsword, Dryleaf Arts. "
            "is_somber=true for unique/boss weapons. "
            "Set remembrance_id if the weapon comes from a remembrance. "
            "Only ONE of boss_id, location_id, dungeon_id, npc_id should be set "
            "(the source of the weapon). All FK ids must reference existing data."
        ),
    },
    {
        "name": "spell",
        "file": "spells.json",
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
            "Generate 5-8 spells/incantations from Shadow of the Erdtree. "
            "Include sorceries and incantations. "
            "Examples: Messmer's Orb, Midra's Flame of Frenzy, "
            "Land of Shadow, Dragonbolt of Florissax, Minor Erdtree. "
            "Set remembrance_id if it comes from a remembrance. "
            "Only ONE source FK should be set. All FK ids must reference existing data."
        ),
    },
    {
        "name": "skill",
        "file": "skills.json",
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
            "Generate 5-8 weapon skills (Ashes of War) from Shadow of the Erdtree. "
            "Examples: Wing Stance, Dryleaf Whirlwind, Palm Blast, "
            "Fire Serpent, Swift Slash, Savage Lion's Claw. "
            "fp_cost is the FP cost to use the skill. "
            "Only ONE source FK should be set. All FK ids must reference existing data."
        ),
    },
    {
        "name": "reusable_item",
        "file": "reusable_items.json",
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
            "Generate 4-6 reusable items from Shadow of the Erdtree. "
            "These are items that can be used repeatedly. "
            "Examples: Iris of Grace, Iris of Occultation, Scadutree Fragment, "
            "Revered Spirit Ash, Aged One's Exultation. "
            "fp_cost=0 for items that don't cost FP. "
            "Only ONE source FK should be set. All FK ids must reference existing data."
        ),
    },
    {
        "name": "summon",
        "file": "summons.json",
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
            "Generate 4-6 spirit ash summons from Shadow of the Erdtree. "
            "Examples: Solitary Furnace Golem, Demi-Human Swordsman Yosh, "
            "Horned Warrior, Fire Knight Hilde, Taylew the Golem Smith. "
            "fp_cost is the FP to summon, hp_cost is the HP cost (usually null). "
            "Only ONE source FK should be set. All FK ids must reference existing data."
        ),
    },
]

# Junction tables handled separately after their parents
JUNCTION_TABLES = [
    {
        "name": "spell_class",
        "file": "spell_classes.json",
        "columns": {
            "spell_id": "INTEGER, FK to spell(id), part of composite PK",
            "class_id": "INTEGER, FK to weapon_class(id), part of composite PK",
        },
        "fk_refs": {"spell_id": "spell", "class_id": "weapon_class"},
        "hint": (
            "Map each spell to its class type using weapon_class ids. "
            "Sorceries map to Staff, incantations map to Seal. "
            "A spell can have multiple classes."
        ),
    },
    {
        "name": "skill_weapon_class",
        "file": "skill_weapon_classes.json",
        "columns": {
            "skill_id": "INTEGER, FK to skill(id), part of composite PK",
            "class_id": "INTEGER, FK to weapon_class(id), part of composite PK",
        },
        "fk_refs": {"skill_id": "skill", "class_id": "weapon_class"},
        "hint": (
            "Map each skill/ash of war to the weapon classes it can be applied to. "
            "A skill can apply to multiple weapon classes."
        ),
    },
]


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
    """Build context string showing all referenced table data for the generator."""
    context_parts = []
    referenced_tables = set(table["fk_refs"].values())
    for ref_table in referenced_tables:
        if ref_table in existing_data:
            ids = [row["id"] for row in existing_data[ref_table]]
            titles = [row.get("title") or row.get("class_name") or str(row) for row in existing_data[ref_table]]
            id_title_pairs = [f"  id={i}: {t}" for i, t in zip(ids, titles)]
            context_parts.append(
                f"Available {ref_table} records (use ONLY these ids for {ref_table} FKs):\n"
                + "\n".join(id_title_pairs)
            )
    return "\n\n".join(context_parts)


def generate_data(table: dict, existing_data: dict[str, list[dict]]) -> list[dict]:
    """Call the generator agent to produce JSON data for a table."""
    schema_desc = "\n".join(f"  {col}: {typ}" for col, typ in table["columns"].items())
    context = build_context(table, existing_data)

    prompt = f"""Generate accurate JSON data for the "{table['name']}" table from Elden Ring: Shadow of the Erdtree DLC.

SCHEMA:
{schema_desc}

{f"AVAILABLE REFERENCE DATA (FK targets):{chr(10)}{context}" if context else "No foreign key dependencies."}

INSTRUCTIONS:
{table['hint']}

RULES:
- Return ONLY a valid JSON array of objects. No markdown, no explanation.
- Every FK id MUST reference an existing id from the reference data above.
- IDs should be sequential integers starting from 1.
- Descriptions should be lore-accurate to Shadow of the Erdtree.
- Nullable fields should be null when not applicable, not omitted.
- Boolean fields must be true or false (not 0/1).
- Do NOT include any fields not in the schema.

Return the JSON array:"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def validate_data(
    table: dict, data: list[dict], existing_data: dict[str, list[dict]]
) -> dict:
    """Call the validator agent to check the generated data."""
    schema_desc = "\n".join(f"  {col}: {typ}" for col, typ in table["columns"].items())
    context = build_context(table, existing_data)

    prompt = f"""You are a data validator for an Elden Ring: Shadow of the Erdtree database.

Validate this generated data for the "{table['name']}" table.

SCHEMA:
{schema_desc}

{f"REFERENCE DATA (valid FK targets):{chr(10)}{context}" if context else "No foreign key dependencies."}

GENERATED DATA:
{json.dumps(data, indent=2)}

Check for:
1. SCHEMA COMPLIANCE: Every required column is present, correct types, no extra fields.
2. FK INTEGRITY: Every FK value references a valid id from the reference data.
3. DATA QUALITY: IDs are unique, no duplicates, reasonable values.
4. FACTUAL ACCURACY: Names and descriptions are reasonably accurate to Shadow of the Erdtree (minor inaccuracies are OK).

Respond with a JSON object:
{{
  "valid": true/false,
  "issues": ["list of issues found, empty if valid"],
  "severity": "pass" | "warn" | "fail"
}}

"pass" = no issues. "warn" = minor issues but data is usable. "fail" = broken FKs or missing required fields.

Return ONLY the JSON object:"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def save_data(table: dict, data: list[dict]) -> None:
    """Write generated data to a JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / table["file"]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {len(data)} records to {path}")


def process_table(table: dict, existing_data: dict[str, list[dict]], max_retries: int = 2) -> list[dict]:
    """Generate and validate data for a single table, retrying on failure."""
    print(f"\n{'='*60}")
    print(f"Processing: {table['name']}")
    print(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        print(f"\n  Attempt {attempt}/{max_retries}")

        print("  Generating data...")
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
            print(f"  Validation: WARN — {len(issues)} minor issues")
            for issue in issues:
                print(f"    - {issue}")
            return data
        else:
            print(f"  Validation: FAIL — {len(issues)} issues")
            for issue in issues:
                print(f"    - {issue}")
            if attempt < max_retries:
                print("  Retrying...")

    print(f"  Using last generated data despite validation issues")
    return data


def main():
    print("Elden Ring: Shadow of the Erdtree — Data Generator")
    print("=" * 60)

    existing_data = load_existing_data()
    print(f"Loaded existing data for: {list(existing_data.keys()) or 'none'}")

    all_tables = TABLES + JUNCTION_TABLES

    for table in all_tables:
        if table["name"] in existing_data:
            print(f"\nSkipping {table['name']} — already exists ({len(existing_data[table['name']])} records)")
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
