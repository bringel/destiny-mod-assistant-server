import os

from flask import Flask, redirect, request, session
from flask.json import jsonify
from requests_oauthlib import OAuth2Session
from sqlalchemy import create_engine, text


def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get("SECRET_KEY")

    @app.route("/login")
    def login():
        bungie = OAuth2Session(os.environ.get("OAUTH_CLIENT_ID"))
        authorization_url, state = bungie.authorization_url(
            os.environ.get("BUNGIE_AUTHORIZATION_URL")
        )

        session["oauth_state"] = state
        print(state)
        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        bungie = OAuth2Session(
            os.environ.get("OAUTH_CLIENT_ID"), state=session["oauth_state"]
        )
        token = bungie.fetch_token(
            os.environ.get("BUNGIE_TOKEN_URL"),
            client_secret=os.environ.get("OAUTH_CLIENT_SECRET"),
            authorization_response=request.url,
        )

        session["oauth_token"] = token

        user = bungie.get(
            f"https://bungie.net/Platform/Destiny2/254/Profile/{session['oauth_token']['membership_id']}/LinkedProfiles/",
            headers={"X-API-KEY": os.environ.get("BUNGIE_API_KEY")},
        ).json()

        print(user)
        profile = user["Response"]["profiles"][0]
        membership_type = profile["membershipType"]
        membership_id = profile["membershipId"]
        display_name = f"{profile['bungieGlobalDisplayName']}#{profile['bungieGlobalDisplayNameCode']}"

        engine = create_engine(os.environ.get("DB_CONNECTION_STRING"))
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (destiny_membership_type, destiny_membership_id, display_name) VALUES (:membership_type, :membership_id, :display_name) ON CONFLICT DO NOTHING;"
                ),
                membership_type=membership_type,
                membership_id=membership_id,
                display_name=display_name,
            )

        return jsonify(user)

    return app
