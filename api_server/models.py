from abc import ABC, abstractproperty
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import metadata
from itertools import groupby
from typing import List, Union

import marshmallow_union
from marshmallow import Schema, fields
from marshmallow_enum import EnumField


def full_icon_path(path):
    return f"https://bungie.net{path}"


def camelcase(s):
    parts = iter(s.split("_"))
    return next(parts) + "".join(i.title() for i in parts)


class JSONSchema(Schema):
    def on_bind_field(self, field_name: str, field_obj) -> None:
        field_obj.data_key = camelcase(field_obj.data_key or field_name)


@dataclass
class User:
    destiny_membership_type: int
    destiny_membership_id: int
    display_name: str

    @classmethod
    def from_json(self, response):
        profile = response["Response"]["profiles"][0]
        membership_type = profile["membershipType"]
        membership_id = profile["membershipId"]
        display_name = f"{profile['bungieGlobalDisplayName']}#{profile['bungieGlobalDisplayNameCode']}"

        return User(
            destiny_membership_type=membership_type,
            destiny_membership_id=membership_id,
            display_name=display_name,
        )

    @classmethod
    def from_db(self, row):
        return User(
            destiny_membership_type=row["destiny_membership_type"],
            destiny_membership_id=row["destiny_membership_id"],
            display_name=row["display_name"],
        )


class UserSchema(JSONSchema):
    destiny_membership_type = fields.Str()
    destiny_membership_id = fields.Str()
    display_name = fields.Str()


@dataclass
class Character:
    character_id: int
    character_class: str
    gender_and_race_description: str
    date_last_played: str
    light: int
    emblem_background_path: str

    @classmethod
    def from_json(self, response, race_defs, class_defs):
        race = race_defs.get(str(response.get("raceHash")))
        character_class = class_defs.get(str(response.get("classHash")))

        return Character(
            character_id=response.get("characterId"),
            character_class=character_class["displayProperties"]["name"],
            gender_and_race_description=race["genderedRaceNamesByGenderHash"][
                str(response.get("genderHash"))
            ],
            date_last_played=response.get("dateLastPlayed"),
            light=response.get("light"),
            emblem_background_path=f'https://bungie.net{response.get("emblemBackgroundPath")}',
        )


class CharacterSchema(JSONSchema):
    character_id = fields.Int()
    character_class = fields.Str()
    gender_and_race_description = fields.Str()
    date_last_played = fields.Str()
    light = fields.Int()
    emblem_background_path = fields.Str()


ARMOR_MOD_CATEGORY = 590099826


class ArmorType(int, Enum):
    Helmet = 1
    Arms = 2
    Chest = 3
    Legs = 4
    ClassItem = 5


class EnergyType(int, Enum):
    Any = 0
    Arc = 1
    Solar = 2
    Void = 3
    Stasis = 6


class DamageType(int, Enum):
    NoDamage = 0
    Kinetic = 1
    Arc = 2
    Solar = 3
    Void = 4
    Raid = 5
    Stasis = 6


BUCKET_HASH_ARMOR_TYPE_MAPPING = {
    3448274439: ArmorType.Helmet,
    3551918588: ArmorType.Arms,
    14239492: ArmorType.Chest,
    20886954: ArmorType.Legs,
    1585787867: ArmorType.ClassItem,
}

STAT_TYPE_HASH_ENERGY_TYPE_MAPPING = {
    2399985800: EnergyType.Void,
    998798867: EnergyType.Stasis,
    3344745325: EnergyType.Solar,
    3578062600: EnergyType.Any,
    3779394102: EnergyType.Arc,
    3950461274: EnergyType.Stasis,
}

# The SocketResponse and PlugResponse classes are returned from the SocketedItem base class and can be returned directly
# or transformed into somethng else if more custom fields are needed
@dataclass
class PlugResponse:
    plug_hash: str
    display_name: str
    icon_path: str
    energy_type: EnergyType
    energy_cost: int


class PlugResponseSchema(JSONSchema):
    plug_hash = fields.Str()
    display_name = fields.Str()
    icon_path = fields.Str()
    energy_type = EnumField(EnergyType, by_value=True)
    energy_cost = fields.Int()


@dataclass
class SocketResponse:
    display_name: str
    icon_path: str
    plug_set_hash: str
    socket_item_type_hash: str
    current_plug: Union[PlugResponse, None]


