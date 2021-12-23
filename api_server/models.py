from dataclasses import dataclass


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

        return User(membership_type, membership_id, display_name)

    @classmethod
    def from_db(self, row):
        return User(
            row["destiny_membership_type"],
            row["destiny_membership_id"],
            row["display_name"],
        )
