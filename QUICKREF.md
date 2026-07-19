# Market Swarm — Quick Reference

## CLI

```bash
# Offline demo (no API key, deterministic)
MARKET_SWARM_MOCK=1 python -m market_swarm simulate --product examples/oat-bar-protein.yaml

# Real simulation (requires an LLM key, see .env.example)
python -m market_swarm simulate --product examples/oat-bar-protein.yaml

# Model selection + JSON export
python -m market_swarm simulate \
  --product examples/oat-bar-protein.yaml \
  --model claude-sonnet-4-5 \
  --output results/my-sim.json

# List available industry packs
python -m market_swarm list-packs
```

## API server & dashboard

```bash
python server.py                          # dashboard at http://localhost:8000
python server.py --port 8001 --reload     # dev mode

curl http://localhost:8000/health
curl http://localhost:8000/api/packs
curl http://localhost:8000/api/packs/fmcg/personas
```

## Industry packs

| Pack | Personas | Status |
|------|----------|--------|
| FMCG / Food | 12 | ✅ Available |
| B2B SaaS (professional services) | 10 | ✅ Available |
| Pharma / Healthcare | 10 | ✅ Available |
| Automotive / Mobility | 10 | ✅ Available |
| Financial Services · Real Estate · Retail/D2C · Energy | — | Roadmap |

## Adding a persona

Create a YAML file in `market_swarm/industry_packs/<pack>/personas/`:

```yaml
name: "Fictional Name"            # never a real person
type: persona_type_snake_case
retailer: "an archetype employer" # never a real company
system_prompt: |
  You are [name], [role] at [archetype employer].

  Your priorities (in this order):
  1. [Specific, with concrete thresholds]
  2. [Numbers/KPIs wherever possible]
  3. [Domain jargon, distinct voice]

  You respond in the simulation's requested output language.
evaluation_criteria:
  - criterion_one
  - criterion_two
  - criterion_three
```

The registry discovers it automatically — no code changes.

## Adding an industry pack

```
market_swarm/industry_packs/<new_pack>/
  pack.yaml           # name, display_name, product_type, version
  models.py           # Pydantic v2: attributes / pricing / competitor models
  prompt_builder.py   # build_evaluation_prompt() + build_panel_info()
  personas/*.yaml
```

## LLM provider priority

```
1. Gemini      (GEMINI_API_KEY)
2. Anthropic   (ANTHROPIC_API_KEY)
3. OpenRouter  (OPENROUTER_API_KEY)
4. OpenAI      (OPENAI_API_KEY)
MARKET_SWARM_MOCK=1 overrides all — offline deterministic mode
```

## Compliance quick-check (before every commit)

- [ ] Output labeled as AI-generated? (EU AI Act Art. 50 — `DISCLAIMER` in engine.py)
- [ ] No real company names or real person names in personas/examples?
- [ ] No guarantees/predictions in wording — always "simulation"?

## Key files

```
market_swarm/
  engine.py          # Orchestration, mock mode, LLM clients, JSON parser
  models.py          # Core Pydantic models
  registry.py        # Industry pack discovery
  export.py          # PDF / PPTX reports
  __main__.py        # CLI entry point
  api/               # FastAPI app, routes, job manager
  industry_packs/    # fmcg / b2b_saas / pharma / automotive
server.py            # API server entry point
examples/            # One product YAML per pack
dashboard/           # Static dashboard (served by API)
docs/validation.md   # Validation methodology & limitations
```
