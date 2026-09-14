import pytest
from conftest import TEST_PASSPHRASE, Repository
from flask import Flask
from flask.testing import FlaskClient


def test_private_routes_require_login(app: Flask) -> None:
    response = app.test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_authenticates_and_logout_clears_session(app: Flask, repository: Repository) -> None:
    client = app.test_client()

    response = client.post("/login", data={"passphrase": TEST_PASSPHRASE})
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert client.get("/").status_code == 200

    assert client.post("/logout").status_code == 302
    assert client.get("/").status_code == 302
    with client.session_transaction() as session:
        assert not session.get("authenticated")


def test_rejected_login_keeps_dashboard_private(app: Flask) -> None:
    client = app.test_client()

    response = client.post("/login", data={"passphrase": "wrong"})

    assert response.status_code == 200
    assert b"Incorrect passphrase" in response.data
    assert client.get("/").status_code == 302
    with client.session_transaction() as session:
        assert not session.get("authenticated")


@pytest.mark.parametrize("path", ["/login", "/subscriptions/add"])
def test_csrf_rejection_renders_error_without_changes(
    app: Flask, authenticated_client: FlaskClient, repository: Repository, path: str
) -> None:
    app.config["WTF_CSRF_ENABLED"] = True

    response = authenticated_client.post(path)

    assert response.status_code == 400
    assert b'id="csrf-title"' in response.data
    with authenticated_client.session_transaction() as session:
        assert session.get("authenticated") is True
    repository.commit.assert_not_called()


def test_calendar_token_is_only_exposed_on_authenticated_dashboard(
    app: Flask, authenticated_client: FlaskClient
) -> None:
    token = app.config["CALENDAR_FEED_TOKEN"].encode()

    assert token not in app.test_client().get("/login").data
    assert token not in app.test_client().get("/").data
    assert token in authenticated_client.get("/").data


def test_invalid_calendar_token_is_public_but_hidden(app: Flask) -> None:
    assert app.test_client().get("/calendar/not-the-token.ics").status_code == 404


def test_valid_calendar_token_returns_feed_without_login(app: Flask, repository: Repository) -> None:
    token = app.config["CALENDAR_FEED_TOKEN"]

    response = app.test_client().get(f"/calendar/{token}.ics")

    assert response.status_code == 200
    assert response.content_type == "text/calendar; charset=utf-8"
    assert response.headers["Content-Disposition"] == "inline; filename=subscription.ics"
    assert response.data.startswith(b"BEGIN:VCALENDAR")


def test_login_is_rate_limited_by_remote_address(app: Flask) -> None:
    client = app.test_client()
    statuses = [
        client.post(
            "/login",
            data={"passphrase": "wrong"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.8"},
        ).status_code
        for _ in range(6)
    ]

    assert statuses == [200, 200, 200, 200, 200, 429]
    assert (
        client.post(
            "/login",
            data={"passphrase": "wrong"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.9"},
        ).status_code
        == 200
    )
