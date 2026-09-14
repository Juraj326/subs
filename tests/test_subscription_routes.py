import json
import re
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import Repository
from dateutil.relativedelta import relativedelta
from factories import make_subscription, subscription_input
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError
from werkzeug.test import TestResponse

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.services.subscription import local_today


def _form_data(**overrides: str) -> dict[str, str]:
    return {
        "service": "Netflix",
        "start_date": "31.01.2026",
        "category": "Entertainment",
        "billing_period": "month",
        "billing_interval": "1",
        "billing_date_offset": "2",
        "payment_method": "mBank MasterCard",
        "cost": "12.90",
        "url": "https://www.netflix.com/account",
        "image_url": "https://cdn.example.com/netflix.png",
    } | overrides


def _editor_payload(response: TestResponse) -> dict[str, Any]:
    match = re.search(
        r'<script id="subscription-data" type="application/json">(.*?)</script>', response.get_data(as_text=True)
    )
    assert match is not None
    return json.loads(match[1])


def test_create_saves_normalized_values(authenticated_client: FlaskClient, repository: Repository) -> None:
    response = authenticated_client.post(
        "/subscriptions/add",
        data=_form_data(
            service="  Netflix  ", category="Professional", billing_date_offset="-5", cost="0", url="  ", image_url=""
        ),
        follow_redirects=True,
    )

    assert [item.status_code for item in response.history] == [302]
    assert response.status_code == 200
    assert b"Netflix was added." in response.data
    (saved,) = repository.rows
    expected = subscription_input() | {
        "category": Category.PROFESSIONAL,
        "billing_date_offset": -5,
        "cost": Decimal(0),
        "url": None,
        "image_url": None,
    }
    assert {name: getattr(saved, name) for name in expected} == expected
    assert saved.active is True
    assert saved.end_date is None
    repository.commit.assert_called_once_with()


def test_edit_saves_all_fields_and_reloads_editor(authenticated_client: FlaskClient, repository: Repository) -> None:
    saved = make_subscription()
    repository.rows.append(saved)
    data = _form_data(
        service="Nebula",
        start_date="29.02.2024",
        category="Professional",
        billing_period="year",
        billing_interval="2",
        billing_date_offset="-5",
        payment_method="mBank VISA",
        cost="8.10",
        url="https://nebula.example.com/account",
        image_url="https://nebula.example.com/logo.png",
        active="true",
    )

    response = authenticated_client.post(
        "/subscriptions/1/update", data=data | {"id": "99", "end_date": "01.01.1900"}, follow_redirects=True
    )

    assert [item.status_code for item in response.history] == [302]
    assert response.status_code == 200
    assert b"Nebula was updated." in response.data
    expected = {
        "service": "Nebula",
        "start_date": date(2024, 2, 29),
        "category": Category.PROFESSIONAL,
        "billing_period": BillingPeriod.YEAR,
        "billing_interval": 2,
        "billing_date_offset": -5,
        "payment_method": PaymentMethod.MBANK_VISA,
        "cost": Decimal("8.10"),
        "url": data["url"],
        "image_url": data["image_url"],
        "active": True,
        "id": 1,
        "end_date": None,
    }
    assert {name: getattr(saved, name) for name in expected} == expected
    repository.commit.assert_called_once_with()

    deep_link = authenticated_client.get("/subscriptions/1")
    assert deep_link.status_code == 200
    assert _editor_payload(deep_link)["1"] == {
        "id": 1,
        "values": data,
        "endDate": "",
        "editorUrl": "/subscriptions/1",
        "updateUrl": "/subscriptions/1/update",
        "removeUrl": "/subscriptions/1/remove",
    }
    assert b'value="29.02.2024"' in deep_link.data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("service", "   "),
        ("start_date", "31.02.2026"),
        ("cost", "sNaN"),
        ("url", "ftp://example.com"),
    ],
)
def test_invalid_create_returns_field_error_without_saving(
    authenticated_client: FlaskClient, repository: Repository, field: str, value: str
) -> None:
    response = authenticated_client.post("/subscriptions/add", data=_form_data(**{field: value}))

    assert response.status_code == 422
    assert f'id="{field}-errors"' in response.get_data(as_text=True)
    assert repository.rows == []
    repository.commit.assert_not_called()


