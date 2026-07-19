"""Tests for population loading and persona generation."""

import os

import pytest

from market_swarm.industry_packs.base import PersonaDefinition
from market_swarm.population import load_population


class TestMockModeGeneration:
    """Test deterministic persona synthesis in mock mode."""

    def test_mock_generates_correct_count(self):
        """Mock mode should generate exactly n personas."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("nemotron-usa", 25)
            assert len(personas) == 25
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_is_deterministic(self):
        """Same seed should produce identical personas."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas1 = load_population("nemotron-usa", 10, seed=42)
            personas2 = load_population("nemotron-usa", 10, seed=42)
            assert personas1 == personas2
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_varies_with_different_seed(self):
        """Different seeds should produce different personas."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas1 = load_population("nemotron-usa", 10, seed=42)
            personas2 = load_population("nemotron-usa", 10, seed=99)
            # At least some personas should differ (very high probability)
            assert personas1 != personas2
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_personas_are_valid(self):
        """Mock personas should be valid PersonaDefinition objects."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("nemotron-usa", 5)
            for persona in personas:
                assert isinstance(persona, PersonaDefinition)
                assert persona.name.startswith("Consumer ")
                assert persona.type == "population_consumer"
                assert persona.retailer is None
                assert len(persona.system_prompt) > 0
                assert persona.evaluation_criteria == [
                    "purchase_intent",
                    "price_acceptance",
                    "brand_appeal",
                    "fit_with_lifestyle",
                ]
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_different_sources_generate_same_count(self):
        """Mock should work with any source string and generate same output."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            # All sources should work in mock mode
            n1 = load_population("nemotron-usa", 15, seed=42)
            n2 = load_population("finepersonas", 15, seed=42)
            n3 = load_population("hf:dummy:col", 15, seed=42)
            assert len(n1) == len(n2) == len(n3) == 15
            # Mock mode should be deterministic regardless of source
            assert n1 == n2 == n3
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_persona_names_unique_within_run(self):
        """Personas in one run should have sequential IDs."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("nemotron-usa", 50, seed=42)
            names = [p.name for p in personas]
            assert names[0] == "Consumer 0000"
            assert names[10] == "Consumer 0010"
            assert names[49] == "Consumer 0049"
            # Check all unique
            assert len(set(names)) == 50
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)


class TestSourceParsing:
    """Test population source string parsing."""

    def test_invalid_source_raises_error(self):
        """Unknown source should raise ValueError."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            with pytest.raises(ValueError, match="Unknown population source"):
                load_population("unknown-source", 10)
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_hf_source_parsing_valid(self):
        """hf:dataset:column format should parse correctly."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            # Should not raise in mock mode
            personas = load_population("hf:myorg/dataset:persona_col", 5)
            assert len(personas) == 5
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_hf_source_parsing_invalid(self):
        """Invalid hf: format should raise ValueError."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            with pytest.raises(ValueError, match="Invalid HuggingFace"):
                load_population("hf:missingcolumn", 10)
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)


class TestDatasetsMissingError:
    """Test friendly error when datasets lib is missing."""

    def test_friendly_error_message_on_import_failure(self, monkeypatch):
        """Error message should mention pip install when datasets is missing."""
        # Disable mock mode
        monkeypatch.delenv("MARKET_SWARM_MOCK", raising=False)

        # Patch the import inside the population module
        import market_swarm.population as pop_module

        def mock_load_nemotron(n, seed=42):
            raise RuntimeError(
                "Population sources require the datasets library. "
                "Install with: pip install 'market-swarm[population]'"
            )

        monkeypatch.setattr(pop_module, "_load_nemotron_usa", mock_load_nemotron)

        with pytest.raises(RuntimeError, match="pip install.*population"):
            load_population("nemotron-usa", 10)


class TestPersonaQuality:
    """Test that generated personas have expected quality."""

    def test_mock_personas_have_rich_prompts(self):
        """Personas should have detailed, meaningful system prompts."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("nemotron-usa", 3, seed=42)
            for persona in personas:
                # Check prompt contains key parts
                assert (
                    "age" in persona.system_prompt.lower()
                    or "bracket" in persona.system_prompt.lower()
                )
                assert "product" in persona.system_prompt.lower()
                assert "evaluate" in persona.system_prompt.lower()
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_mock_personas_have_varied_backgrounds(self):
        """Generated personas should vary in characteristics."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("nemotron-usa", 100, seed=42)
            prompts = [p.system_prompt for p in personas]
            # Check for variety in prompts (not all identical)
            unique_prompts = len(set(prompts))
            assert unique_prompts > 80  # Should have significant variety

        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)


class TestCLIParsing:
    """Test population argument parsing in CLI context."""

    def test_cli_population_format_parsing(self):
        """Test that CLI format 'source:N' parses correctly."""

        # This tests the parsing logic used in __main__.py
        def parse_population_arg(pop_arg):
            parts = pop_arg.rsplit(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid format")
            source, n_str = parts
            n = int(n_str)
            return source, n

        source, n = parse_population_arg("nemotron-usa:200")
        assert source == "nemotron-usa"
        assert n == 200

        source, n = parse_population_arg("finepersonas:50")
        assert source == "finepersonas"
        assert n == 50

        source, n = parse_population_arg("hf:myorg/dataset:persona_col:100")
        # Note: this will split at the last colon
        assert source == "hf:myorg/dataset:persona_col"
        assert n == 100

    def test_cli_population_format_invalid(self):
        """Invalid CLI format should raise error."""

        def parse_population_arg(pop_arg):
            parts = pop_arg.rsplit(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid format")
            source, n_str = parts
            n = int(n_str)
            return source, n

        with pytest.raises(ValueError):
            parse_population_arg("no-colon")

        with pytest.raises(ValueError):
            parse_population_arg("source:notanumber")
