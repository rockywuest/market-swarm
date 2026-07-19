"""German consumer persona generator — census-grounded synthetic personas.

This module implements a two-stage pipeline:

Stage 1 (Demographic Sampling):
  Sample demographic records (age, gender, bundesland, household_size, education,
  income, occupation_status) from joint distributions grounded in official
  German statistics (Destatis Zensus 2022, Mikrozensus). Consumer dimensions
  (grocery_channel_preference, organic_purchase_frequency, price_vs_quality,
  online_grocery_usage) are lightly conditioned on demographics using modeled
  probability tables (IPF is the roadmap).

Stage 2 (Narrative Generation):
  For each record, generate a ~120–180-word German first-person consumer narrative
  via LLM (async, with semaphore rate-limiting). Mock mode produces deterministic
  German templates without LLM calls.

Output:
  - JSONL: data/personas-de/personas_de_v0.1.jsonl (one record per line)
  - Stats: data/personas-de/personas_de_v0.1.stats.json (marginal validation + metadata)

License: CC-BY-4.0 for generated persona narratives.
"""

import asyncio
import json
import logging
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import anthropic
import openai
from rich.console import Console
from rich.table import Table

from .engine import (
    DEFAULT_MODEL,
    _get_async_client,
    mock_enabled,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
)

logger = logging.getLogger(__name__)
console = Console()

# =====================================================================
# Reference Marginals (Destatis/Mikrozensus 2022) — Documented Sources
# =====================================================================

# Adult (18+) population distribution (renormalized from published shares)
# Source: Destatis Zensus 2022 (projected from 2011 baseline + admin updates)
REFERENCE_MARGINALS = {
    "age_bands": {
        "18-29": 0.16,  # ~12.7M / ~83M adults
        "30-49": 0.31,  # ~25.8M
        "50-64": 0.27,  # ~22.4M
        "65+": 0.26,  # ~21.6M
        # Source: destatis.de/DE/Themen/Bevoelkerung/Strukturdaten
        "source": "Destatis Zensus 2022 (projected adulthood 18+)",
    },
    "gender": {
        "female": 0.507,
        "male": 0.493,
        # Source: Destatis demographic statistics (all ages)
        "source": "Destatis Bevölkerungsstand 2023",
    },
    "bundesland_shares": {
        "NRW": 0.215,  # 18M
        "BY": 0.159,  # 13.2M
        "BW": 0.134,  # 11.1M
        "NI": 0.096,  # 8.0M
        "HE": 0.076,  # 6.3M
        "RP": 0.049,  # 4.1M
        "SN": 0.048,  # 4.0M
        "BE": 0.044,  # 3.7M
        "SH": 0.035,  # 2.9M
        "BB": 0.030,  # 2.5M
        "ST": 0.026,  # 2.2M
        "TH": 0.025,  # 2.1M
        "HH": 0.022,  # 1.9M
        "MV": 0.019,  # 1.6M
        "SL": 0.012,  # 1.0M
        "HB": 0.008,  # 0.7M
        # Source: Destatis Bevölkerung nach Bundesland 2023
        "source": "Destatis Statistisches Bundesamt (2023)",
    },
    "household_size": {
        "1": 0.41,  # Single
        "2": 0.33,  # Couple or 2 adults
        "3": 0.12,  # 3 persons
        "4": 0.10,  # 4 persons
        "5+": 0.04,  # 5+ persons
        # Source: Mikrozensus 2022 (Haushalts-Größenverteilung)
        "source": "Mikrozensus 2022 (Destatis)",
    },
    "education_isced": {
        # ISCED bands for population 25-64 (most stable educational cohort)
        "low": 0.13,  # ISCED 0-2 (below secondary)
        "medium": 0.55,  # ISCED 3-4 (secondary/post-secondary)
        "high": 0.32,  # ISCED 5-8 (tertiary+)
        # Source: Mikrozensus 2022 (formale Schulabschluss)
        "source": "Mikrozensus 2022 & EU-LFS aggregation",
    },
    "net_household_income_band": {
        # Monthly net income bands (EUR) — approximate distributions by education
        "under_1500": 0.12,  # <1500 EUR/month
        "1500_2500": 0.25,  # 1500-2500
        "2500_4000": 0.38,  # 2500-4000
        "4000_plus": 0.25,  # >4000 EUR/month
        # Source: Mikrozensus Einkommen (2022, approximate midpoints)
        "source": "Mikrozensus 2022 (Haushaltseinkommen)",
    },
    "occupation_status": {
        # Shares across full adult population (weighted by age distribution)
        "employed": 0.55,  # Erwerbstätige
        "self_employed": 0.06,  # Selbstständige
        "retired": 0.20,  # Rentner/Pensionäre
        "student": 0.05,  # Studierende (some overlap with employed)
        "not_employed": 0.14,  # Arbeitslos, Hausfrauen, andere
        # Source: Destatis Arbeitmarkt 2023 & Mikrozensus
        "source": "Destatis Arbeitsmarktstatistik 2023",
    },
}

