import json
import os

import redis
import requests

headers = {"X-API-KEY": os.environ.get("BUNGIE_API_KEY")}


class DestinyManifest:
    def __init__(self):
        self.redis = redis.Redis.from_url(
            os.environ.get("REDIS_URL"), decode_responses=True
        )

    def update_manifest_if_needed(self):
        urls = requests.get(
            "https://www.bungie.net/Platform/Destiny2/Manifest/", headers=headers
        ).json()

        version = urls["Response"]["version"]
        saved_manifest_version = self.redis.get("manifest:version")

        if version != saved_manifest_version:
            content_path = urls["Response"]["jsonWorldContentPaths"]["en"]
            data = requests.get(
                f"https://bungie.net/{content_path}", headers=headers
            ).json()
            self.redis.set("manifest:version", version)

            for table_name, table_data in data.items():
                self.redis.set(f"manifest:{table_name}", json.dumps(table_data))

    def get_table(self, table_name):
        data = self.redis.get(f"manifest:{table_name}")

        return json.loads(data)
