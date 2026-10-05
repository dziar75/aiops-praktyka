"""Database access layer (PostgreSQL via psycopg 3 + connection pool)."""
from __future__ import annotations

import logging
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import settings
from .menu_data import SEED_MENU
from . import metrics

log = logging.getLogger("orders-api.db")

pool: AsyncConnectionPool | None = None

# Connections held out of the pool while the db_pool_leak resilience flag is
# active, so pool-exhaustion handling can be exercised under load.
_held_connections: list[Any] = []

_SCHEMA = """
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_pln NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    employee_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    total_pln NUMERIC(10, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price_pln NUMERIC(10, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
"""


async def open_pool() -> None:
    global pool
    pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        open=False,
        kwargs={"row_factory": dict_row},
    )
    await pool.open(wait=True, timeout=30)
    metrics.db_pool_size.set(settings.db_pool_max)


async def close_pool() -> None:
    global pool
    for conn in _held_connections:
        try:
            await pool.putconn(conn)  # type: ignore[union-attr]
        except Exception:  # pragma: no cover - best effort cleanup
            pass
    _held_connections.clear()
    if pool is not None:
        await pool.close()
        pool = None


def _require_pool() -> AsyncConnectionPool:
    if pool is None:
        raise RuntimeError("Database pool is not initialised")
    return pool


def update_pool_gauges() -> None:
    if pool is None:
        return
    stats = pool.get_stats()
    size = stats.get("pool_size", settings.db_pool_max)
    available = stats.get("pool_available", 0)
    metrics.db_pool_size.set(size)
    metrics.db_pool_connections_in_use.set(max(size - available, 0))


async def ping() -> None:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchone()


async def init_schema_and_seed() -> None:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SCHEMA)
            await cur.execute("SELECT COUNT(*) AS n FROM menu_items")
            row = await cur.fetchone()
            if row and row["n"] == 0:
                await cur.executemany(
                    "INSERT INTO menu_items (name, category, price_pln) VALUES (%s, %s, %s)",
                    SEED_MENU,
                )
                log.info("Seeded menu", extra={"seeded_items": len(SEED_MENU)})
        await conn.commit()


async def fetch_menu(slow: bool = False) -> list[dict[str, Any]]:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            if slow:
                await cur.execute("SELECT id FROM menu_items ORDER BY category, name")
                ids = [r["id"] for r in await cur.fetchall()]
                items: list[dict[str, Any]] = []
                for item_id in ids:
                    await cur.execute(
                        "SELECT id, name, category, price_pln FROM menu_items WHERE id = %s",
                        (item_id,),
                    )
                    items.append(await cur.fetchone())
                return items
            await cur.execute(
                "SELECT id, name, category, price_pln FROM menu_items ORDER BY category, name"
            )
            return list(await cur.fetchall())


async def search_menu(q: str) -> list[dict[str, Any]]:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            query = (
                "SELECT id, name, category, price_pln FROM menu_items "
                f"WHERE name ILIKE '%{q}%' OR category ILIKE '%{q}%' "
                "ORDER BY category, name"
            )
            await cur.execute(query)
            return list(await cur.fetchall())


async def create_order(employee_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                total = 0.0
                priced: list[tuple[int, int, float]] = []
                for item in items:
                    await cur.execute(
                        "SELECT price_pln FROM menu_items WHERE id = %s",
                        (item["menu_item_id"],),
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise ValueError(f"Unknown menu_item_id: {item['menu_item_id']}")
                    unit_price = float(row["price_pln"])
                    qty = int(item["qty"])
                    total += unit_price * qty
                    priced.append((item["menu_item_id"], qty, unit_price))

                await cur.execute(
                    "INSERT INTO orders (employee_id, status, total_pln) "
                    "VALUES (%s, %s, %s) RETURNING id, created_at",
                    (str(employee_id), "created", round(total, 2)),
                )
                order_row = await cur.fetchone()
                order_id = order_row["id"]

                await cur.executemany(
                    "INSERT INTO order_items (order_id, menu_item_id, qty, unit_price_pln) "
                    "VALUES (%s, %s, %s, %s)",
                    [(order_id, m, qt, pr) for (m, qt, pr) in priced],
                )

    return {
        "id": order_id,
        "employee_id": str(employee_id),
        "status": "created",
        "total_pln": round(total, 2),
        "created_at": order_row["created_at"],
    }


async def get_order(order_id: int) -> dict[str, Any] | None:
    p = _require_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, employee_id, status, total_pln, created_at "
                "FROM orders WHERE id = %s",
                (order_id,),
            )
            order = await cur.fetchone()
            if order is None:
                return None
            await cur.execute(
                "SELECT menu_item_id, qty, unit_price_pln FROM order_items "
                "WHERE order_id = %s ORDER BY id",
                (order_id,),
            )
            order["items"] = list(await cur.fetchall())
            return order


async def leak_one_connection() -> None:
    """Check a connection out of the pool without returning it."""
    p = _require_pool()
    try:
        conn = await p.getconn()
        _held_connections.append(conn)
    except Exception:  # pragma: no cover
        pass