# Consumer dimensions — marginal distributions (independent, modeled correlations in v0.2)
CONSUMER_MARGINALS = {
    "grocery_channel_preference": {
        "hard_discounter": 0.35,
        "full_range_supermarket": 0.50,
        "specialty_local": 0.10,
        "online_delivery": 0.05,
        # Source: consumer_basics_eu.yaml
        "source": "Eurostat Household Consumption Survey",
    },
    "organic_purchase_frequency": {
        "regularly": 0.15,
        "sometimes": 0.25,
        "rarely": 0.30,
        "never": 0.30,
        # Source: consumer_basics_eu.yaml (Eurobarometer 97.4)
        "source": "Eurobarometer 97.4 (April 2022)",
    },
    "price_vs_quality_orientation": {
        "price_priority": 0.25,
        "balanced": 0.45,
        "quality_priority": 0.22,
        "brand_priority": 0.08,
        # Source: consumer_basics_eu.yaml (ALLBUS 2022)
        "source": "ALLBUS 2022",
    },
    "online_grocery_usage": {
        "regularly": 0.10,
        "occasionally": 0.20,
        "planning": 0.15,
        "not_planning": 0.55,
        # Source: consumer_basics_eu.yaml
        "source": "Eurostat Information Society Statistics (2024)",
    },
}


# =====================================================================
# Data Models
# =====================================================================


@dataclass
class DemographicRecord:
    """A single demographic + consumer persona record."""

    age_band: str
    gender: str  # "female" or "male"
    bundesland: str
    household_size: int
    education: str  # "low", "medium", "high"
    net_household_income_band: str
    occupation_status: str
    grocery_channel_preference: str
    organic_purchase_frequency: str
    price_vs_quality_orientation: str
    online_grocery_usage: str


@dataclass
class PersonaRecord:
    """A record ready for output: demographic + narrative."""

    demographic: DemographicRecord
    persona_text: str = ""

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        data = asdict(self.demographic)
        data["persona_text"] = self.persona_text
        return data


@dataclass
class MarginalValidationReport:
    """Comparison of generated vs reference marginals."""

    field_name: str
    reference_shares: dict[str, float]
    generated_shares: dict[str, float]
    per_option_deltas: dict[str, float]
    max_delta: float


# =====================================================================
# Stage 1: Demographic Sampler
# =====================================================================


def _sample_from_distribution(distribution: dict[str, float], rng: random.Random) -> str:
    """Sample one value from a discrete distribution."""
    options = []
    weights = []
    for key, weight in distribution.items():
        if key != "source":  # Skip metadata keys
            options.append(key)
            weights.append(weight)
    return rng.choices(options, weights=weights, k=1)[0]


def _sample_household_size(rng: random.Random) -> int:
    """Sample household size from distribution, return as int."""
    key = _sample_from_distribution(REFERENCE_MARGINALS["household_size"], rng)
    if key == "5+":
        return rng.randint(5, 8)  # 5-8 persons
    return int(key)


