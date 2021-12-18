import os

from flask import session
from requests_oauthlib import OAuth2Session

from api_server.models import User

headers = {"X-API-KEY": os.environ.get("BUNGIE_API_KEY")}


class DestinyAPI:
    def __init__(
        self, *, client_id=None, client_secret=None, oauth_state=None, oauth_token=None
    ):
        self.client_id = client_id or os.environ.get("OAUTH_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("OAUTH_CLIENT_SECRET")
        self.token = oauth_token or session.get("oauth_token")
        self.oauth_state = oauth_state or session.get("oauth_state")

        auto_refresh_extra = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        def token_updater(token):
            session["oauth_token"] = token
            self.token = token

        self.bungie_client = OAuth2Session(
            self.client_id,
            token=self.token,
            state=self.oauth_state,
            auto_refresh_url=os.environ.get("BUNGIE_TOKEN_URL"),
            auto_refresh_kwargs=auto_refresh_extra,
            token_updater=token_updater,
        )

    def get_authorization_url(self):
        return self.bungie_client.authorization_url(
            os.environ.get("BUNGIE_AUTHORIZATION_URL")
        )

    def fetch_token(self, authorization_url):
        return self.bungie_client.fetch_token(
            os.environ.get("BUNGIE_TOKEN_URL"),
            client_secret=self.client_secret,
            authorization_response=authorization_url,
        )

    def get_bungie_user_linked_profiles(self):
        res = self.bungie_client.get(
            f"https://bungie.net/Platform/Destiny2/254/Profile/{self.token['membership_id']}/LinkedProfiles/",
            headers=headers,
        ).json()

        return User.from_json(res)
