"""B2B SaaS professional services product models."""

from typing import Optional

from pydantic import BaseModel, Field


class Attributes(BaseModel):
    """Product attributes and capabilities."""

    deployment: str = "cloud"
    integration_effort: Optional[str] = None
    data_security: Optional[str] = None
    ai_powered: bool = False
    languages: list[str] = Field(default_factory=lambda: ["en"])
    certifications: list[str] = Field(default_factory=list)


class Pricing(BaseModel):
    """Pricing and licensing terms."""

    monthly_per_user_eur: Optional[float] = None
    annual_per_user_eur: Optional[float] = None
    flat_monthly_eur: Optional[float] = None
    flat_annual_eur: Optional[float] = None
    free_trial: bool = False
    free_tier: bool = False
    pricing_model: str = "per_user"
    enterprise_custom: bool = False


class Competitor(BaseModel):
    """Competitive product information."""

    name: str
    brand: Optional[str] = None
    monthly_price_eur: Optional[float] = None
    pricing_model: Optional[str] = None
    key_differentiator: Optional[str] = None
    market_position: Optional[str] = None
