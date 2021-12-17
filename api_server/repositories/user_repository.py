import os

from sqlalchemy import create_engine, text


class UserRepository:
    def __init__(self):
        self.engine = create_engine(os.environ.get("DB_CONNECTION_STRING"))

    def get_user(self, destiny_membership_type, destiny_membership_id):
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "SELECT * from users WHERE users.destiny_membership_type = :type AND users.destiny_membership_id = :id LIMIT 1;"
                ),
                type=destiny_membership_type,
                id=destiny_membership_id,
            )
            return result.one_or_none()

    def create_user(self, destiny_membership_type, destiny_membership_id, display_name):
        with self.engine.begin() as connection:
            res = connection.execute(
                text(
                    "INSERT INTO users (destiny_membership_type, destiny_membership_id, display_name) VALUES (:type, :id, :name) RETURNING *"
                ),
                type=destiny_membership_type,
                id=destiny_membership_id,
                name=display_name,
            )

            return dict(res.one_or_none())