def test_invalid_edit_preserves_entered_and_saved_values(
    authenticated_client: FlaskClient, repository: Repository
) -> None:
    saved = make_subscription(active=False, end_date=date(2026, 3, 2))
    repository.rows.append(saved)
    before = dict(vars(saved))
    data = _form_data(service="Unsaved", active="true", cost="sNaN", url="https://unsaved.example.com")

    response = authenticated_client.post("/subscriptions/1/update", data=data)

    assert response.status_code == 422
    assert b'id="cost-errors"' in response.data
    assert b'value="sNaN"' in response.data
    assert b'value="Unsaved"' in response.data
    assert b'value="https://unsaved.example.com"' in response.data
    payload = _editor_payload(response)["1"]
    assert payload["values"] == _form_data(active="false")
    assert payload["endDate"] == "02.03.2026"
    assert vars(saved) == before
    repository.commit.assert_not_called()


def test_invalid_status_is_rejected(authenticated_client: FlaskClient, repository: Repository) -> None:
    saved = make_subscription()
    repository.rows.append(saved)

    response = authenticated_client.post("/subscriptions/1/update", data=_form_data(active="paused"))

    assert response.status_code == 422
    assert b'id="active-errors"' in response.data
    assert saved.active is True
    repository.commit.assert_not_called()


@pytest.mark.parametrize("path", ["/subscriptions/add", "/subscriptions/1/update"])
def test_duplicate_name_is_rejected_including_cancelled_records(
    authenticated_client: FlaskClient, repository: Repository, path: str
) -> None:
    saved = make_subscription()
    duplicate = make_subscription(id=2, service="Nebula", active=False, end_date=date(2026, 3, 2))
    repository.rows.extend([saved, duplicate])
    before = [dict(vars(row)) for row in repository.rows]

    response = authenticated_client.post(path, data=_form_data(service=" nebula ", active="true"))

    assert response.status_code == 422
    assert b"A subscription with this service already exists." in response.data
    assert [vars(row) for row in repository.rows] == before
    repository.commit.assert_not_called()


def test_cancel_uses_submitted_schedule(app: Flask, authenticated_client: FlaskClient, repository: Repository) -> None:
    saved = make_subscription()
    repository.rows.append(saved)
    today = local_today(app.config["TIMEZONE"])

    response = authenticated_client.post(
        "/subscriptions/1/update",
        data=_form_data(active="false", start_date=today.strftime("%d.%m.%Y"), billing_date_offset="5"),
    )

    assert response.status_code == 302
    assert saved.active is False
    assert saved.start_date == today
    assert saved.billing_date_offset == 5
    assert saved.end_date == today + relativedelta(months=1) + timedelta(days=5)
    repository.commit.assert_called_once_with()


def test_reactivate_clears_expiration(authenticated_client: FlaskClient, repository: Repository) -> None:
    saved = make_subscription(active=False, end_date=date(2026, 3, 2))
    repository.rows.append(saved)

    response = authenticated_client.post("/subscriptions/1/update", data=_form_data(active="true"))

    assert response.status_code == 302
    assert saved.active is True
    assert saved.end_date is None
    repository.commit.assert_called_once_with()


def test_legacy_expiration_is_repaired_once_on_valid_save(
    authenticated_client: FlaskClient, repository: Repository
) -> None:
    saved = make_subscription(
        start_date=date(2026, 1, 15), billing_date_offset=-5, active=False, end_date=date(2026, 9, 15)
    )
    repository.rows.append(saved)
    data = _form_data(start_date="15.01.2026", billing_date_offset="-5", active="false", cost="17.45")
    committed: list[tuple[date | None, Decimal]] = []
    repository.commit.side_effect = lambda: committed.append((saved.end_date, saved.cost))

    assert _editor_payload(authenticated_client.get("/subscriptions/1"))["1"]["endDate"] == "15.09.2026"
    assert authenticated_client.post("/subscriptions/1/update", data=data | {"cost": "sNaN"}).status_code == 422
    assert saved.end_date == date(2026, 9, 15)
    assert saved.cost == Decimal("12.90")
    repository.commit.assert_not_called()

    assert authenticated_client.post("/subscriptions/1/update", data=data).status_code == 302
    assert committed == [(date(2026, 9, 10), Decimal("17.45"))]
    assert authenticated_client.post("/subscriptions/1/update", data=data | {"cost": "18.90"}).status_code == 302
    assert committed == [(date(2026, 9, 10), Decimal("17.45")), (date(2026, 9, 10), Decimal("18.90"))]
    assert _editor_payload(authenticated_client.get("/subscriptions/1"))["1"]["endDate"] == "10.09.2026"


