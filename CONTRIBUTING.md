# Contributing to Market Swarm

Market Swarm improves when its personas are sharper and its validation is stronger. We welcome three types of contributions: **new personas**, **new industry packs**, and **real validation results**. Code contributions follow the rules in [`CLAUDE.md`](CLAUDE.md).

## Development setup

```bash
# Clone and create venv
git clone https://github.com/rockywuest/market-swarm.git
cd market-swarm
python3 -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Verify setup
MARKET_SWARM_MOCK=1 python -m market_swarm simulate --product examples/oat-bar-protein.yaml
```

### Code quality

After every file change, run:

```bash
ruff check .
ruff format .
pytest
```

We use Python 3.11+, Pydantic v2 (strict mode), and type hints on all public functions.

## Contributing: new personas

A persona is a YAML file in `market_swarm/industry_packs/<pack>/personas/`.

**Quality bar:**
- **Name:** fictional only (generate with `names.io`, never use real people)
- **Employer:** archetype only (e.g. "a leading hard-discount chain"), never real company names
- **System prompt:** 150–300 words with **numbered priorities** and **concrete thresholds**
  - Include specific metrics, margin floors, KPIs or decision gates where applicable
  - Give the persona a distinct voice (e.g. risk-averse vs. growth-focused)
- **Evaluation criteria:** 3–5 snake_case criteria that match the priorities

**Example:**

```yaml
name: "Petra Schneider"
type: discount_buyer
retailer: "a leading hard-discount chain in northern Europe"
system_prompt: |
  You are Petra Schneider, category manager for snack bars at a leading hard-discount chain.
  You manage 240 SKUs, two planograms (end-cap and shelf), and a tight margin floor of 28%.

  Your decision priorities (in this order):
  1. Margin preservation: new items must hit ≥28% gross margin or you reject them outright
  2. Shelf productivity: items must generate €45–65 per linear meter per week (category average: €52)
  3. Cannibalization risk: new items cannot cannibalize >8% from existing protein-bar SKUs
  4. Promotional loading: prefer items that sell 30%+ of volume at full RRP (no heavy discounting)
  5. Supply reliability: require 99.5% on-time delivery and 2-week minimum lead time

  Your suppliers are mostly European. You distrust premium positioning and ask: "Why does this cost
  45% more than our house brand?" You review quarterly sales reports and reject categories if
  repeat-purchase falls below 60% of trial.

  Respond in the simulation's requested output language. Be specific with numbers.

evaluation_criteria:
  - margin_floor
  - shelf_productivity
  - cannibalization_risk
  - promo_mechanics
  - supply_reliability
```

**Submission:** open a PR with your persona YAML. No code changes required — the registry discovers it automatically. Include:
- Which pack it belongs to
- Why this persona fills a gap (e.g. "eastern EU discount chains are underrepresented")
- Any trade-specific grounding (e.g. "based on interviews with 3 category managers")

## Contributing: new industry packs

A pack is a directory with pack metadata, Pydantic models, a prompt builder, and personas.

**Directory structure:**

```
market_swarm/industry_packs/<pack_name>/
  pack.yaml              # name, display_name, supported_product_types, version
  models.py              # Pydantic v2: attributes, pricing, competitor models
  prompt_builder.py      # build_evaluation_prompt(product, persona, language) + build_panel_info(product)
  personas/
    persona_1.yaml
    persona_2.yaml
    ...
```

**Quality bar:**
- Pack must have ≥8 personas covering different buyer roles (e.g. procurement, user, IT security for B2B)
- Personas must encode **real industry economics** (e.g. margin floors, capacity constraints, compliance requirements), not generic buyer archetypes
- `models.py` must define Pydantic v2 models for all product attributes your pack cares about
- `prompt_builder.py` must handle multi-language output (controlled by `product.language` field)
- Every persona must have ≥3 concrete thresholds in its system prompt

**Submission:** open an issue titled `[Pack Proposal] <industry>` with:
- Industry name and 3–5 example companies/personas
- Which personas you plan to build (roles, not names yet)
- Your domain expertise (work in this industry, interviews with buyers, etc.)
- References to public data sources (e.g. industry reports, regulatory requirements)

We'll discuss scope before you code.

## Contributing: validation results

**The most valuable contribution.** If you run Market Swarm against your own launches, share your findings.

**What we need:**
1. **Methodology:** How many launches? What's your success definition (listed/delisted, repeat-purchase rate, price acceptance)?
2. **Blinded product YAML:** Product definition from *pre-launch information* only, with brand/product names replaced by neutral placeholders
3. **Simulation output:** The `results.json` from your simulation (with API keys stripped)
4. **Actual outcome:** The real result (listed in channels X and Y, repeat-purchase 45%, etc.)
5. **Comparison:** Which objections did the simulation flag that matched trade feedback? Which did it miss?

**Submission:** open a PR adding your results to [`docs/validation.md`](docs/validation.md) under a new section:

```markdown
### Case study: [Your company / anonymized]

- **Product:** [Anonymized category, e.g. "Plant-based protein bar"]
- **Launch date:** YYYY-MM
- **Outcome:** Listed in 2/3 channels, repeat-purchase 52%
- **Simulated prediction:** Would-list rate 2/3 (match), top objection was margin pressure (match)
- **Methodology note:** [Link to your blinded YAML, or describe your setup]
- **Contributor:** [@yourname](https://github.com/yourname)
```

Negative results are equally valuable — they tell us where personas need recalibration.

## Pull request checklist

Before submitting:

- [ ] Tests pass: `pytest`
- [ ] Code is clean: `ruff check .` and `ruff format .`
- [ ] No real company or real person names in personas/examples
- [ ] All text is English (simulation output language is set in product YAML)
- [ ] Documentation updated (e.g. `QUICKREF.md` if you added a CLI flag)
- [ ] Commit message explains *why*, not just what

## License

By submitting a contribution, you agree that your work will be licensed under the MIT License (see [`LICENSE`](LICENSE)).

## Questions?

Open a [GitHub Discussion](https://github.com/rockywuest/market-swarm/discussions) for setup questions, persona design advice, or validation methodology. Issues are for bugs and feature requests.
