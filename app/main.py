import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import (
    cv_events,
    cv_stream,
    dashboard,
    emergency_drill,
    environmental,
    incidents,
    reports,
    workers,
    ws,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIST = os.path.join(PROJECT_ROOT, "admin", "dist")
DASHBOARD_DIST = os.path.join(PROJECT_ROOT, "dashboard", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MineGuard",
    version="0.1.0",
    description="AI-based mine safety monitoring system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    workers.router,
    incidents.router,
    environmental.router,
    cv_events.router,
    dashboard.router,
    emergency_drill.router,
    reports.router,
    cv_stream.router,
):
    app.include_router(router)
app.include_router(ws.router)


if os.path.isdir(ADMIN_DIST):
    app.mount("/admin-simulator", StaticFiles(directory=ADMIN_DIST, html=True), name="admin")
else:
    @app.get("/admin-simulator", include_in_schema=False)
    def admin_not_built():
        return {
            "message": "Admin simulator frontend is not built. "
            "Run `cd admin && npm install && npm run build` first."
        }


if os.path.isdir(DASHBOARD_DIST):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIST, html=True), name="dashboard")
else:
    @app.get("/dashboard", include_in_schema=False)
    def dashboard_not_built():
        return {
            "message": "Operator dashboard frontend is not built. "
            "Run `cd dashboard && npm install && npm run build` first."
        }


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}