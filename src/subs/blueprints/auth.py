from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    session,
    url_for,
)
from werkzeug import Response
from werkzeug.security import check_password_hash

from subs.forms.auth import LoginForm

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login() -> Response | str:
    if session.get("authenticated"):
        return redirect(url_for("subscriptions.index"))

    form = LoginForm()

    if form.validate_on_submit():
        if check_password_hash(
            current_app.config["APP_PASSPHRASE_HASH"], form.passphrase.data
        ):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("subscriptions.index"))

        flash("Incorrect passphrase", "error")

    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout() -> Response:
    session.clear()
    return redirect(url_for("auth.login"))
