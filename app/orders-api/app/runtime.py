"""Behaviour driven by runtime flags and the active build variant.

These hooks make the service's behaviour configurable for resilience and
load testing (synthetic error injection, latency, resource pressure).
"""
from __future__ import annotations

import logging
import random
import threading
import time

from .config import settings
from .flags import flags

log = logging.getLogger("orders-api.runtime")


class UpstreamUnavailableError(RuntimeError):
    """Raised to simulate a transient downstream failure."""


class ReceiptTemplateError(RuntimeError):
    """Raised when a receipt cannot be rendered from the order."""


# ---------------------------------------------------------------------------
# Request-time hooks
# ---------------------------------------------------------------------------

def should_fail_request() -> bool:
    rate = float(flags.get("error_rate") or 0.0)
    return rate > 0 and random.random() < rate


def raise_synthetic_error() -> None:
    raise UpstreamUnavailableError(
        "order pipeline dependency returned an unexpected response"
    )


def cpu_burn_if_enabled() -> None:
    if not flags.get("cpu_burn"):
        return
    deadline = time.monotonic() + 0.08
    x = 0.0
    while time.monotonic() < deadline:
        x += random.random() ** 0.5
    _ = x


def menu_uses_n_plus_one() -> bool:
    return bool(flags.get("slow_menu_query")) or settings.variant == "menu-v2"


def emit_feedback_log() -> None:
    if not flags.get("log_noise"):
        return
    feedback = flags.get("feedback_text") or ""
    log.info("customer feedback received: %s", feedback, extra={"feedback": feedback})


def maybe_receipt_variant_error(order_id: int) -> None:
    """receipt-v2 occasionally fails to render a receipt but still accepts the order."""
    if settings.variant != "receipt-v2":
        return
    if random.random() < 0.07:
        try:
            raise ReceiptTemplateError("missing field 'nip'")
        except ReceiptTemplateError:
            log.error(
                "Failed to render receipt template",
                extra={"order_id": order_id},
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Background memory pressure
# ---------------------------------------------------------------------------

_cache: list[bytearray] = []
_mem_thread: threading.Thread | None = None
_mem_stop = threading.Event()


def start_memory_pressure() -> None:
    global _mem_thread
    if _mem_thread is not None:
        return

    def _loop() -> None:
        # Grow roughly `memory_leak_mb_per_min` MB each minute, in 5s steps.
        step_seconds = 5
        while not _mem_stop.wait(step_seconds):
            mb_per_min = float(flags.get("memory_leak_mb_per_min") or 0.0)
            if mb_per_min <= 0:
                continue
            bytes_this_step = int(mb_per_min * 1024 * 1024 * step_seconds / 60)
            if bytes_this_step > 0:
                _cache.append(bytearray(bytes_this_step))

    _mem_thread = threading.Thread(target=_loop, name="mem-pressure", daemon=True)
    _mem_thread.start()


def stop_memory_pressure() -> None:
    _mem_stop.set()
