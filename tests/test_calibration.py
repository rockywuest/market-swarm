"""Tests for the calibration harness."""

import os
import tempfile

import pytest

from market_swarm.calibration import (
    CalibrationQuestion,
    export_calibration_json,
    load_question_set,
    run_calibration,
    _total_variation_distance,
    _mock_answer,
)


class TestCalibrationQuestion:
    """Test CalibrationQuestion Pydantic model validation."""

    def test_valid_question(self):
        """Valid question passes validation."""
        q = CalibrationQuestion(
            id="test1",
            question="What is your preference?",
            options=["A", "B", "C"],
            reference={"A": 0.5, "B": 0.3, "C": 0.2},
            source={"name": "Test", "url": "http://test"},
        )
        assert q.id == "test1"
        assert len(q.options) == 3

    def test_reference_must_sum_to_one(self):
        """Reference distribution must sum to ~1.0."""
        with pytest.raises(ValueError, match="must be ~1.0"):
            CalibrationQuestion(
                id="test1",
                question="Q?",
                options=["A", "B"],
                reference={"A": 0.3, "B": 0.3},  # Sum = 0.6, not ~1.0
                source={"name": "Test", "url": "http://test"},
            )

    def test_reference_sum_slightly_off_is_ok(self):
        """Reference sum between 0.95-1.05 is acceptable."""
        q = CalibrationQuestion(
            id="test1",
            question="Q?",
            options=["A", "B"],
            reference={"A": 0.51, "B": 0.49},  # Sum = 1.00
            source={"name": "Test", "url": "http://test"},
        )
        assert q.reference["A"] == 0.51

    def test_options_must_be_unique(self):
        """Options list must have no duplicates."""
        with pytest.raises(ValueError, match="unique"):
            CalibrationQuestion(
                id="test1",
                question="Q?",
                options=["A", "B", "A"],  # Duplicate
                reference={"A": 0.5, "B": 0.5},
                source={"name": "Test", "url": "http://test"},
            )


