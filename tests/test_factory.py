from collections.abc import Mapping

import pytest
from flask import Flask

from subs import create_app


def _config(base: Mapping[str, object], **overrides: object) -> dict[str, object]:
    config = dict(base)
    config.update(overrides)
    return config


def test_factory_accepts_test_config_and_converts_postgres_uri(
    app_config: dict[str, object],
) -> None:
    config = _config(
        app_config,
        DATABASE_URL="postgresql://test:test@localhost/test",
    )

    app = create_app(config)

    assert app.config["DATABASE_URL"] == "postgresql://test:test@localhost/test"
    assert str(app.config["SQLALCHEMY_DATABASE_URI"]).startswith(
        "postgresql+psycopg://"
    )
    assert app.config["APP_ENV"] == "test"
    assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"


@pytest.mark.parametrize(
    "password_hash",
    [
        "scrypt:",
        "scrypt:32768:8:1$missing-digest",
        "scrypt:32768:8:1$salt$not-hex",
        "pbkdf2:sha256:abc$salt$" + "a" * 64,
        "unknown:1$salt$" + "a" * 64,
    ],
)
def test_factory_rejects_malformed_complete_hash(
    app_config: dict[str, object], password_hash: str
) -> None:
    with pytest.raises(RuntimeError, match="complete Werkzeug password hash"):
        create_app(_config(app_config, PASSPHRASE_HASH=password_hash))


def test_factory_rejects_non_postgres_database(
    app_config: dict[str, object],
) -> None:
    with pytest.raises(RuntimeError, match="must use PostgreSQL"):
        create_app(_config(app_config, DATABASE_URL="sqlite+pysqlite:///:memory:"))


def test_production_requires_redis_and_enables_secure_cookie(
    app_config: dict[str, object],
) -> None:
    with pytest.raises(RuntimeError, match="shared Redis"):
        create_app(
            _config(
                app_config,
                APP_ENV="production",
                RATELIMIT_STORAGE_URI=None,
            )
        )

    app = create_app(
        _config(
            app_config,
            APP_ENV="production",
            RATELIMIT_STORAGE_URI="rediss://redis.example.test:6380/0",
        )
    )

    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["RATELIMIT_STORAGE_URI"].startswith("rediss://")


def test_production_rejects_incomplete_redis_uri(
    app_config: dict[str, object],
) -> None:
    with pytest.raises(RuntimeError, match="shared Redis"):
        create_app(
            _config(
                app_config,
                APP_ENV="production",
                RATELIMIT_STORAGE_URI="redis://",
            )
        )


def test_local_and_test_apps_allow_http_cookies(app: Flask) -> None:
    assert app.config["SESSION_COOKIE_SECURE"] is False
