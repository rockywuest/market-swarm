# Validation Methodology

Market Swarm generates **synthetic** market feedback. Synthetic feedback is only
useful if you know how well it tracks reality — so validation is a first-class
concern of this project, not an afterthought. This document describes how we
measure (and how you can measure) whether simulated personas predict anything.

## The honest starting point

As of v1.0.0, Market Swarm has **not** been validated against real launch
outcomes. Treat every simulation as a **hypothesis generator**: a fast, cheap
way to surface objections, pricing friction and channel differences *before*
you spend money on empirical research — never as a replacement for it.

This is deliberate positioning, not fine print. LLM-based persona simulation is
a young technique; published results on synthetic consumer research show
usable signal on *relative* comparisons (variant A vs. variant B, objection
ranking) and weak reliability on *absolute* predictions (exact purchase intent,
volume forecasts).

## What we expect simulation to be good at

| Signal | Expected reliability | Why |
|---|---|---|
| Objection discovery ("what will the trade push back on?") | High | LLMs reproduce domain reasoning patterns well |
| Relative ranking of product variants | Medium–high | Systematic biases cancel out across variants |
| Channel differences (discount vs. full-range vs. drugstore) | Medium | Archetype economics differ structurally |
| Price-point feedback (direction, not exact elasticity) | Medium | Trade margin math is deterministic |
| Absolute scores / purchase intent | Low | No grounding in real panel data |
| Volume forecasts | Not supported | Out of scope by design |

## Backtest design (planned, v1.x)

The validation harness will replay **historical launches with known outcomes**
through the simulation, blind:

1. **Case selection** — launches ≥12 months old with a documented outcome
   (listed/delisted, repeat-purchase performance, price acceptance).
2. **Blinding** — the product YAML is written from the *pre-launch* information
   state only. No outcome hints, no retrospective framing. Product and brand
   names are replaced with neutral placeholders so the LLM cannot recall
   real-world coverage of the launch.
3. **Prediction lock** — simulation output (would_list rate, top objections,
   channel scores) is committed before the outcome is revealed to the harness.
4. **Scoring** —
   - *Listing decisions:* simulated would_list vs. actual listing per channel
     archetype (precision/recall).
   - *Objections:* overlap between simulated top-5 objections and objections
     documented in real trade negotiations (hit rate).
   - *Direction of price feedback:* did the simulation flag the same price
     friction the market showed?
5. **Calibration loop** — systematic misses feed back into persona thresholds
   (e.g. margin floors, trial barriers) as data-driven corrections, versioned
   per pack.

## Running your own validation

You don't need our data to validate — you need *your* data:

1. Pick 3–5 of your own past launches (mix of hits and misses).
2. Write the product YAML from what you knew *before* launch.
3. Run the simulation and lock the output.
4. Compare against what actually happened.
5. Open an issue (or PR) with your aggregate results — methodology feedback is
   as valuable as code.

If simulation output contradicts your market experience, believe your market
experience — then tell us where the personas were wrong.

## Calibration harness: proving realism instead of claiming it

The calibration harness is the first operational validation tool: it asks a
persona pool to answer multiple-choice questions whose **true population
distributions are known from public statistics**, then scores the simulated
distribution against the reference via **Total Variation Distance (TVD)**.

### How it works

```bash
MARKET_SWARM_MOCK=1 python -m market_swarm calibrate \
  --questions data/calibration/consumer_basics_eu.yaml \
  --pack fmcg \
  --output report.json
```

1. **Load a question set** — e.g., EU consumer behavior questions grounded in
   Eurostat, Eurobarometer, EU-SILC data (`data/calibration/consumer_basics_eu.yaml`).
2. **Shuffle option order** (seeded per persona) to mitigate LLM ordering bias.
3. **Each persona answers each question** — in mock mode, deterministic weighted
   samples; in real mode, LLM calls with JSON extraction.
4. **Score per question** — compute TVD between simulated and reference
   distribution. TVD ∈ [0, 1]: 0 = identical, 1 = disjoint.