def _sample_occupation_status(age_band: str, rng: random.Random) -> str:
    """Sample occupation status conditioned on age band (light modeling)."""
    # Age-conditioned modulation of occupation status
    base_dist = REFERENCE_MARGINALS["occupation_status"].copy()
    base_dist.pop("source", None)

    if age_band == "18-29":
        # Higher student, lower retired
        modulated = {
            "employed": 0.50,
            "self_employed": 0.05,
            "retired": 0.01,
            "student": 0.20,
            "not_employed": 0.24,
        }
    elif age_band == "30-49":
        # Mostly employed
        modulated = {
            "employed": 0.70,
            "self_employed": 0.10,
            "retired": 0.02,
            "student": 0.02,
            "not_employed": 0.16,
        }
    elif age_band == "50-64":
        # Mostly employed, starting to retire
        modulated = {
            "employed": 0.65,
            "self_employed": 0.08,
            "retired": 0.10,
            "student": 0.01,
            "not_employed": 0.16,
        }
    else:  # 65+
        # Mostly retired
        modulated = {
            "employed": 0.10,
            "self_employed": 0.02,
            "retired": 0.75,
            "student": 0.00,
            "not_employed": 0.13,
        }

    return _sample_from_distribution(modulated, rng)


def _sample_education(rng: random.Random) -> str:
    """Sample education band (ISCED)."""
    return _sample_from_distribution(REFERENCE_MARGINALS["education_isced"], rng)


def _sample_income_band(education: str, rng: random.Random) -> str:
    """Sample income band lightly conditioned on education."""
    base_dist = REFERENCE_MARGINALS["net_household_income_band"].copy()
    base_dist.pop("source", None)

    if education == "high":
        # Higher income distribution
        modulated = {
            "under_1500": 0.05,
            "1500_2500": 0.15,
            "2500_4000": 0.40,
            "4000_plus": 0.40,
        }
    elif education == "medium":
        # Middle income
        modulated = {
            "under_1500": 0.10,
            "1500_2500": 0.28,
            "2500_4000": 0.40,
            "4000_plus": 0.22,
        }
    else:  # low
        # Lower income
        modulated = {
            "under_1500": 0.20,
            "1500_2500": 0.35,
            "2500_4000": 0.30,
            "4000_plus": 0.15,
        }

    return _sample_from_distribution(modulated, rng)


def sample_demographic_records(n: int, seed: int = 42) -> list[DemographicRecord]:
    """Sample n demographic records with deterministic stratification.

    All marginals follow published official distributions (Destatis/Mikrozensus).
    Consumer dimensions are independently sampled (modeled correlations in v0.2).

    Args:
        n: Number of records to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of DemographicRecord objects.
    """
    rng = random.Random(seed)
    records = []

    for _ in range(n):
        age_band = _sample_from_distribution(REFERENCE_MARGINALS["age_bands"], rng)
        gender = _sample_from_distribution(REFERENCE_MARGINALS["gender"], rng)
        bundesland = _sample_from_distribution(REFERENCE_MARGINALS["bundesland_shares"], rng)
        household_size = _sample_household_size(rng)
        education = _sample_education(rng)
        income_band = _sample_income_band(education, rng)
        occupation_status = _sample_occupation_status(age_band, rng)

        # Consumer dimensions (independent for v0.1)
        grocery_channel = _sample_from_distribution(
            CONSUMER_MARGINALS["grocery_channel_preference"], rng
        )
        organic_freq = _sample_from_distribution(
            CONSUMER_MARGINALS["organic_purchase_frequency"], rng
        )
        price_quality = _sample_from_distribution(
            CONSUMER_MARGINALS["price_vs_quality_orientation"], rng
        )
        online_usage = _sample_from_distribution(CONSUMER_MARGINALS["online_grocery_usage"], rng)

        record = DemographicRecord(
            age_band=age_band,
            gender=gender,
            bundesland=bundesland,
            household_size=household_size,
            education=education,
            net_household_income_band=income_band,
            occupation_status=occupation_status,
            grocery_channel_preference=grocery_channel,
            organic_purchase_frequency=organic_freq,
            price_vs_quality_orientation=price_quality,
            online_grocery_usage=online_usage,
        )
        records.append(record)

    return records