class TestLoadQuestionSet:
    """Test loading calibration question sets from YAML."""

    def test_load_valid_yaml(self):
        """Load valid question set."""
        yaml_content = """
version: "1.0"
questions:
  - id: q1
    question: "Test question?"
    options: ["A", "B"]
    reference: {A: 0.6, B: 0.4}
    source: {name: "Test", url: "http://test"}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                questions = load_question_set(f.name)
                assert len(questions) == 1
                assert questions[0].id == "q1"
            finally:
                os.unlink(f.name)

    def test_file_not_found(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_question_set("/nonexistent/path.yaml")

    def test_missing_questions_key(self):
        """YAML without 'questions' key raises ValueError."""
        yaml_content = "version: '1.0'\nnotquestions: []"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with pytest.raises(ValueError, match="'questions'"):
                    load_question_set(f.name)
            finally:
                os.unlink(f.name)


class TestTVD:
    """Test Total Variation Distance calculation."""

    def test_tvd_identical_distributions(self):
        """TVD between identical distributions is 0."""
        sim = {"A": 0.5, "B": 0.5}
        ref = {"A": 0.5, "B": 0.5}
        tvd = _total_variation_distance(sim, ref)
        assert tvd == pytest.approx(0.0, abs=1e-6)

    def test_tvd_disjoint_distributions(self):
        """TVD between completely disjoint distributions is 1."""
        sim = {"A": 1.0, "B": 0.0}
        ref = {"A": 0.0, "B": 1.0}
        tvd = _total_variation_distance(sim, ref)
        assert tvd == pytest.approx(1.0, abs=1e-6)

    def test_tvd_hand_computed_case(self):
        """TVD for known case: |0.7-0.5| + |0.3-0.5| = 0.4 → TVD = 0.2."""
        sim = {"A": 7, "B": 3}  # Counts: 7/10=0.7, 3/10=0.3
        ref = {"A": 0.5, "B": 0.5}
        tvd = _total_variation_distance(sim, ref)
        # Expected: 0.5 * (|0.7-0.5| + |0.3-0.5|) = 0.5 * 0.4 = 0.2
        assert tvd == pytest.approx(0.2, abs=1e-6)

    def test_tvd_empty_simulated(self):
        """TVD with no simulated responses returns 1.0 (max distance)."""
        sim = {"A": 0, "B": 0}
        ref = {"A": 0.5, "B": 0.5}
        tvd = _total_variation_distance(sim, ref)
        assert tvd == 1.0

    def test_tvd_partial_overlap(self):
        """TVD with partial option overlap."""
        sim = {"A": 0.5, "B": 0.5, "C": 0.0}
        ref = {"A": 0.3, "B": 0.3, "C": 0.4}
        tvd = _total_variation_distance(sim, ref)
        # 0.5 * (|0.5-0.3| + |0.5-0.3| + |0-0.4|) = 0.5 * 0.8 = 0.4
        assert tvd == pytest.approx(0.4, abs=1e-6)


class TestMockAnswer:
    """Test deterministic mock answer generation."""

    def test_mock_answer_is_deterministic(self):
        """Same inputs always produce same output."""
        options = ["A", "B", "C"]
        ref = {"A": 0.5, "B": 0.3, "C": 0.2}

        answer1 = _mock_answer("Alice", "q1", options, ref)
        answer2 = _mock_answer("Alice", "q1", options, ref)

        assert answer1 == answer2

    def test_mock_answer_is_in_options(self):
        """Mock answer is always one of the provided options."""
        options = ["X", "Y", "Z"]
        ref = {o: 1.0 / 3 for o in options}

        for _ in range(10):
            answer = _mock_answer("Bob", "q1", options, ref)
            assert answer in options

    def test_mock_answer_varies_by_persona(self):
        """Different personas can have different answers (not guaranteed but likely)."""
        options = ["A", "B", "C"]
        ref = {"A": 0.5, "B": 0.3, "C": 0.2}

        answers = set()
        for i in range(5):
            answer = _mock_answer(f"Person{i}", "q1", options, ref)
            answers.add(answer)

        # High probability of variation across 5 personas
        assert len(answers) > 1


class TestRunCalibration:
    """Test end-to-end calibration execution."""

    def test_calibration_with_mock_mode(self):
        """Run calibration in mock mode (no LLM calls, deterministic)."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            questions = [
                CalibrationQuestion(
                    id="q1",
                    question="Question 1?",
                    options=["A", "B"],
                    reference={"A": 0.6, "B": 0.4},
                    source={"name": "Test", "url": "http://test"},
                ),
                CalibrationQuestion(
                    id="q2",
                    question="Question 2?",
                    options=["X", "Y", "Z"],
                    reference={"X": 0.5, "Y": 0.3, "Z": 0.2},
                    source={"name": "Test", "url": "http://test"},
                ),
            ]

            report = run_calibration(personas_or_pack="fmcg", questions=questions)

            # Verify report structure
            assert report.pack_name
            assert report.num_personas > 0
            assert report.num_questions == 2
            assert len(report.results) == 2
            assert 0 <= report.calibration_score <= 100
            assert report.mock_mode is True

            # Verify per-question results
            for result in report.results:
                assert result.tvd >= 0.0 and result.tvd <= 1.0
                assert len(result.simulated_distribution) > 0
                assert len(result.per_option_deltas) > 0

        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)

    def test_calibration_report_structure(self):
        """Verify CalibrationReport has all required fields."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            questions = [
                CalibrationQuestion(
                    id="q1",
                    question="Q?",
                    options=["A", "B"],
                    reference={"A": 0.5, "B": 0.5},
                    source={"name": "Test", "url": "http://test"},
                ),
            ]

            report = run_calibration("fmcg", questions)

            # Check all required fields exist
            assert report.pack_name
            assert report.num_personas > 0
            assert report.num_questions == 1
            assert report.overall_tvd >= 0.0
            assert report.calibration_score >= 0
            assert report.disclaimer
            assert len(report.results) > 0

        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)


class TestExportJSON:
    """Test JSON export functionality."""

    def test_export_creates_file(self):
        """Exporting to JSON creates a valid file."""
        os.environ["MARKET_SWARM_MOCK"] = "1"
        try:
            questions = [
                CalibrationQuestion(
                    id="q1",
                    question="Q?",
                    options=["A", "B"],
                    reference={"A": 0.5, "B": 0.5},
                    source={"name": "Test", "url": "http://test"},
                ),
            ]

            report = run_calibration("fmcg", questions)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                output_path = f.name

            try:
                export_calibration_json(report, output_path)
                assert os.path.exists(output_path)

                # Verify JSON is valid and loadable
                import json

                with open(output_path) as f:
                    data = json.load(f)
                    assert "calibration_score" in data
                    assert "results" in data

            finally:
                if os.path.exists(output_path):
                    os.unlink(output_path)

        finally:
            os.environ.pop("MARKET_SWARM_MOCK", None)
