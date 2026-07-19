"""Calibration harness for Market Swarm personas.

Validates persona realism by comparing simulated answer distributions
against known population distributions from public statistics.
Uses Total Variation Distance (TVD) as the primary metric.
"""

import json
import logging
import random
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from rich.table import Table

from .engine import (
    DEFAULT_MODEL,
    _get_client,
    _parse_llm_response,
    mock_enabled,
)
from .registry import get_pack

logger = logging.getLogger(__name__)
console = Console()


class CalibrationQuestion(BaseModel):
    """A single calibration question with reference distribution."""

    id: str
    question: str
    options: list[str]
    reference: dict[str, float] = Field(description="Option -> proportion, must sum to ~1.0")
    source: dict[str, str] = Field(description="name and url of statistical source")
    note: Optional[str] = None

    @field_validator("reference")
    @classmethod
    def validate_reference_sum(cls, v: dict) -> dict:
        """Ensure reference distribution sums to approximately 1.0."""
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Reference distribution sums to {total}, must be ~1.0")
        return v

    @field_validator("options")
    @classmethod
    def validate_options_unique(cls, v: list[str]) -> list[str]:
        """Ensure all options are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Options must be unique")
        return v


class CalibrationResponse(BaseModel):
    """A persona's response to a calibration question."""

    persona_name: str
    question_id: str
    choice: str


class CalibrationResult(BaseModel):
    """Result for a single question: simulated vs reference distribution."""

    question_id: str
    question: str
    simulated_distribution: dict[str, float]
    reference_distribution: dict[str, float]
    tvd: float = Field(description="Total Variation Distance (0-1)")
    per_option_deltas: dict[str, float] = Field(
        description="Absolute deviation per option for transparency"
    )


class CalibrationReport(BaseModel):
    """Full calibration report: all questions + aggregate score."""

    pack_name: str
    num_personas: int
    num_questions: int
    results: list[CalibrationResult]
    overall_tvd: float = Field(description="Mean TVD across all questions")
    calibration_score: float = Field(description="1 - mean(TVD), reported as 0-100 percentage")
    mock_mode: bool = Field(description="Whether MARKET_SWARM_MOCK was enabled")
    disclaimer: str = Field(
        default=(
            "Calibration compares answer distributions, not individuals. "
            "Simulated populations are hypothesis generators for testing persona realism — "
            "see docs/validation.md for limitations and how to contribute better reference sets."
        )
    )


def load_question_set(path: str) -> list[CalibrationQuestion]:
    """Load and validate a calibration question set from YAML file.

    Args:
        path: Path to calibration YAML file.

    Returns:
        List of validated CalibrationQuestion objects.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML is malformed or fails Pydantic validation.
    """
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Calibration question file not found: {path}")

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if "questions" not in data:
        raise ValueError("YAML must contain a 'questions' key")

    questions = []
    for q_data in data["questions"]:
        question = CalibrationQuestion(**q_data)
        questions.append(question)

    logger.info(f"Loaded {len(questions)} calibration questions from {path}")
    return questions


def _total_variation_distance(simulated: dict[str, float], reference: dict[str, float]) -> float:
    """Compute Total Variation Distance between two distributions.

    TVD = 0.5 * sum(|P(x) - Q(x)|) for all x in support.
    Range: 0 (identical) to 1 (disjoint).

    Args:
        simulated: Simulated distribution (option -> count/proportion).
        reference: Reference distribution (option -> proportion).

    Returns:
        TVD as float between 0 and 1.
    """
    # Normalize simulated to proportions if needed
    sim_total = sum(simulated.values())
    if sim_total == 0:
        return 1.0  # No responses = max distance

    sim_norm = {k: v / sim_total for k, v in simulated.items()}

    # Ensure both dicts have same keys
    all_keys = set(sim_norm.keys()) | set(reference.keys())
    sim_vals = [sim_norm.get(k, 0.0) for k in sorted(all_keys)]
    ref_vals = [reference.get(k, 0.0) for k in sorted(all_keys)]

    tvd = 0.5 * sum(abs(s - r) for s, r in zip(sim_vals, ref_vals))
    return tvd