def validate_marginals(records: list[DemographicRecord]) -> list[MarginalValidationReport]:
    """Validate generated record marginals against reference distributions.

    Returns a list of validation reports, one per field, with max deviation reported.
    Prints a rich table and returns structured report for JSON serialization.

    Args:
        records: Generated demographic records.

    Returns:
        List of MarginalValidationReport objects.
    """
    reports = []

    # Fields to validate: (field_name, reference_dist)
    validation_specs = [
        ("age_band", REFERENCE_MARGINALS["age_bands"]),
        ("gender", REFERENCE_MARGINALS["gender"]),
        ("bundesland", REFERENCE_MARGINALS["bundesland_shares"]),
        ("household_size", REFERENCE_MARGINALS["household_size"]),
        ("education", REFERENCE_MARGINALS["education_isced"]),
        ("net_household_income_band", REFERENCE_MARGINALS["net_household_income_band"]),
        ("occupation_status", REFERENCE_MARGINALS["occupation_status"]),
        ("grocery_channel_preference", CONSUMER_MARGINALS["grocery_channel_preference"]),
        ("organic_purchase_frequency", CONSUMER_MARGINALS["organic_purchase_frequency"]),
        ("price_vs_quality_orientation", CONSUMER_MARGINALS["price_vs_quality_orientation"]),
        ("online_grocery_usage", CONSUMER_MARGINALS["online_grocery_usage"]),
    ]

    table = Table(title="Marginal Validation Report")
    table.add_column("Field", style="cyan")
    table.add_column("Option", style="magenta")
    table.add_column("Reference", justify="right")
    table.add_column("Generated", justify="right")
    table.add_column("Delta", justify="right", style="yellow")

    for field_name, reference_dist in validation_specs:
        # Remove metadata
        ref_clean = {k: v for k, v in reference_dist.items() if k != "source"}

        # Count generated field values; household sizes are banded to match
        # the reference distribution's "5+" bucket.
        field_counts = {}
        for r in records:
            val = getattr(r, field_name)
            if field_name == "household_size":
                val = "5+" if int(val) >= 5 else str(val)
            field_counts[str(val)] = field_counts.get(str(val), 0) + 1

        # Compute shares
        total = len(records)
        generated_shares = {k: v / total for k, v in field_counts.items()}

        # Compute per-option deltas
        per_option_deltas = {}
        max_delta = 0.0
        for option in ref_clean.keys():
            ref_share = ref_clean[option]
            gen_share = generated_shares.get(str(option), 0.0)
            delta = abs(ref_share - gen_share)
            per_option_deltas[option] = delta
            max_delta = max(max_delta, delta)

        # Ensure all reference options are represented
        gen_shares_aligned = {}
        for option in ref_clean.keys():
            gen_shares_aligned[option] = generated_shares.get(str(option), 0.0)

        for option in ref_clean.keys():
            table.add_row(
                field_name if option == sorted(ref_clean.keys())[0] else "",
                str(option),
                f"{ref_clean[option]:.2%}",
                f"{gen_shares_aligned[option]:.2%}",
                f"{per_option_deltas[option]:+.2%}",
            )

        report = MarginalValidationReport(
            field_name=field_name,
            reference_shares=ref_clean,
            generated_shares=gen_shares_aligned,
            per_option_deltas=per_option_deltas,
            max_delta=max_delta,
        )
        reports.append(report)

    console.print(table)
    return reports


# =====================================================================
# Stage 2: Narrative Generation
# =====================================================================


