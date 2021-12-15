from flask import Flask, session, redirect, request
from requests_oauthlib import OAuth2Session
import os


def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get("SECRET_KEY")

    @app.route("/login")
    def login():
        bungie = OAuth2Session(os.environ.get("OAUTH_CLIENT_ID"))
        authorization_url, state = bungie.authorization_url(
            "https://www.bungie.net/en/oauth/authorize"
        )

        session["oauth_state"] = state
        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        bungie = OAuth2Session(
            os.environ.get("OAUTH_CLIENT_ID"), state=session["oauth_state"]
        )
        token = bungie.fetch_token(
            "https://www.bungie.net/platform/app/oauth/token/",
            client_secret=os.environ.get("OAUTH_CLIENT_SECRET"),
            authorization_response=request.url,
        )

        session["oauth_token"] = token

        return redirect("/")

    return app
