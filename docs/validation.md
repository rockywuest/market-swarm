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

## Transparency commitments

- Every output carries an AI-generation disclaimer (EU AI Act Art. 50).
- Mock mode (`MARKET_SWARM_MOCK=1`) is clearly labeled in its output.
- Validation results — positive or negative — will be published in this
  document as they exist.
