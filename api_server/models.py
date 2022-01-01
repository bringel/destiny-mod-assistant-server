from dataclasses import dataclass


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
            emblemBackgroundPath=response.get("emblemBackgroundPath"),
        )
