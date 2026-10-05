"""Kantyna order worker.

Consumes order messages from SQS, prepares the order and stores a receipt in S3.
"""

import json
import logging
import os
import random
import signal
import threading
import time
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from app.flags import FlagStore
from app.logging_setup import APP_VARIANT, APP_VERSION, setup_logging

setup_logging()
log = logging.getLogger("worker")

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
QUEUE_URL = os.getenv("QUEUE_URL", "").strip()
RECEIPTS_BUCKET = os.getenv("RECEIPTS_BUCKET", "").strip()
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9000"))
QUEUE_DEPTH_INTERVAL_S = 30
MAX_BATCH = 5
BACKOFF_CAP_S = 30.0

MESSAGES_PROCESSED = Counter(
    "worker_messages_processed_total", "Order messages processed by the worker", ["result"]
)
PROCESSING_SECONDS = Histogram(
    "worker_processing_seconds",
    "Time spent processing a single order message",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
QUEUE_VISIBLE = Gauge("worker_queue_visible_messages", "Approximate number of visible messages in the order queue")
AWS_ERRORS = Counter("worker_aws_errors_total", "AWS API errors", ["operation", "code"])

for _r in ("success", "failed"):
    MESSAGES_PROCESSED.labels(result=_r)


class ProcessingError(Exception):
    """Order could not be prepared."""


def _aws_error_fields(exc: Exception) -> dict:
    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        return {
            "error_code": err.get("Code", "Unknown"),
            "error": err.get("Message", str(exc)),
            "aws_operation": exc.operation_name,
            "request_id": exc.response.get("ResponseMetadata", {}).get("RequestId"),
        }
    return {"error_code": type(exc).__name__, "error": str(exc)}


class Backoff:
    def __init__(self, base: float = 1.0, cap: float = BACKOFF_CAP_S) -> None:
        self.base = base
        self.cap = cap
        self.attempt = 0

    def reset(self) -> None:
        self.attempt = 0

    def next_delay(self) -> float:
        self.attempt += 1
        delay = min(self.cap, self.base * (2 ** (self.attempt - 1)))
        return delay * random.uniform(0.8, 1.2)


class Worker:
    def __init__(self, flags: FlagStore, stop: threading.Event) -> None:
        self.flags = flags
        self.stop = stop
        cfg = Config(region_name=AWS_REGION, retries={"max_attempts": 3, "mode": "standard"},
                     read_timeout=30, connect_timeout=5)
        self.sqs = boto3.client("sqs", config=cfg)
        self.s3 = boto3.client("s3", config=cfg)
        self.backoff = Backoff()

    # ---- queue depth ----------------------------------------------------
    def queue_depth_loop(self) -> None:
        while not self.stop.is_set():
            try:
                resp = self.sqs.get_queue_attributes(
                    QueueUrl=QUEUE_URL, AttributeNames=["ApproximateNumberOfMessages"]
                )
                QUEUE_VISIBLE.set(int(resp["Attributes"].get("ApproximateNumberOfMessages", 0)))
            except (ClientError, BotoCoreError) as exc:
                fields = _aws_error_fields(exc)
                AWS_ERRORS.labels(operation="GetQueueAttributes", code=fields["error_code"]).inc()
                log.error("failed to read queue attributes", extra=fields)
            self.stop.wait(QUEUE_DEPTH_INTERVAL_S)

    # ---- processing -----------------------------------------------------
    def _prepare(self, order: dict) -> None:
        flags = self.flags.get()
        time.sleep(random.uniform(0.05, 0.25) + flags.processing_delay_ms / 1000.0)
        if flags.fail_rate > 0 and random.random() < flags.fail_rate:
            raise ProcessingError("kitchen station unavailable")

    def _write_receipt(self, order_id: str, order: dict) -> str:
        now = datetime.now(timezone.utc)
        key = f"receipts/{now:%Y/%m/%d}/{order_id}.json"
        receipt = {
            "order_id": order_id,
            "employee_id": order.get("employee_id"),
            "items": order.get("items", []),
            "total": order.get("total"),
            "prepared_at": now.isoformat().replace("+00:00", "Z"),
            "worker_version": APP_VERSION,
        }
        self.s3.put_object(
            Bucket=RECEIPTS_BUCKET,
            Key=key,
            Body=json.dumps(receipt).encode("utf-8"),
            ContentType="application/json",
        )
        return key

    def handle(self, message: dict) -> bool:
        """Process one message. Returns False when an AWS error occurred."""
        start = time.perf_counter()
        receipt_handle = message["ReceiptHandle"]
        order_id = "unknown"
        try:
            try:
                order = json.loads(message.get("Body") or "{}")
                order_id = str(order["order_id"])
            except (ValueError, KeyError, TypeError) as exc:
                raise ProcessingError(f"invalid message body: {exc}") from exc

            self._prepare(order)
            key = self._write_receipt(order_id, order)
            self.sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
        except ProcessingError as exc:
            MESSAGES_PROCESSED.labels(result="failed").inc()
            log.warning("order processing failed", extra={"order_id": order_id, "result": "failed", "error": str(exc)})
            return True
        except (ClientError, BotoCoreError) as exc:
            fields = _aws_error_fields(exc)
            AWS_ERRORS.labels(operation=fields.get("aws_operation", "unknown"), code=fields["error_code"]).inc()
            MESSAGES_PROCESSED.labels(result="failed").inc()
            log.error("AWS error while processing order",
                      extra={"order_id": order_id, "result": "failed", "bucket": RECEIPTS_BUCKET, **fields})
            return False
        finally:
            PROCESSING_SECONDS.observe(time.perf_counter() - start)

        MESSAGES_PROCESSED.labels(result="success").inc()
        log.info("order prepared", extra={
            "order_id": order_id, "result": "success", "receipt_key": key,
            "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        })
        return True

    def run(self) -> None:
        threading.Thread(target=self.queue_depth_loop, name="queue-depth", daemon=True).start()
        log.info("polling queue", extra={"queue_url": QUEUE_URL, "bucket": RECEIPTS_BUCKET})
        while not self.stop.is_set():
            try:
                resp = self.sqs.receive_message(
                    QueueUrl=QUEUE_URL,
                    MaxNumberOfMessages=MAX_BATCH,
                    WaitTimeSeconds=20,
                    MessageSystemAttributeNames=["ApproximateReceiveCount"],
                )
            except (ClientError, BotoCoreError) as exc:
                fields = _aws_error_fields(exc)
                AWS_ERRORS.labels(operation="ReceiveMessage", code=fields["error_code"]).inc()
                delay = self.backoff.next_delay()
                log.error("failed to receive messages", extra={**fields, "retry_in_s": round(delay, 1)})
                self.stop.wait(delay)
                continue

            healthy = True
            for message in resp.get("Messages", []):
                if self.stop.is_set():
                    break
                healthy = self.handle(message) and healthy

            if healthy:
                self.backoff.reset()
            else:
                delay = self.backoff.next_delay()
                log.warning("backing off after AWS errors", extra={"retry_in_s": round(delay, 1)})
                self.stop.wait(delay)


def main() -> None:
    stop = threading.Event()

    def _shutdown(signum, _frame):
        log.info("shutdown requested", extra={"signal": signal.Signals(signum).name})
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    start_http_server(METRICS_PORT)
    flags = FlagStore()
    flags.start(stop)
    log.info("worker starting", extra={
        "variant": APP_VARIANT, "region": AWS_REGION, "metrics_port": METRICS_PORT,
        "flags": flags.get().__dict__, "otel_endpoint": OTEL_ENDPOINT or None,
    })

    if not QUEUE_URL:
        log.info("QUEUE_URL not set, worker idling")
        while not stop.wait(60):
            log.debug("idle")
        return

    if not RECEIPTS_BUCKET:
        log.warning("RECEIPTS_BUCKET not set, receipt uploads will fail")

    Worker(flags, stop).run()
    log.info("worker stopped")


if __name__ == "__main__":
    main()
