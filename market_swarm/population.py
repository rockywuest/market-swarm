"""Consumer population sources — load large persona datasets at runtime.

Supports both real and mock modes:
- Real: Load from open datasets (Nemotron, FinePersonas, generic HuggingFace)
- Mock: Generate deterministic varied personas without datasets library

The datasets library is optional; imports are lazy to allow graceful degradation.
"""

import os
import random

from .industry_packs.base import PersonaDefinition


def _validate_mock_mode() -> bool:
    """Check if mock mode is enabled."""
    return os.environ.get("MARKET_SWARM_MOCK", "").lower() in ("1", "true", "yes")


def _generate_mock_personas(n: int, seed: int = 42) -> list[PersonaDefinition]:
    """Generate deterministic, varied consumer personas for offline demos.

    Varies age bracket, household, price sensitivity, and health orientation
    across the swarm. Deterministic seed ensures reproducibility.

    Args:
        n: Number of personas to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of PersonaDefinition objects ready for simulation.
    """
    random.seed(seed)

    age_brackets = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
    household_types = ["single", "couple", "family with children", "multigenerational"]
    price_sensitivities = ["price-conscious", "value-focused", "premium-preferring"]
    health_orientations = [
        "health-conscious",
        "convenience-first",
        "eco-aware",
        "indulgent",
    ]
    occupations = [
        "software engineer",
        "teacher",
        "nurse",
        "retail manager",
        "student",
        "retired",
        "freelancer",
        "executive",
    ]

    personas = []
    for i in range(n):
        person_id = f"{i:04d}"
        age = random.choice(age_brackets)
        household = random.choice(household_types)
        price_sens = random.choice(price_sensitivities)
        health_orient = random.choice(health_orientations)
        occupation = random.choice(occupations)

        background = (
            f"Age {age}, {household} household. "
            f"Occupation: {occupation}. "
            f"Shopping style: {price_sens}. "
            f"Values: {health_orient}."
        )

        system_prompt = (
            "You are a consumer with this background:\n"
            f"{background}\n\n"
            "Evaluate the product strictly from this person's perspective — "
            "considering budget, habits, values, and lifestyle fit. "
            "You respond in the simulation's requested output language. "
            "Be direct and personal."
        )

        persona = PersonaDefinition(
            name=f"Consumer {person_id}",
            type="population_consumer",
            retailer=None,
            system_prompt=system_prompt,
            evaluation_criteria=[
                "purchase_intent",
                "price_acceptance",
                "brand_appeal",
                "fit_with_lifestyle",
            ],
        )
        personas.append(persona)

    return personas


def _load_nemotron_usa(n: int, seed: int = 42) -> list[PersonaDefinition]:
    """Load personas from NVIDIA Nemotron-Personas-USA dataset.

    Uses streaming + reservoir sampling to avoid downloading all 6M rows.
    Personas are grounded in real US Census joint demographic distributions.

    Args:
        n: Number of personas to sample.
        seed: Random seed for reproducibility.

    Returns:
        List of PersonaDefinition objects.

    Raises:
        ImportError: If datasets library is not installed.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise RuntimeError(
            "Population sources require the datasets library. "
            "Install with: pip install 'market-swarm[population]'"
        )

    random.seed(seed)

    # Load with streaming to avoid downloading full 6M rows
    ds = load_dataset("nvidia/Nemotron-Personas-USA", streaming=True, split="train")

    personas = []
    seen_count = 0
    # Reservoir sampling: iterate through dataset, keep n random items
    # This avoids loading all 6M rows into memory
    for record in ds:
        persona_text = record.get("persona", "")
        if not persona_text:
            continue

        seen_count += 1
        if len(personas) < n:
            personas.append(persona_text)
        else:
            # Random replacement: keep each existing item with probability n/seen_count
            j = random.randint(0, seen_count - 1)
            if j < n:
                personas[j] = persona_text

        # Early exit after seeing enough samples (with margin for randomness)
        if seen_count > n * 100:
            break

    # Convert persona texts to PersonaDefinition objects
    result = []
    for i, persona_text in enumerate(personas):
        system_prompt = (
            "You are a consumer with this background:\n"
            f"{persona_text}\n\n"
            "Evaluate the product strictly from this person's perspective — "
            "considering budget, habits, values, and lifestyle fit. "
            "You respond in the simulation's requested output language. "
            "Be direct and personal."
        )

        persona = PersonaDefinition(
            name=f"Consumer {i:04d}",
            type="population_consumer",
            retailer=None,
            system_prompt=system_prompt,
            evaluation_criteria=[
                "purchase_intent",
                "price_acceptance",
                "brand_appeal",
                "fit_with_lifestyle",
            ],
        )
        result.append(persona)

    return result


def _load_finepersonas(n: int, seed: int = 42) -> list[PersonaDefinition]:
    """Load personas from Argilla FinePersonas-v0.1 dataset.

    Args:
        n: Number of personas to sample.
        seed: Random seed for reproducibility.

    Returns:
        List of PersonaDefinition objects.

    Raises:
        ImportError: If datasets library is not installed.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise RuntimeError(
            "Population sources require the datasets library. "
            "Install with: pip install 'market-swarm[population]'"
        )

    random.seed(seed)

    # FinePersonas is smaller (~21M) but still large; use streaming
    ds = load_dataset("argilla/FinePersonas-v0.1", streaming=True, split="train")

    personas = []
    seen_count = 0
    for record in ds:
        persona_text = record.get("persona", "")
        if not persona_text:
            continue

        seen_count += 1
        if len(personas) < n:
            personas.append(persona_text)
        else:
            j = random.randint(0, seen_count - 1)
            if j < n:
                personas[j] = persona_text

        if seen_count > n * 100:
            break

    # Convert to PersonaDefinition
    result = []
    for i, persona_text in enumerate(personas):
        system_prompt = (
            "You are a consumer with this background:\n"
            f"{persona_text}\n\n"
            "Evaluate the product strictly from this person's perspective — "
            "considering budget, habits, values, and lifestyle fit. "
            "You respond in the simulation's requested output language. "
            "Be direct and personal."
        )

        persona = PersonaDefinition(
            name=f"Consumer {i:04d}",
            type="population_consumer",
            retailer=None,
            system_prompt=system_prompt,
            evaluation_criteria=[
                "purchase_intent",
                "price_acceptance",
                "brand_appeal",
                "fit_with_lifestyle",
            ],
        )
        result.append(persona)

    return result


