"""FMCG data models."""

from typing import Optional

from pydantic import BaseModel, Field


class Attributes(BaseModel):
    weight_g: int
    protein_g: Optional[float] = None
    sugar_g: Optional[float] = None
    fiber_g: Optional[float] = None
    organic: bool = False
    vegan: bool = False
    gluten_free: bool = False


class Pricing(BaseModel):
    rrp_eur: float = Field(description="Recommended retail price in EUR")
    trade_price_eur: float = Field(description="Trade/wholesale price in EUR")
    margin_retail_pct: float = Field(description="Retail margin percentage")


class Competitor(BaseModel):
    name: str
    brand: Optional[str] = None
    price_eur: float
    weight_g: Optional[int] = None
    protein_g: Optional[float] = None
    channel: Optional[str] = None
