import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

    manifest_path = Path(app.static_folder or "") / "manifest.json"
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text())
        entry = manifest[_ENTRYPOINT]
        script = url_for("static", filename=entry["file"])
        stylesheets = tuple(url_for("static", filename=path) for path in entry.get("css", ()))
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Vite production assets are missing or invalid") from error

    return FrontendAssets(scripts=(script,), stylesheets=stylesheets)
