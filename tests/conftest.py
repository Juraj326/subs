from collections.abc import Iterator
from dataclasses import dataclass, field
from unittest.mock import Mock

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from subs import create_app
from subs.extensions import db
from subs.models.subscription import Subscription
from subs.repositories import subscription as subscription_repository
from subs.services import calendar as calendar_service

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


@dataclass
class Repository:
    rows: list[Subscription] = field(default_factory=list)
    commit: Mock = field(default_factory=Mock)
    rollback: Mock = field(default_factory=Mock)


@pytest.fixture
def repository(app: Flask, monkeypatch: pytest.MonkeyPatch) -> Repository:
    """Replace database I/O while exercising the real routes, forms and services."""
    repository = Repository()

    def add(subscription: Subscription) -> None:
        subscription.id = max((row.id for row in repository.rows), default=0) + 1
        repository.rows.append(subscription)

    def find_service(service: str, exclude_subscription_id: int | None = None) -> Subscription | None:
        return next(
            (
                row
                for row in repository.rows
                if row.service.strip().lower() == service.strip().lower() and row.id != exclude_subscription_id
            ),
            None,
        )

    monkeypatch.setattr(subscription_repository, "get_all_subscriptions", lambda: list(repository.rows))
    monkeypatch.setattr(calendar_service, "get_all_subscriptions", lambda: list(repository.rows))
    monkeypatch.setattr(
        subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: next((row for row in repository.rows if row.id == subscription_id), None),
    )
    monkeypatch.setattr(subscription_repository, "get_subscription_by_service", find_service)
    monkeypatch.setattr(subscription_repository, "add_subscription", add)
    monkeypatch.setattr(subscription_repository, "delete_subscription", repository.rows.remove)
    monkeypatch.setattr(db.session, "commit", repository.commit)
    monkeypatch.setattr(db.session, "rollback", repository.rollback)
    return repository


@pytest.fixture
def authenticated_client(app: Flask, repository: Repository) -> FlaskClient:
    client = app.test_client()
    assert client.post("/login", data={"passphrase": TEST_PASSPHRASE}).status_code == 302
    return client
