import pytest
from flask import Flask

from subs import create_app
from subs.blueprints import calendar as calendar_blueprint

TEST_PASSPHRASE = "correct horse battery staple"


def test_private_route_redirects_to_login(app: Flask) -> None:
    response = app.test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_authenticates_and_logout_clears_session(app: Flask) -> None:
    client = app.test_client()

    response = client.post("/login", data={"passphrase": TEST_PASSPHRASE})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert client.get("/").status_code == 200

    response = client.post("/logout")
    assert response.status_code == 302
    assert client.get("/").status_code == 302


def test_csrf_rejects_state_changing_request(
    app_config: dict[str, object],
) -> None:
    app = create_app(app_config | {"WTF_CSRF_ENABLED": True})

    response = app.test_client().post("/login", data={"passphrase": TEST_PASSPHRASE})

    assert response.status_code == 400


def test_invalid_calendar_token_is_public_but_hidden(app: Flask) -> None:
    response = app.test_client().get("/calendar/not-the-token.ics")

    assert response.status_code == 404


def test_valid_calendar_token_returns_icalendar(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        calendar_blueprint,
        "get_calendar_ics",
        lambda: b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
    )
    token = app.config["CALENDAR_FEED_TOKEN"]

    response = app.test_client().get(f"/calendar/{token}.ics")

    assert response.status_code == 200
    assert response.content_type == "text/calendar; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        "inline; filename=subscription.ics"
    )
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
