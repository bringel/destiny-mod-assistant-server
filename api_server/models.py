from dataclasses import dataclass
from enum import Enum


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
    Arc = 1
    Solar = 2
    Void = 3
    Stasis = 6


bucket_hash_armor_type_mapping = {
    3448274439: ArmorType.Helmet,
    3551918588: ArmorType.Arms,
    14239492: ArmorType.Chest,
    20886954: ArmorType.Legs,
    1585787867: ArmorType.ClassItem,
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
                    s["currentPlug"] = {
                        "plugHash": item_component_socket["plugHash"],
                        "displayName": active_mod_item_def["displayProperties"]["name"],
                        "iconPath": f"https://bungie.net{active_mod_item_def['displayProperties']['icon']}",
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
