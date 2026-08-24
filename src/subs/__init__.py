import os
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for
from werkzeug import Response

from subs.blueprints.auth import bp as auth_bp
from subs.blueprints.calendar import bp as ical_bp
from subs.blueprints.subscriptions import bp as subs_bp

from .extensions import csrf, db, limiter, migrate
from .models import subscription


def create_app() -> Flask:
    app = Flask(import_name=__name__)

    app.config.from_mapping(_load_config())

    db.init_app(app)
    migrate.init_app(app, db, compare_server_default=True)
    csrf.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(subs_bp)
    app.register_blueprint(ical_bp)

    @app.before_request
    def auth_required() -> Response | None:
        public_endpoints = {"auth.login", "auth.logout", "calendar.ical", "static"}
        if not request.endpoint:
            return
        if request.endpoint in public_endpoints or session.get("authenticated"):
            return

        return redirect(url_for("auth.login"))

    return app


def _load_config() -> dict[str, str | ZoneInfo]:
    load_dotenv()

    config_mapping = {}

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Database URL must be configured")
    if not db_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    config_mapping["SQLALCHEMY_DATABASE_URI"] = re.sub(
        r"^postgresql:", "postgresql+psycopg:", db_url
    )

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY must be configured")
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters")
    config_mapping["SECRET_KEY"] = secret_key

    passphrase_hash = os.environ.get("PASSPHRASE_HASH")
    if not passphrase_hash:
        raise RuntimeError("PASSPHRASE_HASH must be configured")
    if not passphrase_hash.startswith(("scrypt:", "pbkdf2:")):
        raise RuntimeError("PASSPHRASE_HASH is not a recognized password hash")
    config_mapping["PASSPHRASE_HASH"] = passphrase_hash

    calendar_feed_token = os.environ.get("CALENDAR_FEED_TOKEN")
    if not calendar_feed_token:
        raise RuntimeError("CALENDAR_FEED_TOKEN must be configured")
    if len(calendar_feed_token) < 32:
        raise RuntimeError("CALENDAR_FEED_TOKEN must be at least 32 characters")
    config_mapping["CALENDAR_FEED_TOKEN"] = calendar_feed_token

    timezone = os.environ.get("TIMEZONE")
    if not timezone:
        raise RuntimeError("TIMEZONE must be configured")
    try:
        config_mapping["TIMEZONE"] = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise RuntimeError("TIMEZONE must be a valid IANA timezone")

    # config_mapping["SESSION_COOKIE_SECURE"] = True
    config_mapping["SESSION_COOKIE_SAMESITE"] = "Lax"

    ratelimit_storage_uri = os.environ.get("RATELIMIT_STORAGE_URI")
    if ratelimit_storage_uri:
        config_mapping["RATELIMIT_STORAGE_URI"] = ratelimit_storage_uri

    return config_mapping
