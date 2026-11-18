"""The HTTP side of the thin host: one FastAPI app with every loaded plugin's routers mounted.

No sign-in in Phase 1: the host is for one operator on their own machine, bound to 127.0.0.1.
"""
from __future__ import annotations

from fastapi import FastAPI

from .loader import LoadReport


def create_app(report: LoadReport) -> FastAPI:
    app = FastAPI(title="Second Brain thin host", docs_url=None, redoc_url=None)

    @app.get("/host/plugins")
    def plugins() -> dict:
        return {"loaded": report.loaded, "refused": report.refused}

    for _plugin_id, router in report.routers:
        app.include_router(router)
    return app
