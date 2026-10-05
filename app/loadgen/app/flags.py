"""Runtime configuration flags.

Defaults come from environment variables (PEAK_RPS, MULTIPLIER) and may be
overridden by the "loadgen" section of the optional JSON file at FLAGS_FILE,
which is re-read every 15 seconds.
"""

import json
import logging
import os
import time
from dataclasses import dataclass

log = logging.getLogger("flags")

FLAGS_FILE = os.getenv("FLAGS_FILE", "/etc/kantyna/flags/flags.json")
RELOAD_INTERVAL_S = 15
SECTION = "loadgen"


@dataclass(frozen=True)
class LoadgenFlags:
    peak_rps: float
    multiplier: float


def _float(value, default: float) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default


class FlagStore:
    def __init__(self) -> None:
        self._env = LoadgenFlags(
            peak_rps=_float(os.getenv("PEAK_RPS", "18"), 18.0),
            multiplier=_float(os.getenv("MULTIPLIER", "1.0"), 1.0),
        )
        self._flags = self._env
        self._loaded_at = 0.0
        self._reload()

    def _read_file(self) -> dict:
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

    def _reload(self) -> None:
        raw = self._read_file()
        new = LoadgenFlags(
            peak_rps=_float(raw.get("peak_rps", self._env.peak_rps), self._env.peak_rps),
            multiplier=_float(raw.get("multiplier", self._env.multiplier), self._env.multiplier),
        )
        if new != self._flags:
            log.info("flags updated", extra={"flags": new.__dict__})
        self._flags = new
        self._loaded_at = time.monotonic()

    def get(self) -> LoadgenFlags:
        if time.monotonic() - self._loaded_at >= RELOAD_INTERVAL_S:
            self._reload()
        return self._flags
