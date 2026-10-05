"""Daily traffic profile for the canteen (Europe/Warsaw local time)."""

import math
import random
from datetime import datetime
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
NIGHT_RPS = 0.5
WEEKEND_FACTOR = 0.3
NOISE = 0.10


def _gauss(h: float, mu: float, sigma: float) -> float:
    return math.exp(-0.5 * ((h - mu) / sigma) ** 2)


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def _plateau(h: float, rise_start: float, rise_end: float, fall_start: float, fall_end: float) -> float:
    return _smoothstep(rise_start, rise_end, h) * (1.0 - _smoothstep(fall_start, fall_end, h))


def base_rps(now: datetime, peak_rps: float) -> float:
    """Noise-free target RPS for the given moment."""
    local = now.astimezone(WARSAW)
    h = local.hour + local.minute / 60 + local.second / 3600

    office_hours = _plateau(h, 7.0, 9.0, 17.0, 20.0) * 0.10 * peak_rps
    morning = _gauss(h, 8.5, 0.55) * 0.22 * peak_rps
    afternoon = _gauss(h, 15.0, 1.1) * 0.12 * peak_rps
    lunch_amp = max(0.0, peak_rps - NIGHT_RPS - 0.10 * peak_rps)
    lunch = _plateau(h, 10.75, 11.5, 13.5, 14.5) * lunch_amp

    rps = NIGHT_RPS + office_hours + morning + afternoon + lunch
    if local.weekday() >= 5:
        rps = max(NIGHT_RPS * WEEKEND_FACTOR, rps * WEEKEND_FACTOR)
    return rps


def target_rps(now: datetime, peak_rps: float, multiplier: float) -> float:
    noisy = base_rps(now, peak_rps) * random.uniform(1 - NOISE, 1 + NOISE)
    return max(0.05, noisy * multiplier)
