# Personas-DE: Census-Grounded German Consumer Personas

**Version:** 0.1  
**Released:** 2026-07-19  
**License:** CC-BY-4.0 (generated personas); MIT (code)  
**Language:** Persona narratives are in German; documentation is in English.

## Motivation: The EU Data Gap

NVIDIA's [Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA) is the standard for demographically grounded synthetic personas—sampling from joint US Census distributions to ensure realism at scale. However, **no equivalent open dataset exists for Germany or the broader EU**, limiting AI applications to:

- Generic US-centric personas
- Ad-hoc synthetic personas without demographic grounding
- Real customer data (privacy issues, licensing)

**Personas-DE** fills this gap: the first open dataset of census-grounded synthetic German consumer personas, generated algorithmically from published aggregate statistics.

## Methodology

### Stage 1: Demographic Record Sampling (Pure Python)

For each persona, we sample a joint demographic record across:

| Field | Values | Source | Notes |
|-------|--------|--------|-------|
| **age_band** | 18–29, 30–49, 50–64, 65+ | Destatis Zensus 2022 (adult projection) | ~16%, 31%, 27%, 26% |
| **gender** | female, male | Destatis Bevölkerungsstand 2023 | 50.7% / 49.3% |
| **bundesland** | DE_NRW, DE_BY, DE_BW, ... (16 states) | Destatis Statistisches Bundesamt 2023 | NRW 21.5%, BY 15.9%, ... |
| **household_size** | 1–8 persons | Mikrozensus 2022 | 1p: 41%, 2p: 33%, 3p: 12%, 4p: 10%, 5+: 4% |
| **education** | low, medium, high (ISCED) | Mikrozensus 2022 (25–64 cohort) | 13% / 55% / 32% |
| **net_household_income** | <1500, 1500–2500, 2500–4000, >4000 EUR/month | Mikrozensus 2022 | Approximate midpoints; 12%, 25%, 38%, 25% |
| **occupation_status** | employed, self-employed, retired, student, not-employed | Destatis Arbeitsmarkt 2023 & Mikrozensus | Age-conditioned; e.g., 75% retired for 65+ |
| **grocery_channel** | hard discounter, supermarket, specialty/local, online | Eurostat HBS 2023 | 35%, 50%, 10%, 5% |
| **organic_frequency** | regularly, sometimes, rarely, never | Eurobarometer 97.4 (2022) | 15%, 25%, 30%, 30% |
| **price_vs_quality** | price-priority, balanced, quality-priority, brand-priority | ALLBUS 2022 (German social survey) | 25%, 45%, 22%, 8% |
| **online_grocery** | regularly, occasionally, planning, not-planning | Eurostat ISS 2024 | 10%, 20%, 15%, 55% |

**Key design decisions:**

1. **Marginals from aggregates, not individuals**: All reference distributions are published marginal shares from Destatis, Mikrozensus, Eurostat, etc. **No individual records were sampled or reconstructed.** This respects privacy.

2. **Modeled correlations (v0.1), not measured**: Income is lightly conditioned on education; occupation status is age-conditioned. These conditionals are **modeled approximations** (documented probability tables in `personas_de.py`), not measured from joint tables. Future versions will use Iterative Proportional Fitting (IPF) on GENESIS joint tables for higher fidelity.

3. **Consumer dimensions independent (v0.1)**: Grocery channel, organic frequency, price orientation, and online usage are sampled independently. In reality, these are correlated (high-income ↔ organic, online; price-conscious ↔ discounter). v0.2 will add realistic copula structure.

4. **Deterministic seed**: Given a random seed, record sampling is **fully reproducible**—all personas with the same seed will be identical.

### Stage 2: Narrative Generation (Async LLM)

For each demographic record, an LLM generates a ~120–180-word German first-person narrative:

**Prompt structure:**
```
System: "Du bist ein deutscher Verbraucher-Persona-Generator. Schreibe authentische Erzählungen..."

User:
- Alter: 30–49 Jahre
- Geschlecht: weiblich
- Bundesland: Bayern
- Haushaltsgröße: 2 Personen
- Schulabschluss: Hochschulabschluss
- Haushaltseinkommen: 2500–4000 EUR/month
- Berufsstatus: angestellt
- ...consumer dimensions...

Write a 120–180-word German self-description (first person).
No brand names. No real person names.
```

**Constraints enforced in prompt:**
- No real brand names (e.g., "Aldi", "Rewe")
- No surnames of public figures
- Claims must be derivable from demographic record
- German language (all narratives)

**Mock mode**: Deterministic German templates (no LLM call) for testing and CI.

### Output Format