5. **Report** — print per-question TVD, calibration score (1 - mean TVD) as
   percentage, high-variance questions flagged for investigation.

### Metrics

- **Calibration Score**: `100 × (1 - mean TVD)` — 0–100 scale.
  - **80–100**: Excellent realism. Persona population tracks reference closely.
  - **60–79**: Good signal. Usable for relative comparisons (variant A vs. B).
  - **40–59**: Noisy. Still useful for objection discovery; don't trust absolute numbers.
  - **0–39**: Poor calibration. Investigate or retrain personas.

- **Per-Question TVD**: Spot high-variance questions (TVD ≥ 0.15 flagged in
  output) — these reveal systematic persona biases worth fixing.

### What this proves

✓ **Distribution matching** — simulated population behaves like real population
on known axes (e.g., shopping channel preference, organic food uptake, price
sensitivity).

✓ **Persona diversity** — the swarm isn't collapsed to a single attractor; it
spreads across options realistically.

✗ **Individual accuracy** — calibration compares *distributions*, not individuals.
A perfectly calibrated population can still give wrong advice about a specific
person.

✗ **Out-of-distribution generalization** — a question set grounded in 2023
EU data will not validate personas on 2026 technology adoption. Calibration is
time-and-domain-specific.

### Contributing question sets

The calibration harness is only as good as its reference data. Contribute
question sets via PR:

1. Pick a region (EU, US, APAC, etc.) and a topic (food, tech, financial services).
2. Source 6–8 multiple-choice questions from **published aggregate statistics**
   (Eurostat, census, Pew Research, industry reports).
3. Include reference distribution per option (normalized to ~1.0).
4. Add source URLs and notes on variance/caveats.
5. File format: `data/calibration/<topic>_<region>.yaml` (see
   `data/calibration/consumer_basics_eu.yaml` as template).
6. Run in mock mode to verify structure, then in real mode with a small persona
   set to spot-check credibility.

### Limitations & biases

- **Option order**: Even with shuffling, LLMs show systematic bias toward
  first/last options. Calibration dampens but doesn't eliminate this.
- **Reference data lag**: Public statistics are typically 1–2 years old. Social
  change (adoption, preferences) may have moved faster than data.
- **Multiple choice format**: A persona that would give a nuanced answer is
  forced into a bucketing. TVD reflects this compression, not persona
  unrealism.
- **Availability heuristic**: LLMs are trained on internet text, so internet
  subgroups (younger, more engaged, English-speaking) are overrepresented
  in training. Expect calibration to drift toward web-typical answers on
  controversial topics.

### Example output

```
Calibration Harness — FMCG (12 personas × 8 questions)
MOCK mode enabled (deterministic seeded responses)

  [1/12] Marcus Hoffmann... ✓
  [2/12] Zeynep Arslan... ✓
  ...
  [12/12] Svetlana Orlov... ✓

Calibration Results
Pack: FMCG | Personas: 12 | Questions: 8
Calibration Score: 72.4% (Mean TVD: 0.276)

Per-Question Results
Question ID          TVD     Sample Distribution
grocery_channel      0.089   Hard discounter: 35%, Full-range: 55%, ...
organic_frequency    0.152   Regularly: 18%, Sometimes: 28%, ...
...

High-TVD Questions (≥0.15) — Worth investigating:

organic_frequency: How often do you buy organic food products?
  Option              Simulated  Reference  Δ
  Regularly           18.0%      15.0%      +3.0%
  Sometimes           28.0%      25.0%      +3.0%
  Rarely              30.0%      30.0%      ±0.0%
  Never               24.0%      30.0%      -6.0%
```

Simulated personas are undersampling "never" organic buyers — worth checking if
the FMCG personas have an implicit upmarket bias.

## Transparency commitments

- Every output carries an AI-generation disclaimer (EU AI Act Art. 50).
- Mock mode (`MARKET_SWARM_MOCK=1`) is clearly labeled in its output.
- Validation results — positive or negative — will be published in this
  document as they exist.
