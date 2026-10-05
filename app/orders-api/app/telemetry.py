"""OpenTelemetry setup. OTLP export is enabled only when an endpoint is set."""
from __future__ import annotations

import logging

from .config import settings

log = logging.getLogger("orders-api.telemetry")


def setup_tracing(app) -> None:
    """Instrument FastAPI, httpx and psycopg. Export OTLP only if configured."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except Exception as exc:  # pragma: no cover - otel optional
        log.warning("OpenTelemetry not available, tracing disabled", extra={"error": str(exc)})
        return

    resource = Resource.create({"service.name": settings.service_name, "service.version": settings.version})
    provider = TracerProvider(resource=resource)

    if settings.otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            log.info("OTLP trace export enabled", extra={"endpoint": settings.otlp_endpoint})
        except Exception as exc:  # pragma: no cover
            log.warning("Failed to enable OTLP export", extra={"error": str(exc)})

    trace.set_tracer_provider(provider)

    try:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,readyz,metrics")
        HTTPXClientInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover
        log.warning("HTTP instrumentation failed", extra={"error": str(exc)})

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(enable_commenter=False)
    except Exception as exc:  # pragma: no cover
        log.warning("psycopg instrumentation failed", extra={"error": str(exc)})
