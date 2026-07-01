"""
Populate the database from all JSON files in API/data/.
Safe to re-run: uses INSERT ... ON CONFLICT DO UPDATE so existing rows
are refreshed rather than causing errors.
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

DATA_DIR = Path(__file__).parent / "data"


def get_conn():
    url = os.environ["DATABASE_URL"]
    p = urlparse(url)
    return psycopg2.connect(
        host=p.hostname, port=p.port or 5432,
        dbname=p.path.lstrip("/"), user=p.username, password=p.password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def load(filename: str) -> list[dict]:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def seed(cur, table: str, rows: list[dict], pk: str | tuple):
    if not rows:
        return
    columns = list(rows[0].keys())
    col_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("%s" for _ in columns)

    if isinstance(pk, str):
        conflict = f'("{pk}")'
        updates = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in columns if c != pk
        )
    else:
        conflict = "(" + ", ".join(f'"{k}"' for k in pk) + ")"
        updates = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in columns if c not in pk
        )

    on_conflict = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
    sql = (
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})\n'
        f"ON CONFLICT {conflict} {on_conflict}"
    )
    values = [tuple(row[c] for c in columns) for row in rows]
    cur.executemany(sql, values)
    print(f"  {table}: {len(rows)} rows")


def main():
    conn = get_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            print("Seeding tables...")

            # Tier 1 — no foreign key dependencies
            seed(cur, "elden_ring", load("elden_ring.json"), "id")
            seed(cur, "weapon_class", load("weapon_classes.json"), "id")

            # location has self-referential FKs: insert without them, then patch
            locations = load("locations.json")
            seed(cur, "location",
                 [{**r, "prev_location_id": None, "next_location_id": None} for r in locations],
                 "id")
            for r in locations:
                cur.execute(
                    'UPDATE "location" SET prev_location_id=%s, next_location_id=%s WHERE id=%s',
                    (r["prev_location_id"], r["next_location_id"], r["id"]),
                )
            print(f"  location links: {len(locations)} rows patched")

            # Tier 2 — depends on tier 1
            seed(cur, "npc",  load("npcs.json"),   "id")
            seed(cur, "boss", load("bosses.json"),  "id")

            # Tier 3 — depends on tier 2
            seed(cur, "dungeon",     load("dungeons.json"),     "id")
            seed(cur, "remembrance", load("remembrances.json"), "id")

            # Tier 4 — depends on tiers 1-3
            seed(cur, "spell",      load("spells.json"),      "id")
            seed(cur, "skill",      load("skills.json"),       "id")
            seed(cur, "weapon",     load("weapons.json"),      "id")
            seed(cur, "consumable", load("consumables.json"),  "id")
            seed(cur, "talisman",   load("talismans.json"),    "id")
            seed(cur, "armor_set",  load("armor_sets.json"),   "id")
            seed(cur, "armor_piece", load("armor_pieces.json"), "id")
            seed(cur, "summon",     load("summons.json"),      "id")

            # Tier 5 — junction tables
            seed(cur, "spell_class",       load("spell_classes.json"),       ("spell_id", "class_id"))
            seed(cur, "skill_weapon_class", load("skill_weapon_classes.json"), ("skill_id", "class_id"))

        conn.commit()
        print("Done.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