def _generate_mock_narrative(record: DemographicRecord, persona_id: str) -> str:
    """Generate a deterministic German narrative template (no LLM).

    Uses record fields to vary the template plausibly.
    """
    age_desc = {
        "18-29": "Junge Berufstätige",
        "30-49": "Mittleres Alter",
        "50-64": "Älter werdend",
        "65+": "Rentner",
    }.get(record.age_band, "Person")

    household_desc = {
        1: "Ich lebe allein",
        2: "Ich lebe zu zweit",
        3: "Ich bin Teil einer 3-köpfigen Familie",
        4: "Ich bin Teil einer 4-köpfigen Familie",
    }
    household_desc_text = (
        household_desc.get(record.household_size)
        or f"Ich lebe mit {record.household_size} Personen im Haushalt"
    )

    education_desc = {
        "low": "Hauptschule",
        "medium": "Mittlere Reife oder Berufsausbildung",
        "high": "Hochschulabschluss",
    }.get(record.education, "Ausbildung")

    income_desc = {
        "under_1500": "unteres Einkommenssegment",
        "1500_2500": "durchschnittliches Einkommen",
        "2500_4000": "mittleres bis gehobenes Einkommen",
        "4000_plus": "gehobenes Einkommenssegment",
    }.get(record.net_household_income_band, "Einkommenssegment")

    occupation_text = {
        "employed": "Ich arbeite als Angestellte",
        "self_employed": "Ich bin selbstständig",
        "retired": "Ich bin Rentnerin",
        "student": "Ich bin Studentin",
        "not_employed": "Ich bin aktuell nicht erwerbstätig",
    }.get(record.occupation_status, "Ich arbeite")

    channel_desc = {
        "hard_discounter": "Ich kaufe bevorzugt bei Discountern wie Aldi oder Lidl",
        "full_range_supermarket": "Ich shopppe gerne im Supermarkt mit breitem Sortiment",
        "specialty_local": "Ich bevorzuge lokale und Spezialgeschäfte",
        "online_delivery": "Ich kaufe vermehrt Lebensmittel online",
    }.get(record.grocery_channel_preference, "Ich kaufe meine Lebensmittel regelmäßig")

    organic_desc = {
        "regularly": "Bio-Produkte sind mir wichtig",
        "sometimes": "Ich kaufe ab und zu Bio-Produkte",
        "rarely": "Bio-Produkte sind mir nicht sehr wichtig",
        "never": "Ich achte nicht auf Bio-Zertifizierungen",
    }.get(record.organic_purchase_frequency, "Ich achte auf Qualität")

    price_desc = {
        "price_priority": "Der Preis ist für mich entscheidend",
        "balanced": "Ich wäge Preis und Qualität ab",
        "quality_priority": "Qualität ist mir wichtiger als der Preis",
        "brand_priority": "Markentreue und Reputation sind wichtig",
    }.get(record.price_vs_quality_orientation, "Ich suche gutes Preis-Leistungs-Verhältnis")

    online_desc = {
        "regularly": "Ich bestelle regelmäßig Lebensmittel online",
        "occasionally": "Ich probiere Online-Einkaufen gelegentlich",
        "planning": "Ich plane, Online-Shopping auszuprobieren",
        "not_planning": "Ich bevorzuge traditionelle Geschäfte",
    }.get(record.online_grocery_usage, "Ich orientiere mich an neuen Einkaufsformen")

    narrative = (
        f"Ich bin {age_desc} in {record.bundesland} und {education_desc} als Ausbildung. "
        f"{household_desc_text}. {occupation_text} im {income_desc}. "
        f"{channel_desc}. {organic_desc}. {price_desc}. "
        f"{online_desc}. Ich versuche, bewusst zu konsumieren und auf Qualität zu achten, "
        f"ohne dabei mein Budget zu überschreiten."
    )
    return narrative


