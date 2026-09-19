from typing import Any, cast

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug import Response

from subs.formatting import format_eur
from subs.forms.action import ActionForm
from subs.forms.editor import CANCELLED_PROTECTED_FIELDS, EditorSubscriptionPayload, editor_values
from subs.forms.subscription import SubscriptionForm, UpdateSubscriptionForm
from subs.models.subscription import Subscription
from subs.repositories import subscription as subscription_repository
from subs.services.dashboard import DashboardData, build_dashboard_data
from subs.services.subscription import (
    DuplicateSubscriptionError,
    SubscriptionNotFoundError,
    SubscriptionValidationError,
    create_subscription,
    delete_subscription,
    local_today,
    update_subscription,
)

bp = Blueprint("subscriptions", __name__)


@bp.get("/")
def index() -> str:
    return _render_dashboard()


@bp.post("/subscriptions/add")
def add_subscription() -> Response | tuple[str, int]:
    form = SubscriptionForm()
    if form.validate_on_submit():
        try:
            created = create_subscription(**form.service_values())
        except DuplicateSubscriptionError:
            _append_field_error(form, "service", "A subscription with this service already exists.")
            flash("That service is already in your subscriptions.", "error")
        except SubscriptionValidationError as error:
            _apply_service_errors(form, error)
            flash("The subscription could not be created.", "error")
        else:
            flash(f"{created.service} was added.", "success")
            return redirect(url_for("subscriptions.index"))

    return _render_dashboard(form=form, editor_mode="add"), 422


@bp.get("/subscriptions/<int:subscription_id>")
def get_subscription(subscription_id: int) -> Response | str:
    subscription = subscription_repository.get_subscription_by_id(subscription_id)
    if subscription is None:
        flash("That subscription could not be found.", "error")
        return redirect(url_for("subscriptions.index"))

    return _render_dashboard(
        form=UpdateSubscriptionForm(formdata=None, obj=subscription),
        editor_mode="edit",
        editor_subscription=subscription,
    )


@bp.post("/subscriptions/<int:subscription_id>/update")
def update_subscription_route(subscription_id: int) -> Response | tuple[str, int]:
    subscription = subscription_repository.get_subscription_by_id(subscription_id)
    if subscription is None:
        flash("That subscription could not be found.", "error")
        return redirect(url_for("subscriptions.index"))

    formdata = request.form.copy()
    if not subscription.active and formdata.get("active") == "false":
        saved_values = editor_values(subscription)
        for name in CANCELLED_PROTECTED_FIELDS:
            formdata[name] = saved_values[name]
    form = UpdateSubscriptionForm(formdata=formdata)
    if form.validate_on_submit():
        try:
            updated = update_subscription(
                subscription_id=subscription_id,
                active=cast(bool, form.active.data),
                **form.service_values(),
            )
        except DuplicateSubscriptionError:
            _append_field_error(form, "service", "A subscription with this service already exists.")
            flash("That service is already in your subscriptions.", "error")
        except SubscriptionNotFoundError:
            flash("That subscription could not be found.", "error")
            return redirect(url_for("subscriptions.index"))
        except SubscriptionValidationError as error:
            _apply_service_errors(form, error)
            flash("The subscription could not be updated.", "error")
        else:
            flash(f"{updated.service} was updated.", "success")
            return redirect(url_for("subscriptions.index"))

    return (
        _render_dashboard(
            form=form,
            editor_mode="edit",
            editor_subscription=subscription,
        ),
        422,
    )


@bp.post("/subscriptions/<int:subscription_id>/remove")
def remove_subscription(subscription_id: int) -> Response:
    try:
        deleted = delete_subscription(subscription_id)
    except SubscriptionNotFoundError:
        flash("That subscription could not be found.", "error")
    else:
        flash(f"{deleted.service} was permanently deleted.", "success")

    return redirect(url_for("subscriptions.index"))


def _render_dashboard(
    *,
    form: SubscriptionForm | UpdateSubscriptionForm | None = None,
    editor_mode: str | None = None,
    editor_subscription: Subscription | None = None,
) -> str:
    subscriptions = subscription_repository.get_all_subscriptions()
    today = local_today(current_app.config["TIMEZONE"])
    dashboard = build_dashboard_data(subscriptions, today)
    if form is None:
        form = SubscriptionForm(formdata=None)

    return render_template(
        "subscriptions/dashboard.html",
        dashboard=dashboard,
        form=form,
        status_form=form if isinstance(form, UpdateSubscriptionForm) else UpdateSubscriptionForm(formdata=None),
        add_defaults=editor_values(),
        editor_mode=editor_mode,
        editor_subscription=editor_subscription,
        subscription_data=_subscription_data(dashboard),
        chart_data=[
            {
                "category": spending.category.value,
                "monthlyCost": str(float(spending.monthly_cost)),
                "yearlyCost": str(float(spending.yearly_cost)),
                "subscriptions": [
                    {
                        "service": subscription.service,
                        "monthlyCost": str(float(subscription.monthly_cost)),
                        "yearlyCost": str(float(subscription.yearly_cost)),
                        "monthlyCostLabel": format_eur(subscription.monthly_cost),
                        "yearlyCostLabel": format_eur(subscription.yearly_cost),
                    }
                    for subscription in spending.subscriptions
                ],
            }
            for spending in dashboard.category_spending
        ],
        calendar_feed_url=url_for(
            "calendar.ical",
            token=current_app.config["CALENDAR_FEED_TOKEN"],
            _external=True,
        ),
        logout_form=ActionForm(prefix="logout"),
        delete_form=ActionForm(prefix="delete"),
        today=today,
    )


def _subscription_data(dashboard: DashboardData) -> dict[str, EditorSubscriptionPayload]:
    return {
        str(row.subscription.id): {
            "id": row.subscription.id,
            "values": editor_values(row.subscription),
            "endDate": (
                row.subscription.end_date.strftime("%d.%m.%Y") if row.subscription.end_date is not None else ""
            ),
            "editorUrl": url_for(
                "subscriptions.get_subscription",
                subscription_id=row.subscription.id,
            ),
            "updateUrl": url_for(
                "subscriptions.update_subscription_route",
                subscription_id=row.subscription.id,
            ),
            "removeUrl": url_for(
                "subscriptions.remove_subscription",
                subscription_id=row.subscription.id,
            ),
        }
        for row in dashboard.rows
    }


def _append_field_error(
    form: SubscriptionForm | UpdateSubscriptionForm,
    field_name: str,
    message: str,
) -> None:
    field: Any = getattr(form, field_name, None)
    if field is None:
        form.form_errors.append(message)
        return
    cast(list[str], field.errors).append(message)


def _apply_service_errors(
    form: SubscriptionForm | UpdateSubscriptionForm,
    error: SubscriptionValidationError,
) -> None:
    for field_name, message in error.errors.items():
        _append_field_error(form, field_name, message)
