import os

from flask import Flask, redirect, request, session
from flask.json import jsonify
from flask_cors import CORS
from flask_session import Session

from api_server.database import db
from api_server.destiny_api import DestinyAPI
from api_server.destiny_manifest import DestinyManifest
from api_server.models import User
from api_server.repositories.user_repository import UserRepository

sess = Session()


def create_app():

    app = Flask(__name__)
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
        destiny_api = DestinyAPI()
        authorization_url, state = destiny_api.get_authorization_url()

        session["oauth_state"] = state

        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        destiny_api = DestinyAPI()
        token = destiny_api.fetch_token(request.url)

        session["oauth_token"] = token

        user = destiny_api.get_bungie_user_linked_profiles()

        session["destiny_membership_type"] = user.destiny_membership_type
        session["destiny_membership_id"] = user.destiny_membership_id

        user_repository = UserRepository()
        existing_user = user_repository.get_user(
            user.destiny_membership_type, user.destiny_membership_id
        )

        if existing_user is None:
            user_repository.create_user(user)

        return redirect(os.environ.get("APP_URL"))

    @app.route("/user")
    def get_user():
        user_repository = UserRepository()

        membership_type = session.get("destiny_membership_type")
        membership_id = session.get("destiny_membership_id")

        user = user_repository.get_user(membership_type, membership_id)

        res = jsonify(user)

        return res

    return app
