import os

from api_server.database import db
from api_server.models import User
from api_server.tables import users_table
from sqlalchemy import insert, select


class UserRepository:
    def get_user(self, destiny_membership_type, destiny_membership_id):
        with db.begin() as connection:
            statement = select(users_table).where(
                users_table.c.destiny_membership_type == destiny_membership_type,
                users_table.c.destiny_membership_id == destiny_membership_id,
            )

            result = connection.execute(statement).one_or_none()

            if result is None:
                return None
            else:
                return User.from_db(result)

    def create_user(self, user: User):
        with db.begin() as connection:
            statement = insert(users_table).returning(
                users_table.c.destiny_membership_type,
                users_table.c.destiny_membership_id,
                users_table.c.display_name,
            )
            connection.execute(
                statement,
                {
                    "destiny_membership_type": user.destiny_membership_type,
                    "destiny_membership_id": user.destiny_membership_id,
                    "display_name": user.display_name,
                },
            )
