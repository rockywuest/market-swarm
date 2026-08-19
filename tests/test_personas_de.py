"""Tests for German persona generator (personas_de module)."""

import json
import os
import tempfile
from pathlib import Path


from market_swarm.industry_packs.base import PersonaDefinition
from market_swarm.personas_de import (
    DemographicRecord,
    MarginalValidationReport,
    PersonaRecord,
    REFERENCE_MARGINALS,
    _generate_mock_narrative,
    _sample_from_distribution,
    _sample_household_size,
    _sample_income_band,
    _sample_occupation_status,
    compile_stats,
    sample_demographic_records,
    validate_marginals,
    write_personas_jsonl,
    write_stats_json,
)


class TestDemographicSampling:
    """Test Stage 1: demographic record sampling."""

    def test_sample_from_distribution_deterministic(self):
        """Sampling with same seed should give same result."""
        import random

        rng1 = random.Random(42)
        rng2 = random.Random(42)

        dist = {"a": 0.5, "b": 0.3, "c": 0.2}
        result1 = _sample_from_distribution(dist, rng1)
        result2 = _sample_from_distribution(dist, rng2)

        assert result1 == result2

    def test_sample_from_distribution_respects_weights(self):
        """Over many samples, distribution should approximate weights."""
        import random

        rng = random.Random(42)
        dist = {"a": 0.7, "b": 0.3}
        samples = [_sample_from_distribution(dist, rng) for _ in range(1000)]

        a_count = samples.count("a")
        b_count = samples.count("b")

        a_proportion = a_count / len(samples)
        b_proportion = b_count / len(samples)

        # Allow 5% tolerance
        assert 0.65 < a_proportion < 0.75
        assert 0.25 < b_proportion < 0.35

    def test_sample_household_size_returns_int(self):
        """sample_household_size should return int."""
        import random

        rng = random.Random(42)
        for _ in range(10):
            size = _sample_household_size(rng)
            assert isinstance(size, int)
            assert 1 <= size <= 8

    def test_sample_occupation_status_age_conditioned(self):
        """Occupation status should be conditioned on age band."""
        import random

        age_bands = ["18-29", "30-49", "50-64", "65+"]

        for age_band in age_bands:
            rng = random.Random(42)
            samples = [_sample_occupation_status(age_band, rng) for _ in range(100)]

            if age_band == "18-29":
                # Higher proportion of students and employed
                assert samples.count("student") > 5
            elif age_band == "65+":
                # Higher proportion of retired
                assert samples.count("retired") > 30

    def test_sample_education_valid_values(self):
        """Education samples should be one of the valid bands."""
        import random

        rng = random.Random(42)
        valid_educations = {"low", "medium", "high"}

        for _ in range(50):
            education = _sample_from_distribution(REFERENCE_MARGINALS["education_isced"], rng)
            assert education in valid_educations

    def test_sample_income_band_education_conditioned(self):
        """Income should be lightly conditioned on education."""
        import random

        # Sample from each education level
        for education in ["low", "medium", "high"]:
            rng = random.Random(42)
            samples = [_sample_income_band(education, rng) for _ in range(100)]

            if education == "high":
                # Higher education should have more high income
                high_income = samples.count("4000_plus")
                assert high_income > 20
            elif education == "low":
                # Lower education should have more low income
                low_income = samples.count("under_1500")
                assert low_income > 10

    def test_sample_demographic_records_correct_count(self):
        """Should generate exactly n records."""
        records = sample_demographic_records(50, seed=42)
        assert len(records) == 50

    def test_sample_demographic_records_deterministic(self):
        """Same seed should produce identical records."""
        records1 = sample_demographic_records(25, seed=42)
        records2 = sample_demographic_records(25, seed=42)

        assert records1 == records2

    def test_sample_demographic_records_varies_with_seed(self):
        """Different seeds should produce different records."""
        records1 = sample_demographic_records(25, seed=42)
        records2 = sample_demographic_records(25, seed=99)

        # Very high probability that at least some differ
        assert records1 != records2

    def test_sample_demographic_records_schema_complete(self):
        """Each record should have all required fields."""
        records = sample_demographic_records(10, seed=42)

        for record in records:
            assert isinstance(record, DemographicRecord)
            assert record.age_band in {"18-29", "30-49", "50-64", "65+"}
            assert record.gender in {"female", "male"}
            assert record.bundesland in REFERENCE_MARGINALS["bundesland_shares"].keys()
            assert 1 <= record.household_size <= 8
            assert record.education in {"low", "medium", "high"}
            assert record.net_household_income_band in {
                "under_1500",
                "1500_2500",
                "2500_4000",
                "4000_plus",
            }
            assert record.occupation_status in {
                "employed",
                "self_employed",
                "retired",
                "student",
                "not_employed",
            }

    def test_sample_demographic_records_consumer_fields(self):
        """Consumer dimension fields should be valid."""
        records = sample_demographic_records(10, seed=42)

        for record in records:
            assert record.grocery_channel_preference in {
                "hard_discounter",
                "full_range_supermarket",
                "specialty_local",
                "online_delivery",
            }
            assert record.organic_purchase_frequency in {
                "regularly",
                "sometimes",
                "rarely",
                "never",
            }
            assert record.price_vs_quality_orientation in {
                "price_priority",
                "balanced",
                "quality_priority",
                "brand_priority",
            }
            assert record.online_grocery_usage in {
                "regularly",
                "occasionally",
                "planning",
                "not_planning",
            }


