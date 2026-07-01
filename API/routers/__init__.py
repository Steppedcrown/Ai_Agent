from ._base import make_router

bosses_router = make_router("bosses", search_field="title", table="boss")
locations_router = make_router("locations", search_field="title", table="location")
npcs_router = make_router("npcs", search_field="title", table="npc")
dungeons_router = make_router("dungeons", search_field="title", table="dungeon")
remembrances_router = make_router("remembrances", search_field="title", table="remembrance")
weapon_classes_router = make_router("weapon-classes", search_field="class_name", table="weapon_class", tag="Weapon Classes")
weapons_router = make_router("weapons", search_field="title", table="weapon")
spells_router = make_router("spells", search_field="title", table="spell")
skills_router = make_router("skills", search_field="title", table="skill")
consumables_router = make_router("consumables", search_field="title", table="consumable")
talismans_router = make_router("talismans", search_field="title", table="talisman")
armor_sets_router = make_router("armor-sets", search_field="title", table="armor_set", tag="Armor Sets")
armor_pieces_router = make_router("armor-pieces", search_field="title", table="armor_piece", tag="Armor Pieces")
summons_router = make_router("summons", search_field="title", table="summon")

all_routers = [
    bosses_router,
    locations_router,
    npcs_router,
    dungeons_router,
    remembrances_router,
    weapon_classes_router,
    weapons_router,
    spells_router,
    skills_router,
    consumables_router,
    talismans_router,
    armor_sets_router,
    armor_pieces_router,
    summons_router,
]
