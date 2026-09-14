from dataclasses import dataclass

from flask import Flask, url_for

_ENTRYPOINT = "assets/js/main.js"
_STYLESHEET = "assets/app.css"
_VITE_DEVELOPMENT_ORIGIN = "http://localhost:5173"


@dataclass(frozen=True)
class FrontendAssets:
    scripts: tuple[str, ...]
    stylesheets: tuple[str, ...]


def get_frontend_assets(app: Flask) -> FrontendAssets:
    environment = app.config["APP_ENV"]
    if environment == "development":
        return FrontendAssets(
            scripts=(
                f"{_VITE_DEVELOPMENT_ORIGIN}/@vite/client",
                f"{_VITE_DEVELOPMENT_ORIGIN}/{_ENTRYPOINT}",
            ),
            stylesheets=(f"{_VITE_DEVELOPMENT_ORIGIN}/{_STYLESHEET}",),
        )

    if environment == "test":
        return FrontendAssets(scripts=(), stylesheets=())

    return FrontendAssets(
        scripts=(url_for("static", filename="assets/main.js"),),
        stylesheets=(url_for("static", filename="assets/main.css"),),
    )
