import os
import re

from dotenv import load_dotenv
from flask import Flask

from .extensions import db


def create_app():
    load_dotenv()
    app = Flask(import_name=__name__)

    DB_URL = os.environ.get("DATABASE_URL")
    if not DB_URL:
        raise RuntimeError("Database URL must be configured")
    SQLALCHEMY_URL = re.sub(r"^postgresql:", "postgresql+psycopg:", DB_URL)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=SQLALCHEMY_URL,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        APP_PASSPHRASE_HASH=os.environ.get("APP_PASSPHRASE_HASH"),
        CALENDAR_FEED_TOKEN=os.environ.get("CALENDAR_FEED_TOKEN"),
        APP_TIMEZONE=os.environ.get("APP_TIMEZONE"),
    )

    db.init_app(app)

    return app