class TestMarginalValidation:
    """Test marginal validation logic."""

    def test_validate_marginals_returns_reports(self):
        """validate_marginals should return list of reports."""
        records = sample_demographic_records(100, seed=42)
        reports = validate_marginals(records)

        assert isinstance(reports, list)
        assert len(reports) > 0
        assert all(isinstance(r, MarginalValidationReport) for r in reports)

    def test_validate_marginals_includes_all_fields(self):
        """Should have validation reports for all demographic fields."""
        records = sample_demographic_records(100, seed=42)
        reports = validate_marginals(records)

        field_names = {r.field_name for r in reports}
        expected_fields = {
            "age_band",
            "gender",
            "bundesland",
            "household_size",
            "education",
            "net_household_income_band",
            "occupation_status",
            "grocery_channel_preference",
            "organic_purchase_frequency",
            "price_vs_quality_orientation",
            "online_grocery_usage",
        }

        assert expected_fields.issubset(field_names)

    def test_validate_marginals_computes_deltas(self):
        """Per-option deltas should be computed for each field."""
        records = sample_demographic_records(100, seed=42)
        reports = validate_marginals(records)

        for report in reports:
            assert len(report.per_option_deltas) > 0
            assert report.max_delta >= 0
            # Max delta should be at least as large as any per-option delta
            assert report.max_delta == max(report.per_option_deltas.values())

    def test_validate_marginals_reference_vs_generated(self):
        """Reference and generated shares should be present."""
        records = sample_demographic_records(100, seed=42)
        reports = validate_marginals(records)

        for report in reports:
            assert len(report.reference_shares) > 0
            assert len(report.generated_shares) > 0
            # Should have same keys
            assert set(report.reference_shares.keys()) == set(report.generated_shares.keys())


class TestNarrativeGeneration:
    """Test Stage 2: narrative generation (mock mode)."""

    def test_generate_mock_narrative_returns_string(self):
        """Mock narrative should return a German string."""
        record = DemographicRecord(
            age_band="30-49",
            gender="female",
            bundesland="BY",
            household_size=2,
            education="high",
            net_household_income_band="2500_4000",
            occupation_status="employed",
            grocery_channel_preference="full_range_supermarket",
            organic_purchase_frequency="sometimes",
            price_vs_quality_orientation="balanced",
            online_grocery_usage="occasionally",
        )

        narrative = _generate_mock_narrative(record, "persona_000001")

        assert isinstance(narrative, str)
        assert len(narrative) > 50
        # Should contain German text
        assert any(char in narrative for char in "äöüß")

    def test_generate_mock_narrative_deterministic(self):
        """Same record and ID should give same narrative."""
        record = DemographicRecord(
            age_band="30-49",
            gender="female",
            bundesland="BY",
            household_size=2,
            education="high",
            net_household_income_band="2500_4000",
            occupation_status="employed",
            grocery_channel_preference="full_range_supermarket",
            organic_purchase_frequency="sometimes",
            price_vs_quality_orientation="balanced",
            online_grocery_usage="occasionally",
        )

        narrative1 = _generate_mock_narrative(record, "persona_000001")
        narrative2 = _generate_mock_narrative(record, "persona_000001")

        assert narrative1 == narrative2

    def test_generate_mock_narrative_includes_record_fields(self):
        """Narrative should reference record fields."""
        record = DemographicRecord(
            age_band="65+",
            gender="male",
            bundesland="NRW",
            household_size=1,
            education="low",
            net_household_income_band="under_1500",
            occupation_status="retired",
            grocery_channel_preference="hard_discounter",
            organic_purchase_frequency="never",
            price_vs_quality_orientation="price_priority",
            online_grocery_usage="not_planning",
        )

        narrative = _generate_mock_narrative(record, "persona_000002")

        # Should include some key information
        assert "NRW" in narrative or "Rentnerin" in narrative or "Discounter" in narrative


