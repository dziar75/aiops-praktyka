import os

os.environ["SKIP_DB_INIT"] = "1"
os.environ.setdefault("APP_VERSION", "9.9.9-test")
os.environ.setdefault("APP_VARIANT", "stable")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