def _load_hf_dataset(
    dataset_id: str, column: str, n: int, seed: int = 42
) -> list[PersonaDefinition]:
    """Load personas from a generic HuggingFace dataset.

    Args:
        dataset_id: HuggingFace dataset identifier (e.g., "owner/dataset-name").
        column: Column name containing persona text.
        n: Number of personas to sample.
        seed: Random seed for reproducibility.

    Returns:
        List of PersonaDefinition objects.

    Raises:
        ImportError: If datasets library is not installed.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise RuntimeError(
            "Population sources require the datasets library. "
            "Install with: pip install 'market-swarm[population]'"
        )

    random.seed(seed)

    ds = load_dataset(dataset_id, streaming=True, split="train")

    personas = []
    seen_count = 0
    for record in ds:
        persona_text = record.get(column, "")
        if not persona_text:
            continue

        seen_count += 1
        if len(personas) < n:
            personas.append(persona_text)
        else:
            j = random.randint(0, seen_count - 1)
            if j < n:
                personas[j] = persona_text

        if seen_count > n * 100:
            break

    # Convert to PersonaDefinition
    result = []
    for i, persona_text in enumerate(personas):
        system_prompt = (
            "You are a consumer with this background:\n"
            f"{persona_text}\n\n"
            "Evaluate the product strictly from this person's perspective — "
            "considering budget, habits, values, and lifestyle fit. "
            "You respond in the simulation's requested output language. "
            "Be direct and personal."
        )

        persona = PersonaDefinition(
            name=f"Consumer {i:04d}",
            type="population_consumer",
            retailer=None,
            system_prompt=system_prompt,
            evaluation_criteria=[
                "purchase_intent",
                "price_acceptance",
                "brand_appeal",
                "fit_with_lifestyle",
            ],
        )
        result.append(persona)

    return result


def load_population(source: str, n: int, seed: int = 42) -> list[PersonaDefinition]:
    """Load large open persona datasets and sample demographically.

    Supports:
    - "nemotron-usa" → NVIDIA Nemotron-Personas-USA (6M personas, US Census grounded)
    - "finepersonas" → Argilla FinePersonas-v0.1 (21M personas)
    - "hf:DATASET_ID:COLUMN" → Generic HuggingFace dataset loader

    In mock mode (MARKET_SWARM_MOCK=1), generates deterministic consumer personas
    without requiring the datasets library or network access.

    Args:
        source: Data source identifier.
        n: Number of personas to sample.
        seed: Random seed for reproducible sampling (default 42).

    Returns:
        List of PersonaDefinition objects ready for simulation.

    Raises:
        ValueError: If source format is invalid.
        RuntimeError: If datasets library is missing in non-mock mode.

    Examples:
        >>> personas = load_population("nemotron-usa", 100)
        >>> personas = load_population("finepersonas", 50, seed=123)
        >>> personas = load_population("hf:myorg/my-dataset:persona_col", 25)
        >>> # In mock mode: no downloads
        >>> os.environ["MARKET_SWARM_MOCK"] = "1"
        >>> personas = load_population("nemotron-usa", 100)  # Works without datasets lib
    """
    # Validate source format first, regardless of mock mode
    is_hf_source = source.startswith("hf:")
    is_known_source = source in ("nemotron-usa", "finepersonas") or is_hf_source

    if is_hf_source:
        # Validate hf: format
        parts = source.split(":", 2)
        if len(parts) != 3:
            raise ValueError("Invalid HuggingFace source format. Use: hf:dataset_id:column_name")
    elif not is_known_source:
        raise ValueError(
            f"Unknown population source: {source}. "
            f"Supported: nemotron-usa, finepersonas, hf:dataset_id:column"
        )

    if _validate_mock_mode():
        return _generate_mock_personas(n, seed)

    if source == "nemotron-usa":
        return _load_nemotron_usa(n, seed)
    elif source == "finepersonas":
        return _load_finepersonas(n, seed)
    elif is_hf_source:
        _, dataset_id, column = source.split(":", 2)
        return _load_hf_dataset(dataset_id, column, n, seed)
