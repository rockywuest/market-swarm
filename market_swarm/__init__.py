"""Market Swarm — LLM-powered market simulation for product launches."""

from .engine import print_results, run_simulation
from .models import (
    AgentResponse,
    Product,
    SimulationConfig,
    SimulationResult,
)

__version__ = "1.0.0"

__all__ = [
    "run_simulation",
    "print_results",
    "Product",
    "SimulationResult",
    "AgentResponse",
    "SimulationConfig",
]
