from collections.abc import Iterator

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from subs import create_app

TEST_PASSPHRASE = "correct horse battery staple"
TEST_PASSPHRASE_HASH = generate_password_hash(TEST_PASSPHRASE, method="pbkdf2:sha256:1")


@pytest.fixture
def app_config() -> dict[str, object]:
    return {
        "TESTING": True,
        "APP_ENV": "test",
        "DATABASE_URL": ("postgresql+psycopg://test:test@localhost/subscriptions_test"),
        "SECRET_KEY": "test-secret-key-that-is-at-least-32-characters",
        "PASSPHRASE_HASH": TEST_PASSPHRASE_HASH,
        "CALENDAR_FEED_TOKEN": "test-calendar-token-that-is-32-characters",
        "TIMEZONE": "Europe/Bratislava",
        "WTF_CSRF_ENABLED": False,
    }


@pytest.fixture
def app(app_config: dict[str, object]) -> Iterator[Flask]:
    application = create_app(app_config)
    with application.app_context():
        yield application
