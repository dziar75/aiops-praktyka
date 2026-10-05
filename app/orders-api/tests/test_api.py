from datetime import datetime, timezone

import pytest

from app import db, main
from app.payments import PaymentError


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_version(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"]
    assert body["version"] == "9.9.9-test"
    assert body["variant"] == "stable"


def test_metrics_exposes_build_info(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "kantyna_build_info" in resp.text
    assert "http_requests_total" in resp.text


def test_get_menu_returns_items(client, monkeypatch):
    async def fake_fetch_menu(slow=False):
        return [
            {"id": 1, "name": "Żurek", "category": "zupy", "price_pln": 12.0},
            {"id": 2, "name": "Schabowy", "category": "dania główne", "price_pln": 24.0},
        ]

    monkeypatch.setattr(db, "fetch_menu", fake_fetch_menu)
    resp = client.get("/api/menu")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["price"] == 12.0
    assert items[0]["name"] == "Żurek"


def test_search_menu(client, monkeypatch):
    captured = {}

    async def fake_search(q):
        captured["q"] = q
        return [{"id": 1, "name": "Pierogi ruskie", "category": "dania główne", "price_pln": 19.0}]

    monkeypatch.setattr(db, "search_menu", fake_search)
    resp = client.get("/api/menu/search", params={"q": "pierogi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "pierogi"
    assert captured["q"] == "pierogi"
    assert body["items"][0]["name"] == "Pierogi ruskie"


def test_search_requires_query(client):
    resp = client.get("/api/menu/search")
    assert resp.status_code == 422


def test_create_order_success(client, monkeypatch):
    async def fake_create_order(employee_id, items):
        return {
            "id": 101,
            "employee_id": employee_id,
            "status": "created",
            "total_pln": 43.0,
            "created_at": datetime.now(timezone.utc),
        }

    async def fake_charge(order_ref, amount):
        assert order_ref == "101"
        assert amount == 43.0
        return {"status": "approved", "transaction_id": "tx-abc"}

    monkeypatch.setattr(db, "create_order", fake_create_order)
    monkeypatch.setattr(main, "charge", fake_charge)
    monkeypatch.setattr(main, "publish_order", lambda order: None)

    resp = client.post(
        "/api/orders",
        json={"employee_id": "e-42", "items": [{"menu_item_id": 1, "qty": 2}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == 101
    assert body["transaction_id"] == "tx-abc"
    assert body["total"] == 43.0


def test_create_order_payment_failure(client, monkeypatch):
    async def fake_create_order(employee_id, items):
        return {
            "id": 7,
            "employee_id": employee_id,
            "status": "created",
            "total_pln": 10.0,
            "created_at": datetime.now(timezone.utc),
        }

    async def failing_charge(order_ref, amount):
        raise PaymentError("gateway_error")

    monkeypatch.setattr(db, "create_order", fake_create_order)
    monkeypatch.setattr(main, "charge", failing_charge)
    monkeypatch.setattr(main, "publish_order", lambda order: None)

    resp = client.post(
        "/api/orders",
        json={"employee_id": "e-1", "items": [{"menu_item_id": 1, "qty": 1}]},
    )
    assert resp.status_code == 402
    assert "gateway_error" in resp.json()["detail"]


def test_create_order_validation_error(client):
    resp = client.post("/api/orders", json={"employee_id": "e-1", "items": []})
    assert resp.status_code == 422


def test_get_order_found(client, monkeypatch):
    async def fake_get_order(order_id):
        return {
            "id": order_id,
            "employee_id": "e-9",
            "status": "created",
            "total_pln": 18.5,
            "created_at": datetime.now(timezone.utc),
            "items": [{"menu_item_id": 3, "qty": 1, "unit_price_pln": 18.5}],
        }

    monkeypatch.setattr(db, "get_order", fake_get_order)
    resp = client.get("/api/orders/55")
    assert resp.status_code == 200
    assert resp.json()["id"] == 55


def test_get_order_not_found(client, monkeypatch):
    async def fake_get_order(order_id):
        return None

    monkeypatch.setattr(db, "get_order", fake_get_order)
    resp = client.get("/api/orders/999")
    assert resp.status_code == 404


def test_error_rate_flag_injects_500(client, monkeypatch):
    from app import runtime

    monkeypatch.setattr(runtime, "should_fail_request", lambda: True)

    async def fake_fetch_menu(slow=False):
        return []

    monkeypatch.setattr(db, "fetch_menu", fake_fetch_menu)
    resp = client.get("/api/menu")
    assert resp.status_code == 500
