"""Pydantic models for the Market Swarm REST API.

Separate from core models.py — these handle request/response shapes,
job status tracking, and API-specific metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Enums ---


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


# --- Request Models ---


class SimulationRequest(BaseModel):
    """Request body for POST /api/simulations."""

    product_yaml: str = Field(description="Full YAML content of the product definition")
    model_name: str = Field(default="claude-sonnet-4-5", description="LLM model to use")
    pack_override: Optional[str] = Field(default=None, description="Force a specific industry pack")


# --- Response Models ---


class PackInfo(BaseModel):
    """Industry pack summary for GET /api/packs."""

    product_type: str
    display_name: str
    version: str
    description: str
    persona_count: int


class PersonaInfo(BaseModel):
    """Persona summary for GET /api/packs/{pack_type}/personas."""

    name: str
    type: str
    retailer: Optional[str] = None
    pack_type: str


class ProgressInfo(BaseModel):
    """Simulation progress for polling UI."""

    completed: int = 0
    total: int = 0


class JobResponse(BaseModel):
    """Job status response for GET /api/simulations/{job_id}."""

    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    product_name: str
    pack_type: str
    model_name: str
    progress: ProgressInfo = Field(default_factory=ProgressInfo)
    error: Optional[str] = None


class ResultResponse(BaseModel):
    """Full simulation result for GET /api/results/{job_id}."""

    job_id: str
    product: Any
    responses: list[Any]
    avg_score: float
    listing_rate: float
    top_objections: list[str]
    top_suggestions: list[str]
    channel_scores: dict[str, float]
    disclaimer: str
    model_used: str
    execution_time_seconds: float
    created_at: datetime