class SocketResponseSchema(JSONSchema):
    display_name = fields.Str()
    icon_path = fields.Str()
    plug_set_hash = fields.Str()
    socket_item_type_hash = fields.Str()
    current_plug = marshmallow_union.Union([fields.Nested(PlugResponseSchema), None])


class SocketedItem(ABC):
    @abstractproperty
    @property
    def socket_category_hashes(self):
        pass

    def parse_sockets(
        self, item_hash, item_instance_socket_response, inventory_item_defs
    ) -> List[SocketResponse]:
        item_def = inventory_item_defs[str(item_hash)]
        sockets = {}
        for category_hash in self.socket_category_hashes:
            socket_indexes = []
            category_sockets = []
            for category in item_def["sockets"]["socketCategories"]:
                if category["socketCategoryHash"] == category_hash:
                    socket_indexes = category["socketIndexes"]

                for index in socket_indexes:
                    item_def_socket_entry = item_def["sockets"]["socketEntries"][index]
                    item_instance_socket = item_instance_socket_response[index]
                    socket_intitial_item_def_hash = item_def_socket_entry[
                        "singleInitialItemHash"
                    ]

                    socket_initial_item_def = inventory_item_defs[
                        str(socket_intitial_item_def_hash)
                    ]
                    s = {
                        "socket_item_type_hash": item_def_socket_entry[
                            "singleInitialItemHash"
                        ],
                        "display_name": socket_initial_item_def["itemTypeDisplayName"],
                        "icon_path": full_icon_path(
                            socket_initial_item_def["displayProperties"]["icon"]
                        ),
                        "plug_set_hash": item_def_socket_entry["reusablePlugSetHash"],
                    }

                    if (
                        item_instance_socket["plugHash"]
                        != socket_intitial_item_def_hash
                    ):
                        active_plug_item_def = inventory_item_defs[
                            str(item_instance_socket["plugHash"])
                        ]
                        energy_stat = [
                            s
                            for s in active_plug_item_def["investmentStats"]
                            if s["statTypeHash"]
                            in STAT_TYPE_HASH_ENERGY_TYPE_MAPPING.keys()
                        ][0]

                        s["current_plug"] = {
                            "plug_hash": item_instance_socket["plugHash"],
                            "display_name": active_plug_item_def["displayProperties"][
                                "name"
                            ],
                            "icon_path": full_icon_path(
                                active_plug_item_def["displayProperties"]["icon"]
                            ),
                            "energy_cost": energy_stat["value"],
                            "energy_type": STAT_TYPE_HASH_ENERGY_TYPE_MAPPING[
                                energy_stat["statTypeHash"]
                            ],
                        }
                    else:
                        s["current_plug"] = None
                    category_sockets.append(s)
            sockets[category_hash] = category_sockets
        return sockets


@dataclass
class ArmorPiece(SocketedItem):
    item_hash: int
    item_instance_id: str
    item_type: ArmorType
    bucket_hash: int
    name: str
    icon_path: str
    energy_type: EnergyType
    energy_capacity: int
    energy_used: int
    mod_slots: List[SocketResponse]

    socket_category_hashes = [ARMOR_MOD_CATEGORY]

    @classmethod
    def from_json(self, response, instance, socket_response, inventory_item_defs):
        item = inventory_item_defs[str(response["itemHash"])]
        sockets = self.parse_sockets(
            self,
            response["itemHash"],
            socket_response,
            inventory_item_defs,
        )

        return ArmorPiece(
            item_hash=response["itemHash"],
            item_instance_id=response["itemInstanceId"],
            item_type=BUCKET_HASH_ARMOR_TYPE_MAPPING.get(response["bucketHash"]),
            bucket_hash=response["bucketHash"],
            name=item["displayProperties"]["name"],
            icon_path=f'https://bungie.net{item["displayProperties"]["icon"]}',
            energy_type=EnergyType(instance["energy"]["energyType"]),
            energy_capacity=instance["energy"]["energyCapacity"],
            energy_used=instance["energy"]["energyUsed"],
            mod_slots=sockets[ARMOR_MOD_CATEGORY],
        )


class ArmorPieceSchema(JSONSchema):
    item_hash = fields.Int()
    item_instance_id = fields.Str()
    item_type = EnumField(ArmorType, by_value=True)
    bucket_hash = fields.Int()
    name = fields.Str()
    icon_path = fields.Str()
    energy_type = EnumField(EnergyType, by_value=True)
    energy_capacity = fields.Int()
    energy_used = fields.Int()
    mod_slots = fields.List(fields.Nested(SocketResponseSchema))


