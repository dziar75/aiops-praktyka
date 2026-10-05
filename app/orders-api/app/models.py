"""Request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    menu_item_id: int = Field(..., gt=0)
    qty: int = Field(..., gt=0, le=50)


class OrderIn(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=64)
    items: list[OrderItemIn] = Field(..., min_length=1)


class VersionOut(BaseModel):
    service: str
    version: str
    variant: str
