from sqlalchemy import BigInteger, Column, Integer, String, Table

from api_server.database import db

users_table = Table(
    "users",
    db.metadata,
    Column("destiny_membership_type", Integer, nullable=False, primary_key=True),
    Column("destiny_membership_id", BigInteger, nullable=False, primary_key=True),
    Column("display_name", String),
)
