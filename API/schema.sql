-- Elden Ring database schema
-- Tables are ordered to satisfy foreign key dependencies.
-- Safe to re-run: all CREATE TABLE use IF NOT EXISTS,
-- all ADD CONSTRAINT statements are guarded via DO blocks.
-- Initial made with: https://drawsql.app

CREATE TABLE IF NOT EXISTS "elden_ring" (
    "id"           INTEGER      NOT NULL,
    "release_date" DATE         NOT NULL,
    "developer"    VARCHAR(255) NOT NULL,
    "publisher"    VARCHAR(255) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "location" (
    "id"               INTEGER      NOT NULL,
    "title"            VARCHAR(255) NOT NULL,
    "description"      TEXT         NOT NULL,
    "prev_location_id" INTEGER      NULL,
    "next_location_id" INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "npc" (
    "id"                  INTEGER      NOT NULL,
    "title"               VARCHAR(255) NOT NULL,
    "quest_description"   TEXT         NOT NULL,
    "initial_location_id" INTEGER      NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "boss" (
    "id"          INTEGER      NOT NULL,
    "game_id"     INTEGER      NULL,
    "title"       VARCHAR(255) NOT NULL,
    "description" TEXT         NOT NULL,
    "location_id" INTEGER      NULL,
    "runes"       INTEGER      NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "dungeon" (
    "id"          INTEGER      NOT NULL,
    "title"       VARCHAR(255) NOT NULL,
    "location_id" INTEGER      NOT NULL,
    "is_legacy"   BOOLEAN      NOT NULL,
    "boss_id"     INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "remembrance" (
    "id"          INTEGER      NOT NULL,
    "boss_id"     INTEGER      NOT NULL,
    "title"       VARCHAR(255) NOT NULL,
    "description" TEXT         NOT NULL,
    "runes"       INTEGER      NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "weapon_class" (
    "id"         INTEGER      NOT NULL,
    "class_name" VARCHAR(255) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "weapon" (
    "id"             INTEGER      NOT NULL,
    "class_id"       INTEGER      NOT NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "is_somber"      BOOLEAN      NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "spell" (
    "id"             INTEGER      NOT NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

-- weapon_class must be created before spell_class (FK dependency)
CREATE TABLE IF NOT EXISTS "spell_class" (
    "spell_id" INTEGER NOT NULL,
    "class_id" INTEGER NOT NULL,
    PRIMARY KEY ("spell_id", "class_id"),
    FOREIGN KEY ("spell_id") REFERENCES "spell"("id"),
    FOREIGN KEY ("class_id") REFERENCES "weapon_class"("id")
);

CREATE TABLE IF NOT EXISTS "skill" (
    "id"             INTEGER      NOT NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "fp_cost"        INTEGER      NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "skill_weapon_class" (
    "skill_id" INTEGER NOT NULL,
    "class_id" INTEGER NOT NULL,
    PRIMARY KEY ("skill_id", "class_id"),
    FOREIGN KEY ("skill_id") REFERENCES "skill"("id"),
    FOREIGN KEY ("class_id") REFERENCES "weapon_class"("id")
);

CREATE TABLE IF NOT EXISTS "consumable" (
    "id"             INTEGER      NOT NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "fp_cost"        INTEGER      NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "talisman" (
    "id"             INTEGER      NOT NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "armor_set" (
    "id"    INTEGER      NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "armor_piece" (
    "id"             INTEGER      NOT NULL,
    "set_id"         INTEGER      NULL,
    "title"          VARCHAR(255) NOT NULL,
    "description"    TEXT         NOT NULL,
    "remembrance_id" INTEGER      NULL,
    "boss_id"        INTEGER      NULL,
    "location_id"    INTEGER      NULL,
    "dungeon_id"     INTEGER      NULL,
    "npc_id"         INTEGER      NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "summon" (
    "id"          INTEGER      NOT NULL,
    "title"       VARCHAR(255) NOT NULL,
    "description" TEXT         NOT NULL,
    "fp_cost"     INTEGER      NULL,
    "hp_cost"     INTEGER      NULL,
    "boss_id"     INTEGER      NULL,
    "location_id" INTEGER      NULL,
    "dungeon_id"  INTEGER      NULL,
    "npc_id"      INTEGER      NULL,
    PRIMARY KEY ("id")
);

-- Foreign key constraints
-- Each is wrapped in a DO block that skips silently if already present.

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'location_prev_location_id_foreign') THEN
        ALTER TABLE "location" ADD CONSTRAINT "location_prev_location_id_foreign" FOREIGN KEY ("prev_location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'location_next_location_id_foreign') THEN
        ALTER TABLE "location" ADD CONSTRAINT "location_next_location_id_foreign" FOREIGN KEY ("next_location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'npc_initial_location_id_foreign') THEN
        ALTER TABLE "npc" ADD CONSTRAINT "npc_initial_location_id_foreign" FOREIGN KEY ("initial_location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'boss_game_id_foreign') THEN
        ALTER TABLE "boss" ADD CONSTRAINT "boss_game_id_foreign" FOREIGN KEY ("game_id") REFERENCES "elden_ring"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'boss_location_id_foreign') THEN
        ALTER TABLE "boss" ADD CONSTRAINT "boss_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'dungeon_location_id_foreign') THEN
        ALTER TABLE "dungeon" ADD CONSTRAINT "dungeon_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'dungeon_boss_id_foreign') THEN
        ALTER TABLE "dungeon" ADD CONSTRAINT "dungeon_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'remembrance_boss_id_foreign') THEN
        ALTER TABLE "remembrance" ADD CONSTRAINT "remembrance_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_class_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_class_id_foreign" FOREIGN KEY ("class_id") REFERENCES "weapon_class"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_remembrance_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_boss_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_location_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_dungeon_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'weapon_npc_id_foreign') THEN
        ALTER TABLE "weapon" ADD CONSTRAINT "weapon_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'spell_remembrance_id_foreign') THEN
        ALTER TABLE "spell" ADD CONSTRAINT "spell_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'spell_boss_id_foreign') THEN
        ALTER TABLE "spell" ADD CONSTRAINT "spell_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'spell_location_id_foreign') THEN
        ALTER TABLE "spell" ADD CONSTRAINT "spell_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'spell_dungeon_id_foreign') THEN
        ALTER TABLE "spell" ADD CONSTRAINT "spell_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'spell_npc_id_foreign') THEN
        ALTER TABLE "spell" ADD CONSTRAINT "spell_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'skill_remembrance_id_foreign') THEN
        ALTER TABLE "skill" ADD CONSTRAINT "skill_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'skill_boss_id_foreign') THEN
        ALTER TABLE "skill" ADD CONSTRAINT "skill_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'skill_location_id_foreign') THEN
        ALTER TABLE "skill" ADD CONSTRAINT "skill_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'skill_dungeon_id_foreign') THEN
        ALTER TABLE "skill" ADD CONSTRAINT "skill_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'skill_npc_id_foreign') THEN
        ALTER TABLE "skill" ADD CONSTRAINT "skill_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'consumable_remembrance_id_foreign') THEN
        ALTER TABLE "consumable" ADD CONSTRAINT "consumable_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'consumable_boss_id_foreign') THEN
        ALTER TABLE "consumable" ADD CONSTRAINT "consumable_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'consumable_location_id_foreign') THEN
        ALTER TABLE "consumable" ADD CONSTRAINT "consumable_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'consumable_dungeon_id_foreign') THEN
        ALTER TABLE "consumable" ADD CONSTRAINT "consumable_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'consumable_npc_id_foreign') THEN
        ALTER TABLE "consumable" ADD CONSTRAINT "consumable_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'talisman_remembrance_id_foreign') THEN
        ALTER TABLE "talisman" ADD CONSTRAINT "talisman_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'talisman_boss_id_foreign') THEN
        ALTER TABLE "talisman" ADD CONSTRAINT "talisman_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'talisman_location_id_foreign') THEN
        ALTER TABLE "talisman" ADD CONSTRAINT "talisman_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'talisman_dungeon_id_foreign') THEN
        ALTER TABLE "talisman" ADD CONSTRAINT "talisman_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'talisman_npc_id_foreign') THEN
        ALTER TABLE "talisman" ADD CONSTRAINT "talisman_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_set_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_set_id_foreign" FOREIGN KEY ("set_id") REFERENCES "armor_set"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_remembrance_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_remembrance_id_foreign" FOREIGN KEY ("remembrance_id") REFERENCES "remembrance"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_boss_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_location_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_dungeon_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'armor_piece_npc_id_foreign') THEN
        ALTER TABLE "armor_piece" ADD CONSTRAINT "armor_piece_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'summon_boss_id_foreign') THEN
        ALTER TABLE "summon" ADD CONSTRAINT "summon_boss_id_foreign" FOREIGN KEY ("boss_id") REFERENCES "boss"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'summon_location_id_foreign') THEN
        ALTER TABLE "summon" ADD CONSTRAINT "summon_location_id_foreign" FOREIGN KEY ("location_id") REFERENCES "location"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'summon_dungeon_id_foreign') THEN
        ALTER TABLE "summon" ADD CONSTRAINT "summon_dungeon_id_foreign" FOREIGN KEY ("dungeon_id") REFERENCES "dungeon"("id");
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'summon_npc_id_foreign') THEN
        ALTER TABLE "summon" ADD CONSTRAINT "summon_npc_id_foreign" FOREIGN KEY ("npc_id") REFERENCES "npc"("id");
    END IF;
END $$;
