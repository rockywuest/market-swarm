"""Tests for core Pydantic data models."""

import pytest
from pydantic import ValidationError

from market_swarm.models import (
    AgentResponse,
    Product,
    SimulationConfig,
    SimulationResult,
)


class TestProduct:
    def test_minimal_product(self):
        p = Product(name="Test", brand="B", category="C")
        assert p.product_type == "fmcg"  # default
        assert p.claims == []
        assert p.competitors == []

    def test_product_with_all_fields(self):
        p = Product(
            name="Bar",
            brand="Brand",
            category="Snacks",
            subcategory="Protein",
            product_type="fmcg",
            claims=["High Protein"],
            positioning="Premium",
            target_channels=["discounter"],
        )
        assert p.subcategory == "Protein"
        assert "High Protein" in p.claims

    def test_model_dump_roundtrip(self):
        p = Product(name="Test", brand="B", category="C")
        data = p.model_dump()
        p2 = Product(**data)
        assert p2.name == p.name


class TestAgentResponse:
    def test_valid_response(self, sample_agent_response_data):
        r = AgentResponse(
            agent_name="Test Agent",
            agent_type="buyer",
            **sample_agent_response_data,
        )
        assert r.score == 7.5
        assert r.would_list is True

    def test_score_validation_min(self):
        with pytest.raises(ValidationError):
            AgentResponse(
                agent_name="Test",
                agent_type="buyer",
                score=-1,
                would_list=True,
                key_feedback="bad",
            )

    def test_score_validation_max(self):
        with pytest.raises(ValidationError):
            AgentResponse(
                agent_name="Test",
                agent_type="buyer",
                score=11,
                would_list=True,
                key_feedback="bad",
            )

    def test_optional_fields(self):
        r = AgentResponse(
            agent_name="Test",
            agent_type="buyer",
            score=5,
            would_list=False,
            key_feedback="OK",
        )
        assert r.retailer is None
        assert r.price_feedback is None
        assert r.objections == []


class TestSimulationConfig:
    def test_defaults(self):
        c = SimulationConfig()
        assert c.rounds == 3
        assert "buyers" in c.agents
        assert c.focus_areas == []


class TestSimulationResult:
    def test_empty_result(self):
        p = Product(name="T", brand="B", category="C")
        r = SimulationResult(product=p)
        assert r.avg_score == 0.0
        assert r.listing_rate == 0.0
        assert r.responses == []

    def test_model_dump_includes_disclaimer(self):
        p = Product(name="T", brand="B", category="C")
        r = SimulationResult(product=p, disclaimer="Test disclaimer")
        data = r.model_dump()
        assert data["disclaimer"] == "Test disclaimer"
