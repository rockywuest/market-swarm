"""Tests for industry pack registry discovery and loading."""

import pytest

from market_swarm.registry import get_pack, list_packs, get_all_personas


class TestListPacks:
    def test_discovers_all_packs(self):
        packs = list_packs()
        pack_types = {p.product_type for p in packs}
        assert "fmcg" in pack_types
        assert "b2b_saas" in pack_types
        assert "pharma" in pack_types
        assert "automotive" in pack_types

    def test_pack_has_required_fields(self):
        for pack in list_packs():
            assert pack.name
            assert pack.display_name
            assert pack.version
            assert pack.product_type
            assert pack.prompt_builder is not None
            assert len(pack.personas) > 0


class TestGetPack:
    def test_fmcg_pack(self):
        pack = get_pack("fmcg")
        assert pack.product_type == "fmcg"
        assert pack.attributes_model is not None
        assert pack.pricing_model is not None
        assert len(pack.personas) == 12

    def test_b2b_saas_pack(self):
        pack = get_pack("b2b_saas")
        assert pack.product_type == "b2b_saas"
        assert len(pack.personas) == 10

    def test_pharma_pack(self):
        pack = get_pack("pharma")
        assert pack.product_type == "pharma"
        assert len(pack.personas) == 10

    def test_automotive_pack(self):
        pack = get_pack("automotive")
        assert pack.product_type == "automotive"
        assert len(pack.personas) == 10

    def test_invalid_pack_raises(self):
        with pytest.raises(ValueError, match="No Industry Pack found"):
            get_pack("nonexistent_pack")


class TestPersonas:
    def test_all_personas_have_system_prompt(self):
        for persona in get_all_personas():
            assert persona.name, "Persona must have a name"
            assert persona.type, "Persona must have a type"
            assert len(persona.system_prompt) > 50, (
                f"Persona {persona.name} system_prompt too short"
            )

    def test_all_personas_have_evaluation_criteria(self):
        for persona in get_all_personas():
            assert len(persona.evaluation_criteria) >= 3, (
                f"Persona {persona.name} needs at least 3 evaluation criteria"
            )

    def test_total_persona_count(self):
        all_personas = get_all_personas()
        assert len(all_personas) == 42  # 12 + 10 + 10 + 10

    def test_persona_to_system_message(self):
        pack = get_pack("fmcg")
        persona = pack.personas[0]
        msg = persona.to_system_message()
        assert isinstance(msg, str)
        assert len(msg) > 50


class TestPromptBuilder:
    def test_fmcg_builds_prompt(self):
        pack = get_pack("fmcg")
        # Need a minimal product — use attributes model
        from market_swarm.models import Product

        attrs = pack.attributes_model(weight_g=50, protein_g=10)
        pricing = pack.pricing_model(rrp_eur=1.99, trade_price_eur=1.10, margin_retail_pct=45)
        product = Product(
            name="Test",
            brand="TestBrand",
            category="Snacks",
            product_type="fmcg",
            attributes=attrs,
            pricing=pricing,
        )
        prompt = pack.prompt_builder.build_evaluation_prompt(product, ["pricing"])
        assert "Test" in prompt
        assert "1.99" in prompt

    def test_panel_info_has_required_keys(self):
        from market_swarm.models import Product

        pack = get_pack("fmcg")
        attrs = pack.attributes_model(weight_g=50, protein_g=10)
        pricing = pack.pricing_model(rrp_eur=1.99, trade_price_eur=1.10, margin_retail_pct=45)
        product = Product(
            name="Test",
            brand="B",
            category="C",
            product_type="fmcg",
            attributes=attrs,
            pricing=pricing,
        )
        info = pack.prompt_builder.build_panel_info(product)
        assert "title" in info
        assert "pricing_line" in info
        assert "rate_label" in info
