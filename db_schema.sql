CREATE TABLE "elden_ring"(
    "id" INTEGER NOT NULL,
    "release_date" DATE NOT NULL,
    "developer" VARCHAR(255) NOT NULL,
    "publisher" VARCHAR(255) NOT NULL
);
ALTER TABLE
    "elden_ring" ADD PRIMARY KEY("id");
CREATE TABLE "boss"(
    "id" INTEGER NOT NULL,
    "game_id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "location_id" INTEGER NOT NULL,
    "runes" INTEGER NOT NULL
);
ALTER TABLE
    "boss" ADD PRIMARY KEY("id");
CREATE TABLE "remembrance"(
    "id" INTEGER NOT NULL,
    "boss_id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "runes" INTEGER NOT NULL
);
ALTER TABLE
    "remembrance" ADD PRIMARY KEY("id");
CREATE TABLE "weapon"(
    "id" INTEGER NOT NULL,
    "class_id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "is_somber" BOOLEAN NOT NULL,
    "remembrance_id" INTEGER NULL,
    "boss_id" INTEGER NULL,
    "location_id" INTEGER NULL,
    "dungeon_id" INTEGER NULL,
    "npc_id" INTEGER NULL
);
ALTER TABLE
    "weapon" ADD PRIMARY KEY("id");
CREATE TABLE "spell"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "remembrance_id" INTEGER NULL,
    "boss_id" INTEGER NULL,
    "location_id" INTEGER NULL,
    "dungeon_id" INTEGER NULL,
    "npc_id" INTEGER NULL
);
ALTER TABLE
    "spell" ADD PRIMARY KEY("id");
CREATE TABLE "spell_class"(
    "spell_id" INTEGER NOT NULL,
    "class_id" INTEGER NOT NULL,
    PRIMARY KEY ("spell_id", "class_id"),
    FOREIGN KEY("spell_id") REFERENCES "spell"("id"),
    FOREIGN KEY("class_id") REFERENCES "weapon_class"("id")
);
CREATE TABLE "location"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "prev_location_id" INTEGER NULL,
    "next_location_id" INTEGER NULL
);
ALTER TABLE
    "location" ADD PRIMARY KEY("id");
CREATE TABLE "weapon_class"(
    "id" INTEGER NOT NULL,
    "class_name" VARCHAR(255) NOT NULL
);
ALTER TABLE
    "weapon_class" ADD PRIMARY KEY("id");
CREATE TABLE "skill"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "fp_cost" INTEGER NOT NULL,
    "remembrance_id" INTEGER NULL,
    "boss_id" INTEGER NULL,
    "location_id" INTEGER NULL,
    "dungeon_id" INTEGER NULL,
    "npc_id" INTEGER NULL
);
ALTER TABLE
    "skill" ADD PRIMARY KEY("id");
CREATE TABLE "skill_weapon_class"(
    "skill_id" INTEGER NOT NULL,
    "class_id" INTEGER NOT NULL,
    PRIMARY KEY ("skill_id", "class_id"),
    FOREIGN KEY("skill_id") REFERENCES "skill"("id"),
    FOREIGN KEY("class_id") REFERENCES "weapon_class"("id")
);
CREATE TABLE "dungeon"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "location_id" INTEGER NOT NULL,
    "is_legacy" BOOLEAN NOT NULL,
    "boss_id" INTEGER NULL
);
ALTER TABLE
    "dungeon" ADD PRIMARY KEY("id");
CREATE TABLE "npc"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "quest_description" TEXT NOT NULL,
    "initial_location_id" INTEGER NOT NULL
);
ALTER TABLE
    "npc" ADD PRIMARY KEY("id");
CREATE TABLE "reusable_item"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "fp_cost" INTEGER NOT NULL,
    "remembrance_id" INTEGER NULL,
    "boss_id" INTEGER NULL,
    "location_id" INTEGER NULL,
    "dungeon_id" INTEGER NULL,
    "npc_id" INTEGER NULL
);
ALTER TABLE
    "reusable_item" ADD PRIMARY KEY("id");