def _mock_answer(
    persona_name: str, question_id: str, options: list[str], reference: dict[str, float]
) -> str:
    """Generate a deterministic mock answer weighted toward reference distribution.

    Used in MARKET_SWARM_MOCK mode: blends 70% reference + 30% uniform
    to create realistic-looking but imperfect demo output.

    Args:
        persona_name: Name of persona answering.
        question_id: ID of calibration question.
        options: List of available options.
        reference: Reference distribution for this question.

    Returns:
        One of the options.
    """
    seed = hash(f"{persona_name}:{question_id}") % (2**31)
    rng = random.Random(seed)

    # 70% chance of picking from reference distribution, 30% uniform
    if rng.random() < 0.70:
        # Sample from reference distribution
        choices = list(reference.keys())
        weights = [reference.get(c, 0.0) for c in choices]
        return rng.choices(choices, weights=weights, k=1)[0]
    else:
        # Uniform random choice
        return rng.choice(options)


def run_calibration(
    personas_or_pack: str | list,
    questions: list[CalibrationQuestion],
    model: str = DEFAULT_MODEL,
) -> CalibrationReport:
    """Run calibration: have personas answer questions, score vs reference.

    Args:
        personas_or_pack: Either a pack name (str) to load personas,
                         or a list of PersonaDefinition objects.
        questions: List of CalibrationQuestion objects.
        model: LLM model to use for persona responses.

    Returns:
        CalibrationReport with TVD scores and overall calibration score.
    """
    # Resolve personas
    if isinstance(personas_or_pack, str):
        pack = get_pack(personas_or_pack)
        personas = pack.personas
        pack_name = pack.display_name
    else:
        personas = personas_or_pack
        pack_name = f"custom ({len(personas)} personas)"

    num_personas = len(personas)
    num_questions = len(questions)

    console.print(
        f"\n[cyan]Calibration Harness[/cyan] — {pack_name} "
        f"({num_personas} personas × {num_questions} questions)"
    )
    if mock_enabled():
        console.print("[yellow]MOCK mode enabled[/yellow] (deterministic seeded responses)")
    console.print()

    # Collect responses: question_id -> [choices]
    responses_by_question: dict[str, list[str]] = {q.id: [] for q in questions}

    for persona_idx, persona in enumerate(personas, 1):
        console.print(
            f"  [{persona_idx}/{num_personas}] {persona.name}...", end=" ", highlight=False
        )

        for question in questions:
            # Randomize option order for each persona (seeded for reproducibility)
            options_shuffled = question.options.copy()
            shuffle_seed = hash(f"{persona.name}:{question.id}:shuffle") % (2**31)
            random.Random(shuffle_seed).shuffle(options_shuffled)

            if mock_enabled():
                choice = _mock_answer(
                    persona.name, question.id, options_shuffled, question.reference
                )
            else:
                # Real LLM call (synchronous)
                prompt = (
                    f"Answer this question with a JSON object. Choose exactly ONE option.\n\n"
                    f"Question: {question.question}\n\n"
                    f"Options:\n"
                )
                for i, opt in enumerate(options_shuffled, 1):
                    prompt += f"{i}. {opt}\n"

                prompt += (
                    '\nRespond with valid JSON: {"choice": "<option_text>"}\n'
                    "Choose the option that best matches your perspective."
                )

                try:
                    backend, client = _get_client()

                    if backend == "anthropic":
                        response = client.messages.create(
                            model=model,
                            max_tokens=256,
                            system=persona.to_system_message(),
                            messages=[{"role": "user", "content": prompt}],
                        )
                        text = response.content[0].text
                    else:
                        # OpenAI-compatible API
                        response = client.chat.completions.create(
                            model=model,
                            max_tokens=256,
                            messages=[
                                {"role": "system", "content": persona.to_system_message()},
                                {"role": "user", "content": prompt},
                            ],
                        )
                        text = response.choices[0].message.content

                    data = _parse_llm_response(text)
                    choice = data.get("choice", options_shuffled[0])

                    # Validate choice is in original (unshuffled) options
                    if choice not in question.options:
                        choice = question.options[0]

                except Exception as e:
                    logger.warning(f"Failed to get response for {persona.name}: {e}")
                    choice = question.options[0]  # Fallback

            responses_by_question[question.id].append(choice)

        console.print("✓")

    # Score each question
    results = []
    tvds = []

    for question in questions:
        choices = responses_by_question[question.id]

        # Build simulated distribution
        simulated_dist = {}
        for option in question.options:
            count = choices.count(option)
            simulated_dist[option] = count / num_personas if num_personas > 0 else 0.0

        # Compute TVD
        tvd = _total_variation_distance(simulated_dist, question.reference)
        tvds.append(tvd)

        # Per-option deltas for transparency
        per_option_deltas = {
            opt: abs(simulated_dist.get(opt, 0.0) - question.reference.get(opt, 0.0))
            for opt in set(simulated_dist.keys()) | set(question.reference.keys())
        }

        result = CalibrationResult(
            question_id=question.id,
            question=question.question,
            simulated_distribution=simulated_dist,
            reference_distribution=question.reference,
            tvd=tvd,
            per_option_deltas=per_option_deltas,
        )
        results.append(result)

    # Aggregate
    mean_tvd = sum(tvds) / len(tvds) if tvds else 0.0
    calibration_score = (1.0 - mean_tvd) * 100

    report = CalibrationReport(
        pack_name=pack_name,
        num_personas=num_personas,
        num_questions=num_questions,
        results=results,
        overall_tvd=mean_tvd,
        calibration_score=calibration_score,
        mock_mode=mock_enabled(),
    )

    return report


