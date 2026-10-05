"""SQS publishing. No-op when QUEUE_URL is not configured."""
from __future__ import annotations

import json
import logging
from functools import lru_cache

from .config import settings

log = logging.getLogger("orders-api.queue")


@lru_cache(maxsize=1)
def _client():
    import boto3

    return boto3.client("sqs", region_name=settings.aws_region)


def publish_order(order: dict) -> None:
    if not settings.queue_url:
        return
    try:
        body = json.dumps(
            {
                "order_id": order["id"],
                "employee_id": order["employee_id"],
                "total_pln": order["total_pln"],
            },
            default=str,
        )
        _client().send_message(QueueUrl=settings.queue_url, MessageBody=body)
    except Exception as exc:
        log.error(
            "Failed to publish order to queue",
            extra={"order_id": order.get("id"), "error": str(exc)},
            exc_info=True,
        )
