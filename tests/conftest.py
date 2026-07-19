"""Shared fixtures for Market Swarm tests."""

import os
import textwrap

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure no real API keys are used during tests
os.environ.pop("MARKET_SWARM_API_KEY", None)


SAMPLE_PRODUCT_YAML = textwrap.dedent("""\
    product:
      name: "TestBar Pro"
      brand: "TestBrand"
      category: "Snacks"
      subcategory: "Protein"
      product_type: fmcg
      attributes:
        weight_g: 50
        protein_g: 15
        sugar_g: 3
        fiber_g: 5
        organic: false
        vegan: true
        gluten_free: false
      pricing:
        rrp_eur: 1.99
        trade_price_eur: 1.10
        margin_retail_pct: 45
      claims:
        - "High Protein"
      positioning: "Test product for unit tests"
      target_channels:
        - discounter
      competitors: []
    simulation:
      focus_areas:
        - pricing_acceptance
""")


@pytest.fixture
def sample_product_yaml() -> str:
    return SAMPLE_PRODUCT_YAML


@pytest.fixture
def sample_agent_response_data() -> dict:
    return {
        "score": 7.5,
        "would_list": True,
        "key_feedback": "Good product with strong protein content.",
        "objections": ["Price slightly high for the discount channel"],
        "suggestions": ["Groessere Packung anbieten"],
        "price_feedback": "UVP von 1.99 EUR ist akzeptabel.",
        "detailed_reasoning": "The product has solid attributes.",
    }


@pytest.fixture
async def api_client():
    """Async test client for the FastAPI app."""
    from market_swarm.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