def print_calibration_report(report: CalibrationReport) -> None:
    """Pretty-print calibration report with Rich tables."""
    console.print()

    # Header
    header_text = (
        f"[bold]Calibration Results[/bold]\n"
        f"Pack: {report.pack_name} | "
        f"Personas: {report.num_personas} | "
        f"Questions: {report.num_questions}\n"
        f"Calibration Score: [bold cyan]{report.calibration_score:.1f}%[/bold cyan] "
        f"(Mean TVD: {report.overall_tvd:.3f})"
    )
    if report.mock_mode:
        header_text += "\n[yellow]Note: MOCK mode — deterministic seeded responses[/yellow]"

    console.print(header_text)
    console.print()

    # Per-question table
    table = Table(title="Per-Question Results")
    table.add_column("Question", style="cyan")
    table.add_column("TVD", justify="right")
    table.add_column("Sample Distribution")

    for result in report.results:
        # Format simulated dist as "option: 40%"
        dist_str = ", ".join(
            f"{opt[:15]}: {pct:.0%}" for opt, pct in result.simulated_distribution.items()
        )

        tvd_color = "green" if result.tvd < 0.15 else "yellow" if result.tvd < 0.25 else "red"
        table.add_row(
            result.question,
            f"[{tvd_color}]{result.tvd:.3f}[/{tvd_color}]",
            dist_str,
        )

    console.print(table)
    console.print()

    # Detailed per-question breakdown (opt-in: only for high-TVD questions)
    high_tvd_results = [r for r in report.results if r.tvd >= 0.15]
    if high_tvd_results:
        console.print("[bold]High-TVD Questions (≥0.15) — Worth investigating:[/bold]\n")
        for result in high_tvd_results:
            console.print(f"[cyan]{result.question_id}:[/cyan] {result.question}")
            detail_table = Table(show_header=True, header_style="bold")
            detail_table.add_column("Option", style="dim")
            detail_table.add_column("Simulated", justify="right")
            detail_table.add_column("Reference", justify="right")
            detail_table.add_column("Δ", justify="right")

            for opt in result.reference_distribution.keys():
                sim = result.simulated_distribution.get(opt, 0.0)
                ref = result.reference_distribution.get(opt, 0.0)
                delta = result.per_option_deltas.get(opt, 0.0)

                detail_table.add_row(
                    opt,
                    f"{sim:.1%}",
                    f"{ref:.1%}",
                    f"{delta:+.1%}",
                )

            console.print(detail_table)
            console.print()

    # Disclaimer
    console.print(f"[dim]{report.disclaimer}[/dim]")


def export_calibration_json(report: CalibrationReport, output_path: str) -> None:
    """Export calibration report to JSON file."""
    with open(output_path, "w") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
    logger.info(f"Calibration report exported to {output_path}")
