"""Prometheus metrics."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from .config import settings

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "route", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

orders_created_total = Counter(
    "orders_created_total",
    "Number of orders successfully created.",
)

order_value_pln_total = Counter(
    "order_value_pln_total",
    "Cumulative value of created orders in PLN.",
)

payments_failed_total = Counter(
    "payments_failed_total",
    "Number of failed payment attempts.",
    ["reason"],
)

db_pool_connections_in_use = Gauge(
    "db_pool_connections_in_use",
    "Connections currently checked out of the pool.",
)

db_pool_size = Gauge(
    "db_pool_size",
    "Current size of the connection pool.",
)

build_info = Gauge(
    "kantyna_build_info",
    "Build information.",
    ["version", "variant"],
)


def init_build_info() -> None:
    build_info.labels(version=settings.version, variant=settings.variant).set(1)