class TestPersonaRecord:
    """Test PersonaRecord model."""

    def test_persona_record_to_dict(self):
        """PersonaRecord.to_dict() should return dict with all fields."""
        record = DemographicRecord(
            age_band="30-49",
            gender="female",
            bundesland="BY",
            household_size=2,
            education="high",
            net_household_income_band="2500_4000",
            occupation_status="employed",
            grocery_channel_preference="full_range_supermarket",
            organic_purchase_frequency="sometimes",
            price_vs_quality_orientation="balanced",
            online_grocery_usage="occasionally",
        )

        persona = PersonaRecord(demographic=record, persona_text="Test narrative.")
        data = persona.to_dict()

        assert isinstance(data, dict)
        assert data["age_band"] == "30-49"
        assert data["gender"] == "female"
        assert data["persona_text"] == "Test narrative."

    def test_persona_record_to_dict_json_serializable(self):
        """to_dict() output should be JSON serializable."""
        record = DemographicRecord(
            age_band="30-49",
            gender="female",
            bundesland="BY",
            household_size=2,
            education="high",
            net_household_income_band="2500_4000",
            occupation_status="employed",
            grocery_channel_preference="full_range_supermarket",
            organic_purchase_frequency="sometimes",
            price_vs_quality_orientation="balanced",
            online_grocery_usage="occasionally",
        )

        persona = PersonaRecord(demographic=record, persona_text="Test")
        data = persona.to_dict()

        # Should not raise
        json_str = json.dumps(data, ensure_ascii=False)
        assert len(json_str) > 0


class TestOutputSerialization:
    """Test JSONL and stats output."""

    def test_write_personas_jsonl_creates_file(self):
        """write_personas_jsonl should create output file."""
        records = sample_demographic_records(5, seed=42)
        personas = [
            PersonaRecord(demographic=r, persona_text=f"Narrative {i}")
            for i, r in enumerate(records)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "personas.jsonl"
            write_personas_jsonl(personas, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_write_personas_jsonl_format(self):
        """Each line of JSONL should be valid JSON."""
        records = sample_demographic_records(3, seed=42)
        personas = [
            PersonaRecord(demographic=r, persona_text=f"Narrative {i}")
            for i, r in enumerate(records)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "personas.jsonl"
            write_personas_jsonl(personas, output_path)

            with open(output_path, encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 3

            for line in lines:
                data = json.loads(line)
                assert "age_band" in data
                assert "persona_text" in data

    def test_write_stats_json_creates_file(self):
        """write_stats_json should create output file."""
        stats = {"test": "data", "count": 42}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "stats.json"
            write_stats_json(stats, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_write_stats_json_format(self):
        """Stats JSON should be valid JSON."""
        stats = {"metadata": {"count": 10}, "summary": {"max_delta": 0.05}}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "stats.json"
            write_stats_json(stats, output_path)

            with open(output_path, encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded["metadata"]["count"] == 10

    def test_compile_stats_structure(self):
        """compile_stats should return dict with expected structure."""
        records = sample_demographic_records(10, seed=42)
        personas = [PersonaRecord(demographic=r, persona_text="Narrative") for r in records]
        validation_reports = validate_marginals(records)

        stats = compile_stats(
            personas,
            validation_reports,
            model="test-model",
            generated_at="2026-07-19T10:00:00",
            seed=42,
        )

        assert "metadata" in stats
        assert "marginal_validation" in stats
        assert "summary" in stats

        assert stats["metadata"]["count"] == 10
        assert stats["metadata"]["model"] == "test-model"
        assert stats["metadata"]["seed"] == 42


class TestMockMode:
    """Test behavior in MARKET_SWARM_MOCK mode."""

    def test_mock_mode_enabled(self):
        """Mock mode should be detectable."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            from market_swarm.engine import mock_enabled

            assert mock_enabled() is True
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_sample_demographic_records_works_without_llm(self):
        """Demographic sampling should work regardless of mock mode."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            records = sample_demographic_records(10, seed=42)
            assert len(records) == 10
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)


class TestPopulationLoaderIntegration:
    """Test personas-de as a population source."""

    def test_personas_de_source_validation(self):
        """personas-de should be recognized as valid source."""
        from market_swarm.population import load_population

        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            # Mock mode should not fail on invalid file
            personas = load_population("personas-de", 10, seed=42)
            assert len(personas) == 10
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_personas_de_mock_creates_persona_definitions(self):
        """Loaded personas should be PersonaDefinition objects."""
        from market_swarm.population import load_population

        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            personas = load_population("personas-de", 5, seed=42)
            for persona in personas:
                assert isinstance(persona, PersonaDefinition)
                assert persona.type == "population_consumer"
                assert len(persona.system_prompt) > 0
        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)
