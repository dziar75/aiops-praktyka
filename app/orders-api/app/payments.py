"""Client for the payments service."""
from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger("orders-api.payments")


class PaymentError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


async def charge(order_ref: str, amount: float) -> dict:
    """Call the payments service. Raises PaymentError on failure."""
    url = f"{settings.payments_url}/pay"
    payload = {"amount": round(amount, 2), "order_ref": order_ref}
    try:
        async with httpx.AsyncClient(timeout=settings.payments_timeout_s) as client:
            resp = await client.post(url, json=payload)
    except httpx.TimeoutException as exc:
        raise PaymentError("timeout") from exc
    except httpx.HTTPError as exc:
        raise PaymentError("connection_error") from exc

    if resp.status_code != 200:
        reason = "declined"
        try:
            reason = resp.json().get("reason", reason)
        except Exception:
            pass
        raise PaymentError(reason)

    data = resp.json()
    if data.get("status") != "approved":
        raise PaymentError(data.get("reason", "declined"))
    return data
