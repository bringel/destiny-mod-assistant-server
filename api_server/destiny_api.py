import os
from enum import Enum

from flask import session
from requests_oauthlib import OAuth2Session

from api_server.destiny_manifest import DestinyManifest
from api_server.models import User

headers = {"X-API-KEY": os.environ.get("BUNGIE_API_KEY")}


class DestinyComponentType(Enum):
    Profiles = 100
    VendorReceipts = 101
    ProfileInventories = 102
    ProfileCurrencies = 103
    ProfileProgressions = 104
    PlatformSilver = 105
    Characters = 200
    CharacterInventories = 201
    CharacterProgressions = 202
    CharacterRenderData = 203
    CharacterActivities = 204
    CharacterEquipment = 205
    ItemInstances = 300
    ItemObjectives = 301
    ItemPerks = 302
    ItemRenderData = 303
    ItemStats = 304
    ItemSockets = 305
    ItemTalentGrids = 306
    ItemCommonData = 307
    ItemPlugStates = 308
    ItemPlugObjectives = 309
    ItemReusablePlugs = 310
    Vendors = 400
    VendorCategories = 401
    VendorSales = 402
    Kiosks = 500
    CurrencyLookups = 600
    PresentationNodes = 700
    Collectibles = 800
    Records = 900
    Transitory = 1000
    Metrics = 1100
    StringVariables = 1200


DESTINY_BASE_URL = "https://bungie.net/Platform/Destiny2"


class DestinyAPI:
    def __init__(self, *, client_id=None, client_secret=None):
        self.client_id = client_id or os.environ.get("OAUTH_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("OAUTH_CLIENT_SECRET")

        token = session.get("oauth_token")
        state = session.get("oauth_state")
        auto_refresh_extra = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        def token_updater(token):
            session["oauth_token"] = token

        self.bungie_client = OAuth2Session(
            self.client_id,
            token=token,
            state=state,
            auto_refresh_url=os.environ.get("BUNGIE_TOKEN_URL"),
            auto_refresh_kwargs=auto_refresh_extra,
            token_updater=token_updater,
        )
        self.bungie_client.headers.update(headers)

    def get_authorization_url(self):
        return self.bungie_client.authorization_url(
            os.environ.get("BUNGIE_AUTHORIZATION_URL")
        )

    def fetch_token(self, authorization_url):
        token = self.bungie_client.fetch_token(
            os.environ.get("BUNGIE_TOKEN_URL"),
            client_secret=self.client_secret,
            authorization_response=authorization_url,
        )
        return token

    def get_bungie_user_linked_profiles(self):
        token = session.get("oauth_token")
        res = self.bungie_client.get(
            f"{DESTINY_BASE_URL}/254/Profile/{token['membership_id']}/LinkedProfiles/"
        ).json()

        return User.from_json(res)

    def get_characters(self):

        membership_type = session.get("destiny_membership_type")
        membership_id = session.get("destiny_membership_id")

        res = self.bungie_client.get(
            f"{DESTINY_BASE_URL}/{membership_type}/Profile/{membership_id}/?components={DestinyComponentType.Characters.value}"
        ).json()

        manifest = DestinyManifest()
        race_defs = manifest.get_table("DestinyRaceDefinition")
        gender_defs = manifest.get_table("DestinyGenderDefinition")
        class_defs = manifest.get_table("DestinyClassDefinition")

        characters = {}
        for character_id, character_data in res["Response"]["characters"][
            "data"
        ].items():
            race = race_defs.get(str(character_data.get("raceHash")))
            character_class = class_defs.get(str(character_data.get("classHash")))
            characters[character_id] = {
                "class": character_class["displayProperties"]["name"],
                "genderAndRaceDescription": race["genderedRaceNamesByGenderHash"][
                    str(character_data.get("genderHash"))
                ],
                "dateLastPlayed": character_data.get("dateLastPlayed"),
                "light": character_data.get("light"),
                "emblemBackgroundPath": character_data.get("emblemBackgroundPath"),
            }
        return characters
