import pytest

from subs import create_app


def test_production_requires_shared_redis(app_config: dict[str, object]) -> None:
    with pytest.raises(RuntimeError, match="shared Redis"):
        create_app(app_config | {"APP_ENV": "production", "RATELIMIT_STORAGE_URI": None})


def test_production_enables_secure_cookie(app_config: dict[str, object]) -> None:
    app = create_app(
        app_config | {"APP_ENV": "production", "RATELIMIT_STORAGE_URI": "rediss://redis.example.test:6380/0"}
    )

    assert app.config["SESSION_COOKIE_SECURE"] is True
