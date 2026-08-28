from flask import Blueprint, Response, abort, current_app

from subs.services.calendar import get_calendar_ics

bp = Blueprint("calendar", __name__)


@bp.get("/calendar/<token>.ics")
def ical(token: str) -> Response:
    if token != current_app.config["CALENDAR_FEED_TOKEN"]:
        abort(404)

    return Response(
        get_calendar_ics(),
        content_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=subscription.ics"},
    )