@dataclass
class TreeStyleSubclassPerk:
    name: str
    icon_path: str
    description: str


class TreeStyleSubclassPerkSchema(JSONSchema):
    name = fields.Str()
    icon_path = fields.Str()
    description = fields.Str()


class TreePathType(int, Enum):
    Top = 0
    Middle = 1
    Bottom = 2


@dataclass
class TreeStyleSubclassTree:
    name: str
    icon_path: str
    tree_path_type: TreePathType
    left_perk: TreeStyleSubclassPerk
    top_perk: TreeStyleSubclassPerk
    right_perk: TreeStyleSubclassPerk
    bottom_perk: TreeStyleSubclassPerk


class TreeStyleSubclassTreeSchema(JSONSchema):
    name = fields.Str()
    icon_path = fields.Str()
    tree_path_type = EnumField(TreePathType, by_value=True)
    left_perk = fields.Nested(TreeStyleSubclassPerkSchema)
    top_perk = fields.Nested(TreeStyleSubclassPerkSchema)
    right_perk = fields.Nested(TreeStyleSubclassPerkSchema)
    bottom_perk = fields.Nested(TreeStyleSubclassPerkSchema)


SUBCLASSS_BUCKET_HASH = 3284755031
CLASS_ABILITY_GROUP_HASHES = [3874829120, 3874829121]
MOVEMENT_GROUP_HASHES = [4114106724, 4114106725, 4114106726]
GRENADE_GROUP_HASHES = [2697262605, 2697262606, 2697262607]
TOP_TREE_GROUP_HASH = 1350529726
MIDDLE_TREE_GROUP_HASH = 1350529727
BOTTOM_TREE_GROUP_HASH = 1350529724


