from dataclasses import dataclass
from enum import Enum
from itertools import groupby


def full_icon_path(path):
    return f"https://bungie.net{path}"


@dataclass
class User:
    destinyMembershipType: int
    destinyMembershipID: int
    displayName: str

    @classmethod
    def from_json(self, response):
        profile = response["Response"]["profiles"][0]
        membership_type = profile["membershipType"]
        membership_id = profile["membershipId"]
        display_name = f"{profile['bungieGlobalDisplayName']}#{profile['bungieGlobalDisplayNameCode']}"

        return User(
            destinyMembershipType=membership_type,
            destinyMembershipID=membership_id,
            displayName=display_name,
        )

    @classmethod
    def from_db(self, row):
        return User(
            destinyMembershipType=row["destiny_membership_type"],
            destinyMembershipID=row["destiny_membership_id"],
            displayName=row["display_name"],
        )


@dataclass
class Character:
    characterID: int
    characterClass: str
    genderAndRaceDescription: str
    dateLastPlayed: str
    light: int
    emblemBackgroundPath: str

    @classmethod
    def from_json(self, response, race_defs, class_defs):
        race = race_defs.get(str(response.get("raceHash")))
        character_class = class_defs.get(str(response.get("classHash")))

        return Character(
            characterID=response.get("characterId"),
            characterClass=character_class["displayProperties"]["name"],
            genderAndRaceDescription=race["genderedRaceNamesByGenderHash"][
                str(response.get("genderHash"))
            ],
            dateLastPlayed=response.get("dateLastPlayed"),
            light=response.get("light"),
            emblemBackgroundPath=f'https://bungie.net{response.get("emblemBackgroundPath")}',
        )


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


bucket_hash_armor_type_mapping = {
    3448274439: ArmorType.Helmet,
    3551918588: ArmorType.Arms,
    14239492: ArmorType.Chest,
    20886954: ArmorType.Legs,
    1585787867: ArmorType.ClassItem,
}

stat_type_hash_energy_type_mapping = {
    2399985800: EnergyType.Void,
    998798867: EnergyType.Stasis,
    3344745325: EnergyType.Solar,
    3578062600: EnergyType.Any,
    3779394102: EnergyType.Arc,
    3950461274: EnergyType.Stasis,
}


@dataclass
class ArmorPiece:
    itemHash: int
    itemInstanceID: str
    itemType: ArmorType
    bucketHash: int
    name: str
    iconPath: str
    energyType: EnergyType
    energyCapacity: int
    energyUsed: int
    sockets: dict

    @classmethod
    def from_json(self, response, instance, socket_response, inventory_item_defs):
        # TODO: try to abstract the socket logic to a mixin class so that we can use it for aspect-based subclasses as well
        item = inventory_item_defs[str(response["itemHash"])]
        armor_mod_indexes = None
        for category in item["sockets"]["socketCategories"]:
            if category["socketCategoryHash"] == ARMOR_MOD_CATEGORY:
                armor_mod_indexes = category["socketIndexes"]

        sockets = []
        if armor_mod_indexes:
            for index in armor_mod_indexes:
                armor_item_definition_socket = item["sockets"]["socketEntries"][index]
                item_component_socket = socket_response[index]
                socket_item_initial_mod_def = inventory_item_defs[
                    str(armor_item_definition_socket["singleInitialItemHash"])
                ]

                s = {
                    "socketItemTypeHash": armor_item_definition_socket[
                        "singleInitialItemHash"
                    ],
                    "displayName": socket_item_initial_mod_def["itemTypeDisplayName"],
                    "iconPath": f"https://bungie.net{socket_item_initial_mod_def['displayProperties']['icon']}",
                    "plugSetHash": armor_item_definition_socket["reusablePlugSetHash"],
                }
                if (
                    item_component_socket["plugHash"]
                    != armor_item_definition_socket["singleInitialItemHash"]
                ):
                    active_mod_item_def = inventory_item_defs[
                        str(item_component_socket["plugHash"])
                    ]
                    energy_stat = [
                        m
                        for m in active_mod_item_def["investmentStats"]
                        if m["statTypeHash"]
                        in stat_type_hash_energy_type_mapping.keys()
                    ][0]

                    s["currentPlug"] = {
                        "plugHash": item_component_socket["plugHash"],
                        "displayName": active_mod_item_def["displayProperties"]["name"],
                        "iconPath": f"https://bungie.net{active_mod_item_def['displayProperties']['icon']}",
                        "energyCost": energy_stat["value"],
                        "energyType": stat_type_hash_energy_type_mapping[
                            energy_stat["statTypeHash"]
                        ],
                    }
                else:
                    s["currentPlug"] = None
                sockets.append(s)

        return ArmorPiece(
            itemHash=response["itemHash"],
            itemInstanceID=response["itemInstanceId"],
            itemType=bucket_hash_armor_type_mapping.get(response["bucketHash"]),
            bucketHash=response["bucketHash"],
            name=item["displayProperties"]["name"],
            iconPath=f'https://bungie.net{item["displayProperties"]["icon"]}',
            energyType=EnergyType(instance["energy"]["energyType"]),
            energyCapacity=instance["energy"]["energyCapacity"],
            energyUsed=instance["energy"]["energyUsed"],
            sockets=sockets,
        )