def test_invalid_recorded_cycle_rejects_edit_before_mutating(
    authenticated_client: FlaskClient, repository: Repository
) -> None:
    offset = -5
    expiration = date(2026, 9, 14)
    saved = make_subscription(
        start_date=date(2026, 1, 15), billing_date_offset=offset, active=False, end_date=expiration
    )
    repository.rows.append(saved)
    before = dict(vars(saved))

    response = authenticated_client.post(
        "/subscriptions/1/update", data=_form_data(service="Changed", active="false", cost="20.00")
    )

    assert response.status_code == 422
    assert b"Recorded expiration does not match the billing schedule." in response.data
    assert vars(saved) == before
    repository.commit.assert_not_called()


def test_delete_is_post_only_and_removes_record(authenticated_client: FlaskClient, repository: Repository) -> None:
    saved = make_subscription()
    repository.rows.append(saved)

    assert authenticated_client.get("/subscriptions/1/remove").status_code == 404
    assert authenticated_client.delete("/subscriptions/1/remove").status_code == 405
    assert repository.rows == [saved]
    response = authenticated_client.post("/subscriptions/1/remove", follow_redirects=True)

    assert [item.status_code for item in response.history] == [302]
    assert response.status_code == 200
    assert b"Netflix was permanently deleted." in response.data
    assert repository.rows == []
    repository.commit.assert_called_once_with()


def test_missing_record_redirects_with_error(authenticated_client: FlaskClient, repository: Repository) -> None:
    response = authenticated_client.get("/subscriptions/404", follow_redirects=True)

    assert [item.status_code for item in response.history] == [302]
    assert response.status_code == 200
    assert b"That subscription could not be found." in response.data
    repository.commit.assert_not_called()


class _UniqueViolation(Exception):
    diag = SimpleNamespace(constraint_name="subscriptions_service_key")


@pytest.mark.parametrize(
    ("path", "cause", "message"),
    [
        ("/subscriptions/add", _UniqueViolation(), b"A subscription with this service already exists."),
        ("/subscriptions/1/update", Exception("check"), b"violates a database constraint"),
    ],
)
def test_failed_commit_rolls_back_and_returns_useful_error(
    authenticated_client: FlaskClient, repository: Repository, path: str, cause: Exception, message: bytes
) -> None:
    repository.rows.append(make_subscription())
    repository.commit.side_effect = IntegrityError("WRITE", {}, cause)

    response = authenticated_client.post(path, data=_form_data(service="Changed", active="true"))

    assert response.status_code == 422
    assert message in response.data
    repository.commit.assert_called_once_with()
    repository.rollback.assert_called_once_with()


def test_dashboard_displayed_amounts_and_browser_payloads_agree(
    authenticated_client: FlaskClient, repository: Repository
) -> None:
    repository.rows.extend(
        make_subscription(id=index, service=f"Annual {index}", billing_period=BillingPeriod.YEAR, cost=Decimal("19.99"))
        for index in range(1, 7)
    )
    # This individual amount is exactly on a half-cent boundary too.
    repository.rows.append(
        make_subscription(
            id=7,
            service="Half cent",
            category=Category.PROFESSIONAL,
            billing_period=BillingPeriod.YEAR,
            cost=Decimal("0.06"),
        )
    )

    html = authenticated_client.get("/").get_data(as_text=True)
    chart_match = re.search(r'<script id="category-chart-data" type="application/json">(.*?)</script>', html)
    assert chart_match is not None
    categories = {item["category"]: item for item in json.loads(chart_match[1])}
    category = categories["Entertainment"]

    assert category["monthlyCost"] == "9.995"
    assert 'data-monthly-cost-label="10.00€"' in html
    assert 'data-yearly-cost-label="119.94€"' in html
    (half_cent,) = categories["Professional"]["subscriptions"]
    assert half_cent["monthlyCost"] == "0.005"
    assert half_cent["monthlyCostLabel"] == "0.01€"
    assert half_cent["yearlyCostLabel"] == "0.06€"