@dataclass
class TreeStyleSubclass:
    name: str
    icon_path: str
    damage_type: DamageType
    item_hash: str
    active_class_ability: TreeStyleSubclassPerk
    active_movement_ability: TreeStyleSubclassPerk
    active_grenade_ability: TreeStyleSubclassPerk
    active_tree: TreeStyleSubclassTree

    @classmethod
    def from_json(
        self,
        response,
        talent_grid_response,
        inventory_item_defs,
        talent_grid_defs,
    ):
        item_def = inventory_item_defs[str(response["itemHash"])]
        talent_grid = talent_grid_defs[str(item_def["talentGrid"]["talentGridHash"])]

        active_instance_nodes = [
            n["nodeIndex"] for n in talent_grid_response["nodes"] if n["isActivated"]
        ]
        talent_grid_nodes = [
            n
            for n in talent_grid["nodes"]
            if n["nodeIndex"] in active_instance_nodes
            and (n["row"] >= 0 and n["column"] >= 0)
        ]

        class_ability_node = [
            n
            for n in talent_grid_nodes
            if n.get("groupHash") in CLASS_ABILITY_GROUP_HASHES
        ][0]

        movement_ability_node = [
            n for n in talent_grid_nodes if n.get("groupHash") in MOVEMENT_GROUP_HASHES
        ][0]

        grenade_ability_node = [
            n for n in talent_grid_nodes if n.get("groupHash") in GRENADE_GROUP_HASHES
        ][0]

        active_tree_nodes = [
            n
            for n in talent_grid_nodes
            if n.get("groupHash")
            in [TOP_TREE_GROUP_HASH, MIDDLE_TREE_GROUP_HASH, BOTTOM_TREE_GROUP_HASH]
        ]

        def get_step_display_properties(node):
            return node["steps"][0]["displayProperties"]

        active_class_ability = TreeStyleSubclassPerk(
            name=get_step_display_properties(class_ability_node)["name"],
            description=get_step_display_properties(class_ability_node)["description"],
            icon_path=full_icon_path(
                get_step_display_properties(class_ability_node)["icon"]
            ),
        )

        active_movement_ability = TreeStyleSubclassPerk(
            name=get_step_display_properties(movement_ability_node)["name"],
            description=get_step_display_properties(movement_ability_node)[
                "description"
            ],
            icon_path=full_icon_path(
                get_step_display_properties(movement_ability_node)["icon"]
            ),
        )

        active_grenade_ability = TreeStyleSubclassPerk(
            name=get_step_display_properties(grenade_ability_node)["name"],
            description=get_step_display_properties(grenade_ability_node)[
                "description"
            ],
            icon_path=full_icon_path(
                get_step_display_properties(grenade_ability_node)["icon"]
            ),
        )

        # find the group that the active nodes are in to get the path name without pulling the lore definition
        # all the active nodes in the tree must belong to the same group because the game enforces that, so just use the first node

        tree_node_category = [
            c
            for c in talent_grid["nodeCategories"]
            if active_tree_nodes[0]["nodeHash"] in c["nodeHashes"]
        ][0]

        get_node_column = lambda n: n["column"]

        sorted_tree_nodes = sorted(active_tree_nodes, key=get_node_column)

        # there should be 4 nodes in this iterable, grouped like this: [(left), (top, bottom), (right)]
        # so to get the correct diamond shape, compare the 'row' property of the middle group to see which is top or bottom
        # and they are sorted by column so left and right should already be correct
        for index, (column, g) in enumerate(
            groupby(sorted_tree_nodes, key=get_node_column)
        ):
            group = list(g)
            if len(list(group)) == 2:
                if group[0]["row"] < group[1]["row"]:
                    tree_top_perk = group[0]
                    tree_bottom_perk = group[1]
                else:
                    tree_top_perk = group[1]
                    tree_bottom_perk = group[0]
            elif index == 0:
                tree_left_perk = group[0]
            elif index == 2:
                tree_right_perk = group[0]

        active_tree_group_hash = active_tree_nodes[0]["groupHash"]

        if active_tree_group_hash == TOP_TREE_GROUP_HASH:
            tree_path_type = TreePathType.Top
        elif active_tree_group_hash == MIDDLE_TREE_GROUP_HASH:
            tree_path_type = TreePathType.Middle
        elif active_tree_group_hash == BOTTOM_TREE_GROUP_HASH:
            tree_path_type = TreePathType.Bottom
        else:
            tree_path_type = None

        active_tree = TreeStyleSubclassTree(
            name=tree_node_category["displayProperties"]["name"],
            icon_path=full_icon_path(tree_node_category["displayProperties"]["icon"]),
            tree_path_type=tree_path_type,
            left_perk=TreeStyleSubclassPerk(
                name=get_step_display_properties(tree_left_perk)["name"],
                icon_path=full_icon_path(
                    get_step_display_properties(tree_left_perk)["icon"]
                ),
                description=get_step_display_properties(tree_left_perk)["description"],
            ),
            top_perk=TreeStyleSubclassPerk(
                name=get_step_display_properties(tree_top_perk)["name"],
                icon_path=full_icon_path(
                    get_step_display_properties(tree_top_perk)["icon"]
                ),
                description=get_step_display_properties(tree_top_perk)["description"],
            ),
            right_perk=TreeStyleSubclassPerk(
                name=get_step_display_properties(tree_right_perk)["name"],
                icon_path=full_icon_path(
                    get_step_display_properties(tree_right_perk)["icon"]
                ),
                description=get_step_display_properties(tree_right_perk)["description"],
            ),
            bottom_perk=TreeStyleSubclassPerk(
                name=get_step_display_properties(tree_bottom_perk)["name"],
                icon_path=full_icon_path(
                    get_step_display_properties(tree_bottom_perk)["icon"]
                ),
                description=get_step_display_properties(tree_bottom_perk)[
                    "description"
                ],
            ),
        )

        return TreeStyleSubclass(
            name=item_def["displayProperties"]["name"],
            icon_path=full_icon_path(item_def["displayProperties"]["icon"]),
            damage_type=DamageType(item_def["talentGrid"]["hudDamageType"]),
            item_hash=response["itemHash"],
            active_class_ability=active_class_ability,
            active_movement_ability=active_movement_ability,
            active_grenade_ability=active_grenade_ability,
            active_tree=active_tree,
        )


class TreeStyleSubclassSchema(JSONSchema):
    name = fields.Str()
    icon_path = fields.Str()
    damage_type = EnumField(DamageType, by_value=True)
    item_hash = fields.Str()
    active_class_ability = fields.Nested(TreeStyleSubclassPerkSchema)
    active_movement_ability = fields.Nested(TreeStyleSubclassPerkSchema)
    active_grenade_ability = fields.Nested(TreeStyleSubclassPerkSchema)
    active_tree = fields.Nested(TreeStyleSubclassTreeSchema)


@dataclass
class FullCharacterData:
    character: Character
    armor: List[ArmorPiece]
    subclass: TreeStyleSubclass


class FullCharacterDataSchema(JSONSchema):
    character = fields.Nested(CharacterSchema)
    armor = fields.List(fields.Nested(ArmorPieceSchema))
    subclass = fields.Nested(TreeStyleSubclassSchema)
