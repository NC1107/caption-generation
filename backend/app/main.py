"""App entrypoint: FastAPI + job manager lifespan, JSON API, and the SPA."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, db
from app.api.routes import router as api_router
from app.config import get_settings
from app.jobs import JobManager


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    settings.ensure_dirs()
    db.init_db(settings.db_path)

    manager = JobManager(settings)
    await manager.start()

    app.state.settings = settings
    app.state.manager = manager
    logging.getLogger("caption").info("Caption Generation %s ready", __version__)
    try:
        yield
    finally:
        await manager.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Caption Generation", version=__version__, lifespan=lifespan)

    settings = get_settings()
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router)
    _mount_frontend(app, settings)
    return app


def _mount_frontend(app: FastAPI, settings) -> None:
    static_path = settings.static_path
    if static_path is None:
        @app.get("/")
        def _no_ui() -> JSONResponse:
            return JSONResponse(
                {
                    "name": "Caption Generation",
                    "version": __version__,
                    "note": "API is running. Build the frontend or run Vite in dev.",
                    "api": "/api",
                }
            )
        return

    index = static_path / "index.html"
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/")
    def _index() -> FileResponse:
        return FileResponse(index)

    # Client-side routing: unknown paths fall back to index.html.
    @app.get("/{full_path:path}")
    def _spa(full_path: str) -> FileResponse:
        candidate = static_path / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
