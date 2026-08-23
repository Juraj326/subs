import os
import re

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for

from subs.blueprints.auth import bp as auth_bp
from subs.blueprints.calendar import bp as ical_bp
from subs.blueprints.subscriptions import bp as subs_bp

from .extensions import db, migrate
from .models import subscription


def create_app() -> Flask:
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
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(subs_bp)
    app.register_blueprint(ical_bp)

    @app.before_request
    def auth_required():
        public_endpoints = {"auth.login", "auth.logout", "calendar.ical", "static"}
        if not request.endpoint:
            return
        if request.endpoint in public_endpoints or session.get("authenticated"):
            return

        return redirect(url_for("auth.login"))

    return app
