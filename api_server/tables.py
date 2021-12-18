from datetime import time

from sqlalchemy import TIMESTAMP, BigInteger, Column, Integer, String, Table, func

from api_server.database import db

users_table = Table(
    "users",
    db.metadata,
    Column("destiny_membership_type", Integer, nullable=False, primary_key=True),
    Column("destiny_membership_id", BigInteger, nullable=False, primary_key=True),
    Column("display_name", String),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        default=func.current_timestamp(),
        nullable=False,
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        default=func.current_timestamp(),
        nullable=False,
    ),
)
