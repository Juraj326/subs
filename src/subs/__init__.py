import hashlib
import os
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for
from werkzeug import Response

from subs.blueprints.auth import bp as auth_bp
from subs.blueprints.calendar import bp as ical_bp
from subs.blueprints.subscriptions import bp as subs_bp

from .extensions import csrf, db, limiter, migrate
from .models import Subscription as Subscription


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(import_name=__name__)
    app.config.from_mapping(_load_config(test_config))

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
    config["SQLALCHEMY_DATABASE_URI"] = re.sub(
        r"^postgresql:", "postgresql+psycopg:", database_url
    )

    storage_uri = config.get("RATELIMIT_STORAGE_URI")
    if environment == "production":
        if not isinstance(storage_uri, str) or not _is_shared_redis_uri(storage_uri):
            raise RuntimeError(
                "RATELIMIT_STORAGE_URI must use shared Redis in production"
            )
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
    if not _is_valid_password_hash(passphrase_hash):
        raise RuntimeError("PASSPHRASE_HASH is not a complete Werkzeug password hash")

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


def _is_valid_password_hash(password_hash: str) -> bool:
    try:
        method, salt, digest = password_hash.split("$")
    except ValueError:
        return False

    if not re.fullmatch(r"[A-Za-z0-9]+", salt):
        return False
    if not re.fullmatch(r"[0-9a-f]+", digest):
        return False

    method_parts = method.split(":")
    if method_parts[0] == "scrypt" and len(method_parts) == 4:
        try:
            n, r, p = (int(value) for value in method_parts[1:])
        except ValueError:
            return False
        return n > 1 and n & (n - 1) == 0 and r > 0 and p > 0 and len(digest) == 128

    if method_parts[0] == "pbkdf2" and len(method_parts) == 3:
        try:
            iterations = int(method_parts[2])
            digest_size = len(
                hashlib.pbkdf2_hmac(method_parts[1], b"password", b"salt", 1)
            )
        except TypeError, ValueError:
            return False
        return iterations > 0 and digest_size > 0 and len(digest) == digest_size * 2

    return False
