# Market Swarm — Project Instructions

## Core Workflow
- Architecture decisions before code — never skip this step
- Scope: one feature/task per conversation

## Code Quality Standards
- Python 3.11+ with type hints on all public functions
- Pydantic v2 for all data models — strict validation, no bare dicts
- Run `ruff check` and `ruff format` after every file change
- Keep implementations minimal — no abstractions that weren't asked for
- All prompts, personas and docs in English; simulation output language is
  controlled by the product YAML (`language` field)

## Architecture Rules

### Industry Pack System
- Personas are YAML files in `industry_packs/<pack>/personas/`
- Each pack has: `pack.yaml`, `personas/`, `models.py`, `prompt_builder.py`
- NEVER hardcode product types — use the registry for dynamic dispatch
- New industries = new pack directory, not changes to engine.py

### Persona Quality
- Every persona needs: name (fictional), type, system_prompt (150–300 words),
  evaluation_criteria (3–5)
- System prompts must include numbered decision priorities with concrete
  thresholds — no generic statements
- Personas use retailer/employer ARCHETYPES ("a leading hard-discount chain"),
  never real company names, and always fictional person names

### Engine
- `engine.py` handles orchestration only — no industry-specific logic
- LLM client selection via `_get_client()` — priority: Gemini > Anthropic > OpenRouter > OpenAI
- `MARKET_SWARM_MOCK=1` runs deterministic offline evaluations (demos, CI)
- JSON extraction uses 4-strategy fallback parser — do not simplify
- All API calls must respect rate limits and handle timeouts gracefully

## EU Compliance (check on EVERY change)
1. **AI Act Art. 50**: every output must be labeled as AI-generated
   (see `DISCLAIMER` in engine.py — always included in results)
2. **GDPR Art. 28**: product YAML data goes to cloud LLM APIs — users must be
   able to verify the provider chain
3. **Product liability**: no guarantees or predictions — always "simulation"
4. Never use real person names or real company names in personas or examples

## Communication Style
- Explain WHY when making decisions, not just what
- Flag tradeoffs explicitly before implementing
- If something seems wrong with a request, challenge it