subclass_bucket_hash = 3284755031
class_ability_group_hashes = [3874829120, 3874829121]
movement_group_hashes = [4114106724, 4114106725, 4114106726]
grenade_group_hashes = [2697262605, 2697262606, 2697262607]
top_tree_group_hash = 1350529726
middle_tree_group_hash = 1350529727
bottom_tree_group_hash = 1350529724


@dataclass
class TreeStyleSubclass:
    name: str
    iconPath: str
    damageType: DamageType
    itemHash: str
    activeClassAbility: dict
    activeMovementAbility: dict
    activeGrenadeAbility: dict
    activeTree: dict

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
            if n.get("groupHash") in class_ability_group_hashes
        ][0]

        movement_ability_node = [
            n for n in talent_grid_nodes if n.get("groupHash") in movement_group_hashes
        ][0]

        grenade_ability_node = [
            n for n in talent_grid_nodes if n.get("groupHash") in grenade_group_hashes
        ][0]

        active_tree_nodes = [
            n
            for n in talent_grid_nodes
            if n.get("groupHash")
            in [top_tree_group_hash, middle_tree_group_hash, bottom_tree_group_hash]
        ]

        def get_step_display_properties(node):
            return node["steps"][0]["displayProperties"]

        active_class_ability = {
            "name": get_step_display_properties(class_ability_node)["name"],
            "description": get_step_display_properties(class_ability_node)[
                "description"
            ],
            "iconPath": full_icon_path(
                get_step_display_properties(class_ability_node)["icon"]
            ),
        }

        active_movement_ability = {
            "name": get_step_display_properties(movement_ability_node)["name"],
            "description": get_step_display_properties(movement_ability_node)[
                "description"
            ],
            "iconPath": full_icon_path(
                get_step_display_properties(movement_ability_node)["icon"]
            ),
        }

        active_grenade_ability = {
            "name": get_step_display_properties(grenade_ability_node)["name"],
            "description": get_step_display_properties(grenade_ability_node)[
                "description"
            ],
            "iconPath": full_icon_path(
                get_step_display_properties(grenade_ability_node)["icon"]
            ),
        }

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

        active_tree = {
            "name": tree_node_category["displayProperties"]["name"],
            "iconPath": full_icon_path(tree_node_category["displayProperties"]["icon"]),
            "treePathType": "top"
            if active_tree_group_hash == top_tree_group_hash
            else "middle"
            if active_tree_group_hash == middle_tree_group_hash
            else "bottom"
            if active_tree_group_hash == bottom_tree_group_hash
            else "",
            "leftPerk": {
                "name": get_step_display_properties(tree_left_perk)["name"],
                "iconPath": full_icon_path(
                    get_step_display_properties(tree_left_perk)["icon"]
                ),
                "description": get_step_display_properties(tree_left_perk)[
                    "description"
                ],
            },
            "topPerk": {
                "name": get_step_display_properties(tree_top_perk)["name"],
                "iconPath": full_icon_path(
                    get_step_display_properties(tree_top_perk)["icon"]
                ),
                "description": get_step_display_properties(tree_top_perk)[
                    "description"
                ],
            },
            "rightPerk": {
                "name": get_step_display_properties(tree_right_perk)["name"],
                "iconPath": full_icon_path(
                    get_step_display_properties(tree_right_perk)["icon"]
                ),
                "description": get_step_display_properties(tree_right_perk)[
                    "description"
                ],
            },
            "bottomPerk": {
                "name": get_step_display_properties(tree_bottom_perk)["name"],
                "iconPath": full_icon_path(
                    get_step_display_properties(tree_bottom_perk)["icon"]
                ),
                "description": get_step_display_properties(tree_bottom_perk)[
                    "description"
                ],
            },
        }

        return TreeStyleSubclass(
            name=item_def["displayProperties"]["name"],
            iconPath=full_icon_path(item_def["displayProperties"]["icon"]),
            damageType=item_def["talentGrid"]["hudDamageType"],
            itemHash=response["itemHash"],
            activeClassAbility=active_class_ability,
            activeMovementAbility=active_movement_ability,
            activeGrenadeAbility=active_grenade_ability,
            activeTree=active_tree,
        )
