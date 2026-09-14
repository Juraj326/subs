import os
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError
from werkzeug import Response

from subs.assets import get_frontend_assets
from subs.blueprints.auth import bp as auth_bp
from subs.blueprints.calendar import bp as ical_bp
from subs.blueprints.subscriptions import bp as subs_bp
from subs.formatting import format_eur

from .extensions import csrf, db, limiter, migrate
from .models import Subscription as Subscription


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(
        import_name=__name__,
        static_folder=None,
    )
    app.config.from_mapping(_load_config(test_config))

    db.init_app(app)
    migrate.init_app(app, db, compare_server_default=True)
    csrf.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(subs_bp)
    app.register_blueprint(ical_bp)

    @app.context_processor
    def frontend_context() -> dict[str, object]:
        return {"frontend_assets": get_frontend_assets(app)}

    app.add_template_filter(format_eur, "eur")

    @app.errorhandler(CSRFError)
    def handle_csrf_error(_error: CSRFError) -> tuple[str, int]:
        return render_template("errors/csrf.html"), 400

    @app.before_request
    def auth_required() -> Response | None:
        public_endpoints = {"auth.login", "auth.logout", "calendar.ical"}
        if not request.endpoint:
            return
        if request.endpoint in public_endpoints or session.get("authenticated"):
            return

        return redirect(url_for("auth.login"))

    return app


def _load_config(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    load_dotenv()

    config: dict[str, Any] = {
        "APP_ENV": os.environ.get("APP_ENV"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "RATELIMIT_STORAGE_URI": os.environ.get("RATELIMIT_STORAGE_URI"),
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "PASSPHRASE_HASH": os.environ.get("PASSPHRASE_HASH"),
        "CALENDAR_FEED_TOKEN": os.environ.get("CALENDAR_FEED_TOKEN"),
        "TIMEZONE": os.environ.get("TIMEZONE"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    }

    if overrides:
        config.update(overrides)

    _validate_and_normalize_config(config)
    return config


def _validate_and_normalize_config(config: dict[str, Any]) -> None:
    environment = config.get("APP_ENV")
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production")

    database_url = config.get("DATABASE_URL")
    if not isinstance(database_url, str) or not database_url:
        raise RuntimeError("Database URL must be configured")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    config["SQLALCHEMY_DATABASE_URI"] = re.sub(r"^postgresql:", "postgresql+psycopg:", database_url)

    storage_uri = config.get("RATELIMIT_STORAGE_URI")
    if environment == "production":
        if not isinstance(storage_uri, str) or not _is_shared_redis_uri(storage_uri):
            raise RuntimeError("RATELIMIT_STORAGE_URI must use shared Redis in production")
    elif not storage_uri:
        config["RATELIMIT_STORAGE_URI"] = "memory://"

    secret_key = config.get("SECRET_KEY")
    if not isinstance(secret_key, str) or not secret_key:
        raise RuntimeError("SECRET_KEY must be configured")
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters")

    passphrase_hash = config.get("PASSPHRASE_HASH")
    if not isinstance(passphrase_hash, str) or not passphrase_hash:
        raise RuntimeError("PASSPHRASE_HASH must be configured")
    hash_parts = passphrase_hash.split("$")
    if len(hash_parts) != 3 or not all(hash_parts):
        raise RuntimeError("PASSPHRASE_HASH must have the format method$salt$digest")

    calendar_feed_token = config.get("CALENDAR_FEED_TOKEN")
    if not isinstance(calendar_feed_token, str) or not calendar_feed_token:
        raise RuntimeError("CALENDAR_FEED_TOKEN must be configured")
    if len(calendar_feed_token) < 32:
        raise RuntimeError("CALENDAR_FEED_TOKEN must be at least 32 characters")

    timezone = config.get("TIMEZONE")
    if isinstance(timezone, str):
        try:
            config["TIMEZONE"] = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            raise RuntimeError("TIMEZONE must be a valid IANA timezone")
    elif not isinstance(timezone, ZoneInfo):
        raise TypeError("TIMEZONE must be configured as a valid IANA timezone")

    config["SESSION_COOKIE_SECURE"] = environment == "production"


def _is_shared_redis_uri(storage_uri: str) -> bool:
    parsed_uri = urlsplit(storage_uri)
    return parsed_uri.scheme in {"redis", "rediss"} and parsed_uri.hostname is not None