**JSONL** (`personas_de_v0.1.jsonl`):  
One JSON object per line, one persona per line.

```json
{
  "age_band": "30-49",
  "gender": "female",
  "bundesland": "BY",
  "household_size": 2,
  "education": "high",
  "net_household_income_band": "2500_4000",
  "occupation_status": "employed",
  "grocery_channel_preference": "full_range_supermarket",
  "organic_purchase_frequency": "sometimes",
  "price_vs_quality_orientation": "balanced",
  "online_grocery_usage": "occasionally",
  "persona_text": "Ich bin eine 35-jährige Betriebswirtin in München. Ich lebe mit meinem Partner in einer..."
}
```

**Stats sidecar** (`personas_de_v0.1.stats.json`):  
Marginal validation report + generation metadata.

```json
{
  "metadata": {
    "count": 1000,
    "version": "0.1",
    "model": "claude-opus-4-8",
    "generated_at": "2026-07-19T14:23:00",
    "seed": 42,
    "mock_mode": false
  },
  "marginal_validation": {
    "age_band": {
      "max_delta": 0.018,
      "per_option_deltas": {"18-29": 0.008, "30-49": 0.012, ...}
    },
    ...
  },
  "summary": {
    "max_deviation_any_field": 0.042,
    "avg_deviation": 0.015
  }
}
```

## Validation & Limitations

### Marginal Validation

For each demographic field, we report:
- **Reference share**: Published aggregate proportion
- **Generated share**: Observed proportion in the sample
- **Max delta**: Largest absolute deviation (any option)

**Example (100-persona run):**
```
Field: age_band
  18-29:   Reference 16% → Generated 18% (delta +2%)
  30-49:   Reference 31% → Generated 29% (delta -2%)
  50-64:   Reference 27% → Generated 27% (delta  0%)
  65+:     Reference 26% → Generated 26% (delta  0%)
  Max delta: 2%
```

**Acceptance threshold (v0.1):** Max delta < 5% for most fields. Larger deviations on rare options (e.g., "online_delivery" 5% → 7% in 100-person sample) are expected and acceptable.

### Known Limitations

1. **Modeled correlations, not measured**  
   Income↔education and occupation↔age are approximations. The true joint distribution is only available in restricted-access GENESIS tables. Roadmap: IPF on official joint tables (partner data agreement pending).

2. **Consumer dimensions independent**  
   Online grocery adoption, organic frequency, price orientation are sampled independently, but real consumers show strong correlations (e.g., high-income → organic → online). Roadmap: Copula structure estimated from Eurostat/Eurobarometer microdata.

3. **v0.1 narratives are LLM interpretations**  
   While grounded in record fields, narratives are not factual consumer statements—they are plausible synthetic stories. Personas should never be treated as actual consumer data.

4. **No urbanicity / regional heterogeneity**  
   Bundesland distribution is included, but urban/rural split within states is not. Regional consumer behavior (e.g., organic uptake 35% in Baden-Württemberg vs 8% in Bulgaria) is flattened to EU averages in consumer dimensions. Roadmap: Stratify consumer dimensions by region.

5. **No temporal dynamics**  
   Snapshot distribution (2022–2024). No cohort aging, job transitions, or consumer behavior drift over time.

6. **Persona narratives are German by design**  
   This is intentional—the dataset simulates German consumers. Translating narratives to other languages would lose cultural nuance and introduce compounding errors. Use the demographic record fields for multilingual simulation.

## Usage

### Generation

Generate 1000 personas with seed 42 (deterministic):

```bash
python -m market_swarm generate-personas-de --n 1000 --seed 42
```

Output: `data/personas-de/personas_de_v0.1.jsonl` + `personas_de_v0.1.stats.json`

**CLI options:**
```
--n N                 Number of personas (default: 100)
--seed SEED           Random seed (default: 42)
--model MODEL         LLM model (default: claude-opus-4-8)
--output DIR          Output directory (default: data/personas-de/)
--generated-at ISO    Date (default: today, ISO 8601)
--max-concurrent N    Parallel LLM calls (default: 5)
```

### Loading in Simulations

Use personas-de as a population source:

```bash
python -m market_swarm simulate \
  --product examples/oat-bar-protein.yaml \
  --population personas-de:100 \
  --population-only
```

In Python:
```python
from market_swarm.population import load_population

personas = load_population("personas-de", 100, seed=42)
# Returns list of PersonaDefinition objects
```

### Mock Mode (for testing)

```bash
MARKET_SWARM_MOCK=1 python -m market_swarm generate-personas-de --n 50 --seed 42
```

Produces deterministic mock narratives without calling any LLM. Fast and free for CI.

## Data Quality & Reproducibility