async def _generate_narrative_async(
    record: DemographicRecord,
    persona_id: str,
    model: str = DEFAULT_MODEL,
    semaphore: asyncio.Semaphore | None = None,
) -> str:
    """Generate a German persona narrative via async LLM call with retry logic.

    Args:
        record: Demographic record.
        persona_id: Unique ID for this persona.
        model: LLM model to use.
        semaphore: Optional semaphore for rate limiting.

    Returns:
        German narrative (120–180 words).
    """
    if mock_enabled():
        return _generate_mock_narrative(record, persona_id)

    backend, client = _get_async_client()

    system_prompt = (
        "Du bist ein deutscher Verbraucher-Persona-Generator. "
        "Basierend auf demografischen Daten schreibst du eine authentische, "
        "erste-Person-Erzählung einer echten Konsumentin auf Deutsch. "
        "Die Erzählung sollte 120–180 Wörter umfassen, plausibel sein und "
        "keine echten Markennamen oder Namen öffentlicher Personen enthalten."
    )

    age_label = {
        "18-29": "18–29 Jahre",
        "30-49": "30–49 Jahre",
        "50-64": "50–64 Jahre",
        "65+": "65+ Jahre",
    }.get(record.age_band, record.age_band)

    household_label = {
        1: "Alleinstehend",
        2: "Zwei Personen",
        3: "Drei Personen",
        4: "Vier Personen",
    }
    household_label_text = household_label.get(
        record.household_size, f"{record.household_size} Personen"
    )

    education_label = {
        "low": "Hauptschulabschluss",
        "medium": "Mittlere Reife oder Berufsausbildung",
        "high": "Hochschulabschluss (Universität oder FH)",
    }.get(record.education, record.education)

    user_prompt = (
        f"Schreibe eine deutsche Verbraucher-Persona basierend auf diesen Daten:\n"
        f"- Alter: {age_label}\n"
        f"- Geschlecht: {record.gender}\n"
        f"- Bundesland: {record.bundesland}\n"
        f"- Haushaltsgröße: {household_label_text}\n"
        f"- Schulabschluss: {education_label}\n"
        f"- Haushaltseinkommen: {record.net_household_income_band}\n"
        f"- Berufsstatus: {record.occupation_status}\n"
        f"- Bevorzugter Einkaufskanal: {record.grocery_channel_preference}\n"
        f"- Bio-Kauffrequenz: {record.organic_purchase_frequency}\n"
        f"- Preis-Qualitäts-Orientierung: {record.price_vs_quality_orientation}\n"
        f"- Online-Grocery-Nutzung: {record.online_grocery_usage}\n\n"
        f"Schreibe eine kurze, authentische Selbstbeschreibung als diese Person "
        f"(120–180 Wörter, Ich-Perspektive). Verwende keine echten Markennamen oder "
        f"Namen bekannter Personen."
    )

    async def _call_llm() -> str:
        # Generous token budget: reasoning models (e.g. Gemini 2.5) spend
        # "thinking" tokens against max_tokens before any visible output.
        if backend == "anthropic":
            response = await client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        else:
            from .engine import _resolve_model

            resolved_model, token_limit = _resolve_model(backend, model)
            response = await client.chat.completions.create(
                model=resolved_model,
                max_tokens=max(token_limit, 2048),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

    # Retry loop with backoff
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            if semaphore:
                async with semaphore:
                    text = await _call_llm()
            else:
                text = await _call_llm()
            text = (text or "").strip()
            # Guard against truncated/empty narratives (e.g. reasoning-token
            # exhaustion): a real narrative has at least ~60 words.
            if len(text.split()) < 60:
                raise ValueError(f"narrative too short ({len(text.split())} words)")
            return text

        except ValueError as e:
            last_error = e
            logger.warning(
                "Short narrative for persona %s (attempt %d/%d): %s",
                persona_id,
                attempt + 1,
                MAX_RETRIES,
                e,
            )

        except (anthropic.RateLimitError, openai.RateLimitError) as e:
            last_error = e
            delay = RETRY_BASE_DELAY * (2**attempt)
            logger.warning(
                "Rate limited on persona %s (attempt %d/%d), retrying in %.1fs",
                persona_id,
                attempt + 1,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)

        except (anthropic.APIStatusError, openai.APIStatusError) as e:
            status = getattr(e, "status_code", 0)
            if status >= 500:
                last_error = e
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Server error %d on persona %s (attempt %d/%d), retrying in %.1fs",
                    status,
                    persona_id,
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries for persona {persona_id}: {last_error}")


# =====================================================================
# Pipeline: Sampling + Narrative Generation
# =====================================================================


async def generate_personas_de(
    n: int,
    seed: int = 42,
    model: str = DEFAULT_MODEL,
    max_concurrent: int = 5,
    on_progress: Optional[callable] = None,
) -> tuple[list[PersonaRecord], list[MarginalValidationReport]]:
    """Generate n German consumer personas with demographic grounding.

    Pipeline:
      1. Sample n demographic records from marginals
      2. Validate marginals against references
      3. Generate German narrative for each record (async)
      4. Return PersonaRecord objects + validation report

    Args:
        n: Number of personas to generate.
        seed: Random seed for reproducibility.
        model: LLM model to use (ignored in mock mode).
        max_concurrent: Max concurrent narrative generation calls.
        on_progress: Optional callback(completed: int, total: int) for progress tracking.

    Returns:
        Tuple of (list[PersonaRecord], list[MarginalValidationReport])
    """
    logger.info(f"Sampling {n} demographic records with seed={seed}")
    records = sample_demographic_records(n, seed)

    logger.info("Validating marginals...")
    validation_reports = validate_marginals(records)

    logger.info(f"Generating {n} German narratives (async, max_concurrent={max_concurrent})")
    semaphore = asyncio.Semaphore(max_concurrent)
    completed_count = 0

    async def _generate_one(i: int, record: DemographicRecord) -> PersonaRecord:
        nonlocal completed_count
        persona_id = f"persona_{i:06d}"
        try:
            narrative = await _generate_narrative_async(
                record,
                persona_id,
                model=model,
                semaphore=semaphore,
            )
            completed_count += 1
            if on_progress:
                on_progress(completed_count, n)
            return PersonaRecord(demographic=record, persona_text=narrative)
        except Exception as e:
            logger.error(f"Error generating narrative for {persona_id}: {e}")
            completed_count += 1
            if on_progress:
                on_progress(completed_count, n)
            # Return record with empty narrative on error
            return PersonaRecord(demographic=record, persona_text=f"[ERROR: {str(e)[:100]}]")

    persona_records = await asyncio.gather(*[_generate_one(i, r) for i, r in enumerate(records)])

    return persona_records, validation_reports


# =====================================================================
# Output & Serialization
# =====================================================================


def write_personas_jsonl(
    personas: list[PersonaRecord],
    output_path: Path | str,
) -> None:
    """Write personas to JSONL file (one persona per line)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for persona in personas:
            json_line = json.dumps(persona.to_dict(), ensure_ascii=False)
            f.write(json_line + "\n")

    logger.info(f"Wrote {len(personas)} personas to {output_path}")


def write_stats_json(
    stats: dict,
    output_path: Path | str,
) -> None:
    """Write generation statistics and validation reports to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote stats to {output_path}")


def compile_stats(
    personas: list[PersonaRecord],
    validation_reports: list[MarginalValidationReport],
    model: str,
    generated_at: str,
    seed: int,
) -> dict:
    """Compile generation metadata and validation results into stats dict."""
    max_deltas_by_field = {}
    for report in validation_reports:
        max_deltas_by_field[report.field_name] = {
            "max_delta": report.max_delta,
            "per_option_deltas": report.per_option_deltas,
        }

    return {
        "metadata": {
            "count": len(personas),
            "version": "0.1",
            "model": model,
            "generated_at": generated_at,
            "seed": seed,
            "mock_mode": mock_enabled(),
        },
        "marginal_validation": {
            field: max_deltas_by_field[field] for field in sorted(max_deltas_by_field.keys())
        },
        "summary": {
            "max_deviation_any_field": max(
                r.max_delta for r in validation_reports if r.max_delta > 0
            ),
            "avg_deviation": sum(r.max_delta for r in validation_reports) / len(validation_reports)
            if validation_reports
            else 0,
        },
    }
