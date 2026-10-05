"""Runtime configuration flags.

Values come from environment variables and may be overridden by an optional
JSON file (FLAGS_FILE) that is reloaded periodically, so settings can be tuned
without restarting the process.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass

log = logging.getLogger("flags")

FLAGS_FILE = os.getenv("FLAGS_FILE", "/etc/kantyna/flags/flags.json")
RELOAD_INTERVAL_S = 15
SECTION = "worker"


@dataclass(frozen=True)
class WorkerFlags:
    processing_delay_ms: int = 0
    fail_rate: float = 0.0


def _from_env() -> dict:
    return {
        "processing_delay_ms": os.getenv("PROCESSING_DELAY_MS", "0"),
        "fail_rate": os.getenv("FAIL_RATE", "0"),
    }


def _from_file() -> dict:
    try:
        with open(FLAGS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("could not read flags file", extra={"path": FLAGS_FILE, "error": str(exc)})
        return {}
    section = data.get(SECTION) if isinstance(data, dict) else None
    return section if isinstance(section, dict) else {}


def _build(raw: dict) -> WorkerFlags:
    try:
        delay = max(0, int(float(raw.get("processing_delay_ms", 0))))
    except (TypeError, ValueError):
        delay = 0
    try:
        rate = min(1.0, max(0.0, float(raw.get("fail_rate", 0.0))))
    except (TypeError, ValueError):
        rate = 0.0
    return WorkerFlags(processing_delay_ms=delay, fail_rate=rate)


class FlagStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flags = WorkerFlags()
        self.reload()

    def get(self) -> WorkerFlags:
        with self._lock:
            return self._flags

    def reload(self) -> None:
        raw = _from_env()
        raw.update({k: v for k, v in _from_file().items() if k in ("processing_delay_ms", "fail_rate")})
        new = _build(raw)
        with self._lock:
            old, self._flags = self._flags, new
        if new != old:
            log.info("flags updated", extra={"flags": new.__dict__})

    def start(self, stop: threading.Event) -> threading.Thread:
        def loop() -> None:
            while not stop.wait(RELOAD_INTERVAL_S):
                try:
                    self.reload()
                except Exception:  # noqa: BLE001
                    log.exception("flags reload failed")

        t = threading.Thread(target=loop, name="flags-reloader", daemon=True)
        t.start()
        return t