### Seeding & Reproducibility

All generation is **fully reproducible** with a seed:

```python
personas1 = load_population("personas-de", 100, seed=42)
personas2 = load_population("personas-de", 100, seed=42)
# personas1 == personas2 (bitwise)
```

### Validation Report Interpretation

The stats sidecar shows marginal deviance. Example interpretation:

```
max_deviation_any_field: 0.035 (3.5%)
avg_deviation: 0.012 (1.2%)
```

This is **excellent** — marginal distributions match published statistics within 3.5%. Note:
- Smaller samples show larger statistical variance (law of large numbers).
- 100 personas: expect ±5% deviation
- 1000 personas: expect ±1–2% deviation
- 10,000 personas: expect <1% deviation

## Roadmap

### v0.2 (Q3 2026)
- [ ] IPF on Destatis GENESIS joint tables (age × education × income × occupation)
- [ ] Copula structure for consumer dimensions (correlation matrix from Eurostat)
- [ ] Regional stratification: urbanicity split within Bundesländer
- [ ] Validation against holdout Mikrozensus microdata

### v0.3 (Q4 2026)
- [ ] Multi-country: DE, AT, CH, NL, FR, UK personas (EU-wide survey data)
- [ ] Demographic subsetting: e.g., "generate only 18–35, high-income, urban personas"
- [ ] Household composition: couple vs single parent vs multi-generational
- [ ] Language variants: German personas with English narratives option

### v1.0 (Q1 2027)
- [ ] Longitudinal: persona lifecycle (age progression, income change)
- [ ] Integration with EVS (European Values Study) for lifestyle segmentation
- [ ] Open-source release under CC-BY-4.0 on Hugging Face Hub
- [ ] Research paper: validation against real consumer survey data

## License & Attribution

**Code**: MIT (same as Market Swarm)  
**Generated personas**: CC-BY-4.0

If you use Personas-DE in research or production, please cite:

```
Market Swarm Contributors (2026). Personas-DE: Census-Grounded German Consumer Personas. 
Version 0.1. Generated 2026-07-19. CC-BY-4.0.
https://github.com/market-swarm/market-swarm/tree/main/data/personas-de/
```

Data sources:
- Destatis (Statistisches Bundesamt): Zensus 2022, Mikrozensus, Arbeitsmarktstatistik
- Eurostat: Household Budget Survey (HBS), Information Society Statistics (ISS)
- Eurobarometer 97.4 (April 2022): Organic food consumption
- ALLBUS 2022: German General Social Survey

## Contributing

Improvements welcome:
- [ ] Better reference distributions (e.g., joint table access)
- [ ] Regional consumer behavior data (e.g., per-Bundesland organic uptake)
- [ ] Validation against real survey data
- [ ] Non-German locales (Austria, Switzerland, France, ...)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for process.

## Contact

Questions about methodology or data? Open an issue or email [maintainers].

---

**Disclaimer**: Personas-DE generates plausible synthetic consumer stories for market simulation. Narratives are LLM-generated interpretations of demographic records and should never be treated as factual consumer statements or real people. Use for product testing, scenario analysis, and research only.

## v0.1 Calibration Results (measured, not claimed)

Release calibration run (2026-07-19): 200 sampled personas × 8 questions
from `data/calibration/consumer_basics_eu.yaml`, 1,600 LLM calls, 19
unparsable answers skipped. Full report:
`data/personas-de/calibration_v0.1.json`. (An n=100 pre-run scored 78.6% —
the result is stable across sample sizes.)

**Calibration Score: 79.8%** (100 × (1 − mean TVD))

| Question | TVD | Reading |
|---|---|---|
| Grocery channel preference | 0.080 | ✅ strong — dimension is conditioned in the sampler |
| Organic purchase frequency | 0.078 | ✅ strong — conditioned |
| Sustainable label influence | 0.110 | good |
| Online grocery adoption | 0.125 | good |
| Price vs quality priority | 0.170 | fair |
| Smoking status | 0.245 | fair — not conditioned |
| Household food budget share | 0.302 | weak — needs EVS-based conditioning (roadmap) |
| Preferred product information | 0.503 | ❌ weak — LLM attitude bias, not demographic |

The pattern is exactly what the methodology predicts: dimensions explicitly
grounded in the demographic records track reality well; free attitudes
inherit LLM training-data bias. v0.2 priorities follow directly from the
weakest rows — EVS spending conditioning and attitude grounding via
ALLBUS-derived priors.

Marginal fidelity of the released 1,000-persona set vs. official reference
distributions: max deviation **4.3%**, average **2.1%** (see
`personas_de_v0.1.stats.json`).
