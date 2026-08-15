"""FastAPI application entrypoint.

Run: uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, crawl, dashboard, keywords, search_engines, tasks, websites, workspaces
from .core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Universal AI SEO Platform - multi search-engine SEO intelligence",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    workspaces.router,
    websites.router,
    crawl.router,
    keywords.router,
    tasks.router,
    search_engines.router,
    dashboard.router,
):
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.get("/", tags=["system"])
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}
