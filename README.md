# Market Swarm

**Simulate how the market will react to your product — before you launch it.**

Market Swarm runs your product concept past a swarm of LLM-powered personas:
trade buyers, category managers and consumers — each with numbered decision
priorities, concrete thresholds and real category economics. In 15 minutes you
get scored feedback, ranked objections and channel-level differences that
would otherwise surface months later in real negotiations.

> **What this is:** a synthetic pre-research tool — a hypothesis generator
> that makes your empirical research (and your launch) sharper.
> **What this is not:** a replacement for real market research.
> See [Limitations & Validation](#limitations--validation).

---

## Try it in 2 minutes — no API key needed

```bash
git clone https://github.com/rockywuest/market-swarm.git
cd market-swarm
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Offline demo: deterministic mock evaluations, zero cost
MARKET_SWARM_MOCK=1 python -m market_swarm simulate \
  --product examples/oat-bar-protein.yaml
```

For real simulations, add one LLM key (`cp .env.example .env`, then set
`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` or
`OPENAI_API_KEY`) and drop the `MARKET_SWARM_MOCK` flag.

### Web dashboard

```bash
python server.py           # FastAPI + static dashboard on :8000
```

Pick a pack, run a simulation, watch the swarm score your product.

---

## The problem

Bringing a new product to market means concept tests, focus groups at
five-figure cost per round, and 4–8 week waits for panel results. Most
mid-size manufacturers skip pre-launch research entirely and rely on gut
feeling — then learn about their pricing problem in the first annual
negotiation with a discounter.

## The approach

Every persona is a YAML file with a distinct role, numbered priorities and
hard thresholds — a hard-discount buyer who walks away above a price point,
an in-house category manager who thinks in line capacity and cannibalization,
a health-conscious consumer who reads the ingredient list first. The engine is
industry-agnostic; industry knowledge lives in **packs**:

```
┌─────────────────────────────────────────────────────────┐
│                      Market Swarm                        │
│                                                          │
│  product.yaml ──►  Industry Pack  ──►  Simulation Engine │
│                    (personas +          (async, mock     │
│                     prompt builder)      mode, retries)  │
│                             │                            │
│                             ▼                            │
│               Scores · Objections · Channel Δ            │
│               CLI · Dashboard · PDF/PPTX export          │
└─────────────────────────────────────────────────────────┘
```

Adding an industry = adding a directory. No engine changes
(`market_swarm/industry_packs/` — the registry discovers packs at runtime).

## Industry packs

| Pack | Personas | Status |
|---|---|---|
| **FMCG / Food** — hard-discount, full-range, drugstore buyers; in-house & retail category managers; four consumer archetypes | 12 | ✅ Available |
| **B2B SaaS** — decision makers, users, IT/security, procurement | 10 | ✅ Available |
| **Pharma / Healthcare** — payers, hospital pharmacists, GPs, regulators-context | 10 | ✅ Available |
| **Automotive / Mobility** — fleet managers, dealers, TCO-driven buyers | 10 | ✅ Available |
| Financial Services · Real Estate · Retail/D2C · Energy | — | Roadmap |

Depth over breadth: the FMCG pack is the flagship — it encodes actual trade
economics (margin floors, shelf-space productivity in EUR per linear meter,
cannibalization logic, promo mechanics), not generic "retail buyer" prompts.

**Scaling beyond expert panels:** for consumer swarms of hundreds or
thousands of demographically weighted personas, see
[`docs/persona-sources.md`](docs/persona-sources.md) — a curated, license-aware
guide to open persona datasets (Nemotron-Personas, FinePersonas), official
statistics for census-grounded generation, and why there is a
Germany/EU-shaped gap this project intends to fill.

## Product definition

```yaml
product:
  name: "NordOat Protein Bar"
  brand: "NordOat Foods"
  category: "Snack Bars"
  product_type: fmcg
  pricing:
    trade_price_eur: 0.85
    rrp_eur: 1.49
  claims: ["12g protein", "vegan", "no added sugar"]
  competitors:
    - name: "ProBar Elite"
      rrp_eur: 2.49
simulation:
  focus_areas: ["pricing", "differentiation", "channel fit"]
```

See `examples/` for complete definitions across all four packs.

## Limitations & Validation

Market Swarm output is **synthetic**. As of v1.0.0 it has **not** been
validated against real launch outcomes — and we say so out loud, because a
simulation tool you can't calibrate is a toy.

What simulation is expected to be good at (objection discovery, relative
variant ranking, channel differences) vs. weak at (absolute scores, volume
forecasts) — and the blind backtest design we're building to measure it — is
documented in [`docs/validation.md`](docs/validation.md). If you run the
methodology against your own historical launches, we want to hear the results:
positive or negative.

## EU compliance by design

- **AI Act Art. 50** — every output (CLI, API, PDF, PPTX) carries an
  AI-generation disclaimer. Non-negotiable, built into the engine.
- **GDPR** — your product YAML goes to the LLM provider you configure;
  the provider chain is explicit, no hidden calls.
- **Fair competition** — personas are fictional people at **archetype**
  employers ("a leading hard-discount chain"), never real companies or
  real employees.
- **Product liability** — results are labeled simulation, never prediction.

## Inspired by

- [MiroFish](https://github.com/666ghj/MiroFish) — LLM social simulation at scale
- [CAMEL-AI OASIS](https://github.com/camel-ai/oasis) — multi-agent social simulation
- Hands-on category management experience in European FMCG

## License

MIT © 2026 [Rocky Wüst](https://github.com/rockywuest)

Commercial support, private industry packs and validation projects:
**FRECH & WUEST GmbH** · [frechundwuest.de](https://frechundwuest.de)
