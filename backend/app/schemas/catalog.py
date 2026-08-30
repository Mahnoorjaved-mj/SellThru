"""Pydantic schemas for products/stores master data."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    is_active: Optional[bool] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
