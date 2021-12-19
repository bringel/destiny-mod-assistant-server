import os

from flask import Flask, redirect, request, session
from flask.json import jsonify
from flask_session import Session

from api_server.database import db
from api_server.destiny_api import DestinyAPI
from api_server.models import User
from api_server.repositories.user_repository import UserRepository


def create_app():

    app = Flask(__name__)

    app.secret_key = os.environ.get("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    db.init_app(app)
    app.config["SESSION_TYPE"] = "sqlalchemy"
    app.config["SESSION_SQLALCHEMY"] = db
    Session(app)

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

        user_repository = UserRepository()
        existing_user = user_repository.get_user(
            user.destiny_membership_type, user.destiny_membership_id
        )

        if existing_user is None:
            user_repository.create_user(user)

        return redirect(os.environ.get("APP_URL"))

    return app
