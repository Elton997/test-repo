# app/main.py
from contextlib import asynccontextmanager
import asyncio
import importlib
import json
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from app.core.config import load_environment, get_env_load_state, settings
from app.core.middleware import LoggingMiddleware


class PrettyJSONResponse(JSONResponse):
    """Custom JSONResponse that pretty-prints JSON with indentation."""
    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        ).encode("utf-8")

load_environment()  # load .env.dev or .env.prod based on APP_ENV

CRITICAL_ROUTER_MODULES = (
    "app.dcim.routers.login_router",
    "app.dcim.routers.listing_router",
    "app.dcim.routers.export_router",
    "app.dcim.routers.details_router",
    "app.dcim.routers.summary_router",
    "app.dcim.routers.search_router",
)

DEFERRED_ROUTER_MODULES = (
    "app.dcim.routers.add_router",
    "app.dcim.routers.update_router",
    "app.dcim.routers.delete_router",
    "app.dcim.routers.change_log_router",
    "app.dcim.routers.bulk_upload_router",
)

ALL_ROUTER_MODULES = CRITICAL_ROUTER_MODULES + DEFERRED_ROUTER_MODULES


def _import_router(module_path: str):
    """
    Import a router module and return its `router` attribute.
    Kept sync so it can be executed inside a thread without touching the loop.
    """
    module = importlib.import_module(module_path)
    router = getattr(module, "router", None)
    if router is None:
        raise AttributeError(f"Module {module_path} does not expose a FastAPI router named 'router'")
    return router


def _load_router_with_profile(module_path: str):
    """Synchronous helper executed in a thread so we can capture timing info."""
    start = perf_counter()
    router = _import_router(module_path)
    duration_ms = (perf_counter() - start) * 1000
    return module_path, router, duration_ms


async def _load_routers(app: FastAPI, module_paths, app_logger, *, label: str):
    """Load routers concurrently while still logging individual durations."""
    # app_logger.info(
    #     "Loading routers",
    #     extra={"batch": label, "count": len(module_paths)},
    # )

    tasks = [
        asyncio.to_thread(_load_router_with_profile, module_path)
        for module_path in module_paths
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            raise result

        module_path, router, load_ms = result
        app.include_router(router)
        # app_logger.info(
        #     "Router loaded",
        #     extra={
        #         "router_module": module_path,
        #         "load_ms": round(load_ms, 2),
        #         "batch": label,
        #     },
        # )


async def _prewarm_database(app_logger):
    """Ping the database in a worker thread; log but do not block startup."""
    from app.db.session import get_engine

    engine = get_engine()

    def _ping():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM DUAL"))

    try:
        await asyncio.to_thread(_ping)
        # app_logger.debug("Database prewarm finished")
    except Exception as exc:
        app_logger.warning("Database prewarm failed", extra={"error": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Routers are loaded here (after uvicorn says "running") instead of at import time.
    Database connection is pre-warmed so first request is fast.
    """
    from app.core.logger import app_logger

    env_state = get_env_load_state()
    # if env_state["env_file"]:
    #     app_logger.info(
    #         "Environment file loaded",
    #         extra={"env_file": env_state["env_file"]},
    #     )
    if env_state["warning"]:
        app_logger.warning(
            "Environment file missing",
            extra={"warning": env_state["warning"]},
        )

    startup_start = perf_counter()
    db_task = asyncio.create_task(_prewarm_database(app_logger))
    deferred_task = asyncio.create_task(
        _load_routers(app, DEFERRED_ROUTER_MODULES, app_logger, label="deferred")
    )

    await _load_routers(app, CRITICAL_ROUTER_MODULES, app_logger, label="critical")

    startup_duration_ms = (perf_counter() - startup_start) * 1000
    app_logger.info(
        "DCIM FastAPI application started",
        extra={
            "version": "1.0.0",
            "startup_ms": round(startup_duration_ms, 2),
            "routers_loaded": len(CRITICAL_ROUTER_MODULES),
            "routers_deferred": len(DEFERRED_ROUTER_MODULES),
            "db_prewarm_blocking": False,
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
        },
    )

    yield  # App is running

    # Ensure the DB warm-up task finished and log shutdown
    await asyncio.gather(db_task, deferred_task)
    app_logger.info("DCIM FastAPI application shutting down")


app = FastAPI(
    title="DCIM FastAPI Backend",
    description="Data Center Infrastructure Management (DCIM) API for managing sites, locations, racks, and devices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    default_response_class=PrettyJSONResponse,
    swagger_ui_parameters={"persistAuthorization": True},
)


def custom_openapi():
    """
    Add global Bearer auth header to Swagger / OpenAPI so the token
    can be provided once via the Authorize button and reused.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})

    # HTTP Bearer auth using Authorization: Bearer <JWT_ACCESS_TOKEN>
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Use the access token as: `Bearer <JWT_ACCESS_TOKEN>`",
    }

    # Apply BearerAuth globally (all endpoints will show the lock icon)
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add CORS middleware to handle OPTIONS preflight requests
# This must be added before other middleware
# Parse CORS origins from config (comma-separated list or "*" for all)
cors_origins = settings.CORS_ORIGINS
if cors_origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods including OPTIONS
    allow_headers=["*"],  # Allows all headers
)

app.add_middleware(LoggingMiddleware)

@app.get("/")
def read_root():
    return {
        "message": "DCIM FastAPI is running 🚀",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    """
    Lightweight health probe invoked by uptime monitors/Postman.
    Performs a quick DB ping and surfaces runtime metadata.
    """
    from app.db.session import get_engine

    db_status = "unknown"
    overall_status = "degraded"

    try:
        engine = get_engine()

        def _ping():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))

        await asyncio.to_thread(_ping)
        db_status = "up"
        overall_status = "ok"
    except Exception as exc:
        db_status = f"down ({type(exc).__name__})"

    return {
        "status": overall_status,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }
