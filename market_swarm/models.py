"""Data models for Market Swarm.

Industry-specific models (Attributes, Pricing, Competitor) live in
industry_packs/<pack>/models.py and are loaded dynamically by the registry.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str
    brand: str
    category: str
    subcategory: Optional[str] = None
    product_type: str = "fmcg"
    attributes: Any = Field(default_factory=dict)
    pricing: Any = Field(default_factory=dict)
    claims: list[str] = Field(default_factory=list)
    positioning: str = ""
    target_channels: list[str] = Field(default_factory=list)
    competitors: list[Any] = Field(default_factory=list)


class SimulationConfig(BaseModel):
    agents: dict[str, int] = Field(default={"buyers": 12, "category_managers": 8, "consumers": 30})
    rounds: int = 3
    focus_areas: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """A single agent's evaluation of a product."""

    agent_name: str
    agent_type: str
    retailer: Optional[str] = None
    score: float = Field(ge=0, le=10, description="Overall score 0-10")
    would_list: bool = Field(description="Would list/buy this product?")
    key_feedback: str = Field(description="One-line summary")
    objections: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    price_feedback: Optional[str] = None
    detailed_reasoning: str = ""


class SimulationResult(BaseModel):
    """Aggregated results from a simulation run."""

    product: Product
    responses: list[AgentResponse] = Field(default_factory=list)
    avg_score: float = 0.0
    listing_rate: float = 0.0
    top_objections: list[str] = Field(default_factory=list)
    top_suggestions: list[str] = Field(default_factory=list)
    channel_scores: dict[str, float] = Field(default_factory=dict)
    disclaimer: str = ""
