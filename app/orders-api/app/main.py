"""Kantyna orders-api — FastAPI application."""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import db, metrics, runtime
from .config import settings
from .flags import flags
from .logging_setup import configure_logging
from .models import OrderIn, VersionOut
from .payments import PaymentError, charge
from .queue import publish_order
from .telemetry import setup_tracing

log = logging.getLogger("orders-api")

_SKIP_METRICS_PATHS = {"/metrics", "/healthz", "/readyz"}


async def _pool_gauge_loop() -> None:
    while True:
        try:
            db.update_pool_gauges()
        except Exception:  # pragma: no cover
            log.debug("pool gauge update failed", exc_info=True)
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    metrics.init_build_info()
    flags.start()
    runtime.start_memory_pressure()
    log.info(
        "Starting orders-api",
        extra={"version": settings.version, "variant": settings.variant},
    )

    gauge_task = None
    if not settings.skip_db_init:
        await db.open_pool()
        await db.init_schema_and_seed()
        gauge_task = asyncio.create_task(_pool_gauge_loop())

    try:
        yield
    finally:
        if gauge_task is not None:
            gauge_task.cancel()
        runtime.stop_memory_pressure()
        flags.stop()
        if not settings.skip_db_init:
            await db.close_pool()


app = FastAPI(title="Kantyna orders-api", version=settings.version, lifespan=lifespan)
setup_tracing(app)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    path = request.url.path
    start = time.perf_counter()

    if path not in _SKIP_METRICS_PATHS:
        runtime.cpu_burn_if_enabled()
        runtime.emit_feedback_log()

    status_code = 500
    try:
        if path.startswith("/api/") and runtime.should_fail_request():
            try:
                runtime.raise_synthetic_error()
            except runtime.UpstreamUnavailableError:
                log.error(
                    "Unhandled error while processing request",
                    extra={"route": path},
                    exc_info=True,
                )
            status_code = 500
            response: Response = JSONResponse(
                status_code=500, content={"detail": "internal server error"}
            )
        else:
            response = await call_next(request)
            status_code = response.status_code
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        route_label = getattr(route, "path", None) or ("unmatched" if route is None else path)
        metrics.http_requests_total.labels(
            method=request.method, route=route_label, status=str(status_code)
        ).inc()
        metrics.http_request_duration_seconds.labels(
            method=request.method, route=route_label
        ).observe(duration)

    return response


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    try:
        await db.ping()
    except Exception as exc:
        log.warning("Readiness check failed", extra={"error": str(exc)})
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.get("/version", response_model=VersionOut)
async def version():
    return VersionOut(service=settings.service_name, version=settings.version, variant=settings.variant)


@app.get("/metrics")
async def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _menu_item(row: dict) -> dict:
    price = float(row["price_pln"])
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price_pln": price,
        "price": price,
    }


@app.get("/api/menu")
async def get_menu():
    if flags.get("db_pool_leak"):
        import random

        if random.random() < 0.3:
            await db.leak_one_connection()
    items = await db.fetch_menu(slow=runtime.menu_uses_n_plus_one())
    return {"items": [_menu_item(r) for r in items]}


@app.get("/api/menu/search")
async def search_menu(q: str = Query(..., min_length=1, max_length=100)):
    items = await db.search_menu(q)
    return {"items": [_menu_item(r) for r in items], "query": q}


@app.post("/api/orders", status_code=201)
async def create_order(order_in: OrderIn):
    try:
        order = await db.create_order(
            employee_id=order_in.employee_id,
            items=[item.model_dump() for item in order_in.items],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        payment = await charge(order_ref=str(order["id"]), amount=order["total_pln"])
    except PaymentError as exc:
        metrics.payments_failed_total.labels(reason=exc.reason).inc()
        log.warning(
            "Payment failed for order",
            extra={"order_id": order["id"], "reason": exc.reason},
        )
        raise HTTPException(status_code=402, detail=f"payment failed: {exc.reason}")

    runtime.maybe_receipt_variant_error(order["id"])
    publish_order(order)

    metrics.orders_created_total.inc()
    metrics.order_value_pln_total.inc(order["total_pln"])
    log.info(
        "Order created",
        extra={
            "order_id": order["id"],
            "employee_id": order["employee_id"],
            "status": "created",
        },
    )

    order["transaction_id"] = payment.get("transaction_id")
    order["order_id"] = order["id"]
    order["total"] = order["total_pln"]
    return order


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    order = await db.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order
