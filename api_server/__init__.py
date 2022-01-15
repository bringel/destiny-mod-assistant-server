import os

from flask import Flask, redirect, request, session
from flask.json import jsonify
from flask_cors import CORS
from flask_session import Session
from requests_oauthlib.oauth2_session import OAuth2Session
from werkzeug.middleware.profiler import ProfilerMiddleware

from api_server.database import db
from api_server.destiny_api import DestinyAPI
from api_server.models import User
from api_server.repositories.user_repository import UserRepository

sess = Session()


def create_app():

    app = Flask(__name__)
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.secret_key = os.environ.get("SECRET_KEY")
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    CORS(app, origins=["http://localhost:3000"], supports_credentials=True)
    app.config["SESSION_TYPE"] = "redis"
    sess.init_app(app)

    @app.route("/login")
    def login():
        client_id = os.environ.get("OAUTH_CLIENT_ID")
        destiny = OAuth2Session(client_id)
        authorization_url, state = destiny.authorization_url(
            os.environ.get("BUNGIE_AUTHORIZATION_URL")
        )

        session["oauth_state"] = state

        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        client_id = os.environ.get("OAUTH_CLIENT_ID")
        client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
        token_url = os.environ.get("BUNGIE_TOKEN_URL")

        destiny = OAuth2Session(client_id, state=session["oauth_state"])
        token = destiny.fetch_token(
            token_url, client_secret=client_secret, authorization_response=request.url
        )

        session["oauth_token"] = token

        destiny_api = DestinyAPI()
        user = destiny_api.get_bungie_user_linked_profiles()

        session["destinyMembershipType"] = user.destinyMembershipType
        session["destinyMembershipID"] = user.destinyMembershipID

        user_repository = UserRepository()
        existing_user = user_repository.get_user(
            user.destinyMembershipType, user.destinyMembershipID
        )

        if existing_user is None:
            user_repository.create_user(user)

        return redirect(os.environ.get("APP_URL"))

    @app.route("/user")
    def get_user():
        user_repository = UserRepository()

        membership_type = session.get("destinyMembershipType")
        membership_id = session.get("destinyMembershipID")

        user = user_repository.get_user(membership_type, membership_id)

        res = jsonify(user)

        return res

    @app.route("/characters")
    def get_characters():
        destiny_api = DestinyAPI()

        return jsonify(destiny_api.get_characters())

    @app.route("/characters/<character_id>")
    def get_character(character_id):
        destiny_api = DestinyAPI()

        return jsonify(destiny_api.get_character(character_id))

    return app
