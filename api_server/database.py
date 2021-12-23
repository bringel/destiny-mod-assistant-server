import os

from sqlalchemy import create_engine
from sqlalchemy.sql.schema import MetaData

db = create_engine(os.environ.get("DATABASE_URL"))

metadata = MetaData(bind=db)
