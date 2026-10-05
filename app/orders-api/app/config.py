"""Static configuration read from the environment at process start."""
from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.service_name: str = os.getenv("OTEL_SERVICE_NAME", "orders-api")
        self.version: str = os.getenv("APP_VERSION", "0.0.0-dev")
        self.variant: str = os.getenv("APP_VARIANT", "stable")

        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://kantyna:kantyna@postgres:5432/kantyna",
        )
        self.db_pool_min: int = int(os.getenv("DB_POOL_MIN", "1"))
        self.db_pool_max: int = int(os.getenv("DB_POOL_MAX", "10"))

        self.payments_url: str = os.getenv("PAYMENTS_URL", "http://payments:8080")
        self.payments_timeout_s: float = float(os.getenv("PAYMENTS_TIMEOUT_S", "3.0"))

        self.queue_url: str = os.getenv("QUEUE_URL", "")
        self.aws_region: str = os.getenv("AWS_REGION", "eu-central-1")

        self.otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        self.flags_file: str = os.getenv("FLAGS_FILE", "/etc/kantyna/flags/flags.json")
        self.flags_reload_seconds: float = float(os.getenv("FLAGS_RELOAD_SECONDS", "15"))

        # Skip schema bootstrap / background loops in unit tests.
        self.skip_db_init: bool = os.getenv("SKIP_DB_INIT", "0") in ("1", "true", "True")


settings = Settings()
