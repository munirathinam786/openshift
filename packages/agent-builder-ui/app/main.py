from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Agent Builder UI", version="1.0.0")
templates = Jinja2Templates(directory="/app/app/templates")


def ui_config() -> dict[str, str]:
    return {
        "apiBaseUrl": os.getenv("VITE_API_BASE_URL", "http://localhost:8000"),
        "appName": os.getenv("VITE_APP_NAME", "Kyndryl Agent Builder"),
        "oidcAuthority": os.getenv("VITE_OIDC_AUTHORITY", ""),
        "oidcClientId": os.getenv("VITE_OIDC_CLIENT_ID", ""),
        "oidcRedirectUri": os.getenv("VITE_OIDC_REDIRECT_URI", ""),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"config": ui_config(), "timestamp": datetime.now(UTC).isoformat()},
    )


@app.get("/config")
def config() -> JSONResponse:
    return JSONResponse(ui_config())
