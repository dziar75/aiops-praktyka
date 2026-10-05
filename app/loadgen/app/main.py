"""Synthetic canteen traffic generator.

Sends a realistic mix of requests to orders-api following a daily curve.
"""

import asyncio
import logging
import os
import random
import signal
import time
from collections import deque
from datetime import datetime, timezone

import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from app.curve import target_rps
from app.flags import FlagStore
from app.logging_setup import APP_VARIANT, APP_VERSION, setup_logging

setup_logging()
log = logging.getLogger("loadgen")

BASE_URL = os.getenv("BASE_URL", "http://orders-api:8000").rstrip("/")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9100"))
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "10"))
MAX_IN_FLIGHT = int(os.getenv("MAX_IN_FLIGHT", "200"))
RETARGET_INTERVAL_S = 10

SEARCH_QUERIES = [
    "pierogi", "zupa", "schabowy", "rosół", "żurek", "sałatka", "makaron",
    "kurczak", "naleśniki", "bigos", "gołąbki", "kotlet", "ryba", "wege", "deser",
]

REQUESTS = Counter("loadgen_requests_total", "Requests sent by the load generator", ["endpoint", "status"])
DURATION = Histogram(
    "loadgen_request_duration_seconds", "Request latency observed by the load generator", ["endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
TARGET_RPS = Gauge("loadgen_target_rps", "Current target request rate")
IN_FLIGHT = Gauge("loadgen_in_flight_requests", "Requests currently in flight")
DROPPED = Counter("loadgen_dropped_total", "Requests skipped because too many were in flight")

recent_orders: deque[int] = deque(maxlen=200)
_last_error_log = 0.0


def _pick_request() -> tuple[str, str, str, dict | None]:
    """Returns (endpoint label, method, path, json body)."""
    r = random.random()
    if r < 0.60:
        return "menu", "GET", "/api/menu", None
    if r < 0.70:
        return "menu_search", "GET", f"/api/menu/search?q={random.choice(SEARCH_QUERIES)}", None
    if r < 0.95:
        items = [
            {"menu_item_id": random.randint(1, 20), "qty": random.randint(1, 3)}
            for _ in range(random.choices([1, 2, 3], weights=[6, 3, 1])[0])
        ]
        return "orders_create", "POST", "/api/orders", {"employee_id": f"e-{random.randint(1, 500)}", "items": items}
    order_id = random.choice(recent_orders) if recent_orders else 1
    return "orders_get", "GET", f"/api/orders/{order_id}", None


def _remember_order(resp: httpx.Response) -> None:
    try:
        data = resp.json()
    except ValueError:
        return
    if isinstance(data, dict):
        oid = data.get("order_id", data.get("id"))
        if isinstance(oid, int):
            recent_orders.append(oid)


async def fire(client: httpx.AsyncClient, sem: asyncio.Semaphore) -> None:
    global _last_error_log
    endpoint, method, path, body = _pick_request()
    start = time.perf_counter()
    IN_FLIGHT.inc()
    try:
        resp = await client.request(method, path, json=body)
        status = str(resp.status_code)
        if endpoint == "orders_create" and resp.status_code in (200, 201, 202):
            _remember_order(resp)
        if resp.status_code >= 500:
            log.warning("server error", extra={"endpoint": endpoint, "path": path, "status": resp.status_code})
    except httpx.HTTPError as exc:
        status = "timeout" if isinstance(exc, httpx.TimeoutException) else "error"
        now = time.monotonic()
        if now - _last_error_log > 5:
            _last_error_log = now
            log.warning("request failed", extra={"endpoint": endpoint, "path": path,
                                                 "error": f"{type(exc).__name__}: {exc}"})
    finally:
        IN_FLIGHT.dec()
        sem.release()
    REQUESTS.labels(endpoint=endpoint, status=status).inc()
    DURATION.labels(endpoint=endpoint).observe(time.perf_counter() - start)


async def run(stop: asyncio.Event, flags: FlagStore) -> None:
    sem = asyncio.Semaphore(MAX_IN_FLIGHT)
    tasks: set[asyncio.Task] = set()
    limits = httpx.Limits(max_connections=MAX_IN_FLIGHT, max_keepalive_connections=50)
    headers = {"User-Agent": f"kantyna-loadgen/{APP_VERSION}"}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=REQUEST_TIMEOUT_S, limits=limits,
                                 headers=headers) as client:
        def compute() -> float:
            f = flags.get()
            return target_rps(datetime.now(timezone.utc), f.peak_rps, f.multiplier)

        rps = compute()
        next_retarget = time.monotonic() + RETARGET_INTERVAL_S
        TARGET_RPS.set(rps)
        log.info("target rate", extra={"target_rps": round(rps, 2)})

        while not stop.is_set():
            now = time.monotonic()
            if now >= next_retarget:
                rps = compute()
                TARGET_RPS.set(rps)
                next_retarget = now + RETARGET_INTERVAL_S
                log.debug("target rate", extra={"target_rps": round(rps, 2)})

            if sem.locked():
                DROPPED.inc()
            else:
                await sem.acquire()
                task = asyncio.create_task(fire(client, sem))
                tasks.add(task)
                task.add_done_callback(tasks.discard)

            # Poisson arrivals
            try:
                await asyncio.wait_for(stop.wait(), timeout=random.expovariate(rps))
            except asyncio.TimeoutError:
                pass

        if tasks:
            await asyncio.wait(tasks, timeout=REQUEST_TIMEOUT_S)


def main() -> None:
    start_http_server(METRICS_PORT)
    flags = FlagStore()
    log.info("loadgen starting", extra={
        "base_url": BASE_URL, "peak_rps": flags.get().peak_rps, "multiplier": flags.get().multiplier,
        "variant": APP_VARIANT, "metrics_port": METRICS_PORT,
    })

    async def _amain() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await run(stop, flags)

    asyncio.run(_amain())
    log.info("loadgen stopped")


if __name__ == "__main__":
    main()
