import os

from api_server.database import db
from api_server.tables import users_table
from sqlalchemy import insert, select


class UserRepository:
    def get_user(self, destiny_membership_type, destiny_membership_id):
        with db.engine.begin() as connection:
            statement = select(users_table).where(
                users_table.c.destiny_membership_type == destiny_membership_type,
                users_table.c.destiny_membership_id == destiny_membership_id,
            )

            result = connection.execute(statement)
            return result.one_or_none()

    def create_user(self, destiny_membership_type, destiny_membership_id, display_name):
        with db.engine.begin() as connection:
            statement = insert(users_table).returning(
                users_table.c.destiny_membership_type,
                users_table.c.destiny_membership_id,
                users_table.c.display_name,
            )
            res = connection.execute(
                statement,
                {
                    "destiny_membership_type": destiny_membership_type,
                    "destiny_membership_id": destiny_membership_id,
                    "display_name": display_name,
                },
            )

            return res.one_or_none()
