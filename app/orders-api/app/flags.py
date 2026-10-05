"""Runtime feature / resilience flags.

Values come from environment variables and, when present, an optional JSON
file (a mounted ConfigMap). The file is re-read on a fixed interval so changes
take effect without a restart. File values take precedence over environment
values when the file and the relevant section are present.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable

from .config import settings

_SECTION = "orders-api"

# name -> (env var, caster, default)
_SPEC: dict[str, tuple[str, Callable[[Any], Any], Any]] = {
    "error_rate": ("ERROR_RATE", float, 0.0),
    "memory_leak_mb_per_min": ("MEMORY_LEAK_MB_PER_MIN", float, 0.0),
    "cpu_burn": ("CPU_BURN", None, False),
    "db_pool_leak": ("DB_POOL_LEAK", None, False),
    "slow_menu_query": ("SLOW_MENU_QUERY", None, False),
    "log_noise": ("LOG_NOISE", None, False),
    "feedback_text": ("FEEDBACK_TEXT", str, ""),
}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _cast(name: str, caster: Callable[[Any], Any] | None, raw: Any) -> Any:
    if caster is None:  # boolean flag
        return _to_bool(raw)
    try:
        return caster(raw)
    except (TypeError, ValueError):
        return _SPEC[name][2]


class FlagStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, Any] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.reload()

    def _read_file_section(self) -> dict[str, Any]:
        path = settings.flags_file
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            section = data.get(_SECTION, {})
            return section if isinstance(section, dict) else {}
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            return {}

    def reload(self) -> None:
        file_section = self._read_file_section()
        resolved: dict[str, Any] = {}
        for name, (env_var, caster, default) in _SPEC.items():
            if name in file_section:
                resolved[name] = _cast(name, caster, file_section[name])
            elif env_var in os.environ:
                resolved[name] = _cast(name, caster, os.environ[env_var])
            else:
                resolved[name] = default
        with self._lock:
            self._values = resolved

    def get(self, name: str) -> Any:
        with self._lock:
            return self._values.get(name, _SPEC[name][2])

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._values)

    def start(self) -> None:
        if self._thread is not None:
            return

        def _loop() -> None:
            while not self._stop.wait(settings.flags_reload_seconds):
                self.reload()

        self._thread = threading.Thread(target=_loop, name="flags-reload", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


flags = FlagStore()
