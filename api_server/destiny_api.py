import os
from enum import Enum

from flask import session
from requests_oauthlib import OAuth2Session

from api_server.destiny_manifest import DestinyManifest
from api_server.models import (
    BUCKET_HASH_ARMOR_TYPE_MAPPING,
    SUBCLASSS_BUCKET_HASH,
    ArmorPiece,
    AspectSubclass,
    Character,
    FullCharacterData,
    TreeStyleSubclass,
    User,
)

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


DESTINY_BASE_URL = "https://www.bungie.net/Platform/Destiny2"


class DestinyAPI:
    def get_client(self):
        token = session.get("oauth_token")

        client_id = os.environ.get("OAUTH_CLIENT_ID")
        client_secret = os.environ.get("OAUTH_CLIENT_SECRET")

        if token is not None:

            auto_refresh_extra = {
                "client_id": client_id,
                "client_secret": client_secret,
            }

            def token_updater(token):
                session["oauth_token"] = token

            c = OAuth2Session(
                client_id,
                token=token,
                auto_refresh_url=os.environ.get("BUNGIE_TOKEN_URL"),
                auto_refresh_kwargs=auto_refresh_extra,
                token_updater=token_updater,
            )
            c.headers.update(headers)
            return c
        else:
            state = session.get("oauth_state")
            client_id = os.environ.get("OAUTH_CLIENT_ID")
            c = OAuth2Session(client_id, state=state)
            c.headers.update(headers)
            return c

    def get_bungie_user_linked_profiles(self):
        token = session.get("oauth_token")
        res = (
            self.get_client()
            .get(
                f"{DESTINY_BASE_URL}/254/Profile/{token['membership_id']}/LinkedProfiles/"
            )
            .json()
        )

        return User.from_json(res)

    def get_characters(self):

        membership_type = session.get("destinyMembershipType")
        membership_id = session.get("destinyMembershipID")

        res = (
            self.get_client()
            .get(
                f"{DESTINY_BASE_URL}/{membership_type}/Profile/{membership_id}/?components={DestinyComponentType.Characters.value}"
            )
            .json()
        )

        manifest = DestinyManifest()
        race_defs = manifest.get_table("DestinyRaceDefinition")

        class_defs = manifest.get_table("DestinyClassDefinition")

        characters = []
        for character_data in res["Response"]["characters"]["data"].values():
            characters.append(
                Character.from_json(character_data, race_defs, class_defs)
            )
        return characters

    def get_character(self, character_id):

        membership_type = session.get("destinyMembershipType")
        membership_id = session.get("destinyMembershipID")

        components = [
            DestinyComponentType.Characters,
            DestinyComponentType.CharacterInventories,
            DestinyComponentType.CharacterEquipment,
            DestinyComponentType.ItemInstances,
            DestinyComponentType.ItemSockets,
            DestinyComponentType.ItemTalentGrids,
        ]

        res = (
            self.get_client()
            .get(
                f"{DESTINY_BASE_URL}/{membership_type}/Profile/{membership_id}/Character/{character_id}?components={','.join([str(c.value) for c in components])}"
            )
            .json()
        )

        manifest = DestinyManifest()
        inventory_item_defs = manifest.get_table("DestinyInventoryItemDefinition")
        race_defs = manifest.get_table("DestinyRaceDefinition")
        class_defs = manifest.get_table("DestinyClassDefinition")
        talent_grid_defs = manifest.get_table("DestinyTalentGridDefinition")

        character_res = res["Response"]["character"]["data"]
        equipment_res = res["Response"]["equipment"]["data"]["items"]
        instances = res["Response"]["itemComponents"]["instances"]["data"]
        sockets = res["Response"]["itemComponents"]["sockets"]["data"]
        talentGrids = res["Response"]["itemComponents"]["talentGrids"]["data"]

        armor_responses = [
            e
            for e in equipment_res
            if e["bucketHash"] in BUCKET_HASH_ARMOR_TYPE_MAPPING.keys()
        ]

        armor = []

        for a in armor_responses:
            instance = instances.get(a["itemInstanceId"])
            socket_response = sockets[a["itemInstanceId"]]["sockets"]
            armor.append(
                ArmorPiece.from_json(a, instance, socket_response, inventory_item_defs)
            )

        equipment_subclass = [
            e for e in equipment_res if e["bucketHash"] == SUBCLASSS_BUCKET_HASH
        ][0]

        talent_grid = talentGrids[str(equipment_subclass["itemInstanceId"])]

        if talent_grid["talentGridHash"] == 0:
            subclass_socket_response = sockets[equipment_subclass["itemInstanceId"]][
                "sockets"
            ]
            subclass = AspectSubclass.from_json(
                equipment_subclass, subclass_socket_response, inventory_item_defs
            )
        else:
            subclass = TreeStyleSubclass.from_json(
                equipment_subclass,
                talent_grid,
                inventory_item_defs,
                talent_grid_defs,
            )

        character = Character.from_json(character_res, race_defs, class_defs)

        return FullCharacterData(character=character, armor=armor, subclass=subclass)