CREATE TABLE "summon"(
    "id" INTEGER NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "fp_cost" INTEGER NULL,
    "hp_cost" INTEGER NULL,
    "boss_id" INTEGER NULL,
    "location_id" INTEGER NULL,
    "dungeon_id" INTEGER NULL,
    "npc_id" INTEGER NULL
);
ALTER TABLE
    "summon" ADD PRIMARY KEY("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "spell" ADD CONSTRAINT "spell_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "spell" ADD CONSTRAINT "spell_npc_id_foreign" FOREIGN KEY("npc_id") REFERENCES "npc"("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_npc_id_foreign" FOREIGN KEY("npc_id") REFERENCES "npc"("id");
ALTER TABLE
    "summon" ADD CONSTRAINT "summon_npc_id_foreign" FOREIGN KEY("npc_id") REFERENCES "npc"("id");
ALTER TABLE
    "reusable_item" ADD CONSTRAINT "reusable_item_npc_id_foreign" FOREIGN KEY("npc_id") REFERENCES "npc"("id");
ALTER TABLE
    "skill" ADD CONSTRAINT "skill_dungeon_id_foreign" FOREIGN KEY("dungeon_id") REFERENCES "dungeon"("id");
ALTER TABLE
    "skill" ADD CONSTRAINT "skill_remembrance_id_foreign" FOREIGN KEY("remembrance_id") REFERENCES "remembrance"("id");
ALTER TABLE
    "spell" ADD CONSTRAINT "spell_dungeon_id_foreign" FOREIGN KEY("dungeon_id") REFERENCES "dungeon"("id");
ALTER TABLE
    "summon" ADD CONSTRAINT "summon_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "remembrance" ADD CONSTRAINT "remembrance_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "skill" ADD CONSTRAINT "skill_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "reusable_item" ADD CONSTRAINT "reusable_item_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "dungeon" ADD CONSTRAINT "dungeon_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "reusable_item" ADD CONSTRAINT "reusable_item_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "boss" ADD CONSTRAINT "boss_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "summon" ADD CONSTRAINT "summon_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_dungeon_id_foreign" FOREIGN KEY("dungeon_id") REFERENCES "dungeon"("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_remembrance_id_foreign" FOREIGN KEY("remembrance_id") REFERENCES "remembrance"("id");
ALTER TABLE
    "skill" ADD CONSTRAINT "skill_npc_id_foreign" FOREIGN KEY("npc_id") REFERENCES "npc"("id");
ALTER TABLE
    "spell" ADD CONSTRAINT "spell_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "boss" ADD CONSTRAINT "boss_game_id_foreign" FOREIGN KEY("game_id") REFERENCES "elden_ring"("id");
ALTER TABLE
    "reusable_item" ADD CONSTRAINT "reusable_item_remembrance_id_foreign" FOREIGN KEY("remembrance_id") REFERENCES "remembrance"("id");
ALTER TABLE
    "skill" ADD CONSTRAINT "skill_boss_id_foreign" FOREIGN KEY("boss_id") REFERENCES "boss"("id");
ALTER TABLE
    "reusable_item" ADD CONSTRAINT "reusable_item_dungeon_id_foreign" FOREIGN KEY("dungeon_id") REFERENCES "dungeon"("id");
ALTER TABLE
    "dungeon" ADD CONSTRAINT "dungeon_location_id_foreign" FOREIGN KEY("location_id") REFERENCES "location"("id");
ALTER TABLE
    "summon" ADD CONSTRAINT "summon_dungeon_id_foreign" FOREIGN KEY("dungeon_id") REFERENCES "dungeon"("id");
ALTER TABLE
    "npc" ADD CONSTRAINT "npc_initial_location_id_foreign" FOREIGN KEY("initial_location_id") REFERENCES "location"("id");
ALTER TABLE
    "weapon" ADD CONSTRAINT "weapon_class_id_foreign" FOREIGN KEY("class_id") REFERENCES "weapon_class"("id");
ALTER TABLE
    "spell" ADD CONSTRAINT "spell_remembrance_id_foreign" FOREIGN KEY("remembrance_id") REFERENCES "remembrance"("id");
ALTER TABLE
    "location" ADD CONSTRAINT "location_prev_location_id_foreign" FOREIGN KEY("prev_location_id") REFERENCES "location"("id");
ALTER TABLE
    "location" ADD CONSTRAINT "location_next_location_id_foreign" FOREIGN KEY("next_location_id") REFERENCES "location"("id");