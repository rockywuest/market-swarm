"""Upload the Personas-DE dataset to the Hugging Face Hub.

One-time setup: a write token from https://huggingface.co/settings/tokens,
then `hf auth login` (or set HF_TOKEN). Then:

    .venv/bin/python tools/upload_personas_de.py [--repo-id RockyRocket/personas-de]
"""

import argparse
from pathlib import Path

from huggingface_hub import HfApi

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "personas-de"

CARD = """---
license: cc-by-4.0
language:
  - de
tags:
  - synthetic
  - personas
  - germany
  - market-research
  - census-grounded
size_categories:
  - n<1K
pretty_name: Personas-DE
---

# Personas-DE — Synthetic German Consumer Personas

The first open synthetic persona dataset for Germany grounded in official
statistics: demographic records sampled against published Destatis / Zensus
2022 / Mikrozensus marginals (age, gender, Bundesland, household size,
education, income band, occupation status) plus consumer dimensions aligned
with public Eurostat/Eurobarometer aggregates, each turned into a
first-person German narrative.

Built by and for [market-swarm](https://github.com/rockywuest/market-swarm),
the open-source LLM market-simulation tool — usable there directly via
`--population personas-de:N`.

**v0.1 honesty note:** marginals are grounded in cited official aggregates;
cross-attribute correlations are *modeled*, not measured (IPF on GENESIS
joint tables is the roadmap). Narratives are LLM interpretations of the
records. Full methodology, source table and limitations:
[docs/personas-de.md](https://github.com/rockywuest/market-swarm/blob/main/docs/personas-de.md).

License: CC-BY-4.0 — free for commercial use with attribution.
Maintainer: Rocky Wüst ([@rockywuest](https://github.com/rockywuest)).
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default="RockyRocket/personas-de")
    args = parser.parse_args()

    jsonl = DATA_DIR / "personas_de_v0.1.jsonl"
    stats = DATA_DIR / "personas_de_v0.1.stats.json"
    if not jsonl.exists():
        raise SystemExit(f"Dataset not found: {jsonl} — run generate-personas-de first.")

    api = HfApi()
    api.create_repo(args.repo_id, repo_type="dataset", exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(jsonl),
        path_in_repo="personas_de_v0.1.jsonl",
        repo_id=args.repo_id,
        repo_type="dataset",
    )
    if stats.exists():
        api.upload_file(
            path_or_fileobj=str(stats),
            path_in_repo="personas_de_v0.1.stats.json",
            repo_id=args.repo_id,
            repo_type="dataset",
        )
    api.upload_file(
        path_or_fileobj=CARD.encode(),
        path_in_repo="README.md",
        repo_id=args.repo_id,
        repo_type="dataset",
    )
    print(f"Uploaded → https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
