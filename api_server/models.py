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

    @classmethod
    def from_json(self, response, instance, inventory_item_defs):
        item = inventory_item_defs[str(response["itemHash"])]

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
        )
