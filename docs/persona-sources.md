# Persona Sources — Scaling the Swarm with Real-World Grounding

Market Swarm ships ~42 hand-crafted **expert personas** (trade buyers, category
managers) — depth over breadth. For **consumer swarms** (hundreds to thousands
of demographically weighted personas), don't hand-write them: sample from
open persona datasets or generate them from official statistics.

This page curates the sources, their licenses, and how to use them cleanly.
**Market Swarm does not redistribute any of these datasets** — load them at
runtime (e.g. via the `datasets` library); the license obligations are between
you and the dataset publisher.

## Ready-to-use persona datasets

| Dataset | Size | Grounding | License | Commercial use |
|---|---|---|---|---|
| [Nemotron-Personas-USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA) (NVIDIA) | 6M | US Census — real joint demographic distributions | CC-BY-4.0 | ✅ with attribution |
| [Nemotron-Personas-Japan](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan) / [-India](https://huggingface.co/datasets/nvidia/Nemotron-Personas-India) / [-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) / [-Brazil](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Brazil) / [-Singapore](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Singapore) | 1M+ each | National census / statistics offices | CC-BY-4.0 | ✅ with attribution |
| [FinePersonas](https://huggingface.co/datasets/argilla/FinePersonas-v0.1) (Argilla) | 21M | Inferred from FineWeb-Edu web text | Llama-3 license | ⚠️ allowed with Llama-3 terms (attribution, acceptable-use) |
| [PersonaHub](https://huggingface.co/datasets/proj-persona/PersonaHub) | 200k+ released | Web-text derived ("1B personas" method) | CC-BY-**NC**-SA | ❌ research only — do not use commercially |

**Recommendation:** the Nemotron family is the gold standard — personas whose
age × education × occupation × geography correlations match real censuses,
under a clean commercial license.

## The gap: Germany and Europe

As of mid-2026 there is **no census-grounded open persona dataset for Germany
or any EU locale** — NVIDIA's locale roll-out (USA, Japan, India, Korea,
Singapore, Brazil, El Salvador) has not reached Europe. The
[Nemotron methodology](https://docs.nvidia.com/nemo/datadesigner/dev-notes/designing-nemotron-personas)
is documented and its statistical components are Apache-2.0: a probabilistic
graphical model fitted on official statistics generates demographically
faithful records; an LLM turns each record into a narrative persona.

The German raw material for replicating this exists and is license-clean:

| Source | What it grounds | Access / license |
|---|---|---|
| [Zensus 2022](https://www.zensus2022.de/) + [GENESIS API](https://www-genesis.destatis.de/) (Destatis) | Age, household, housing, region — joint marginals | Data licence Germany (DL-DE/BY-2.0) — commercial use with attribution |
| Mikrozensus (Destatis) | Education, occupation, income brackets, annually | Public-/Campus-Use-Files |
| EVS — Einkommens- und Verbrauchsstichprobe | **Household spending by category** — the FMCG grounding | Scientific-use files; aggregates publicly |
| [ALLBUS](https://www.gesis.org/allbus) (GESIS) / European Values Study | Values, attitudes, trust — the "milieu" dimension | Free for research; aggregates citable |
| Eurostat [EU-SILC](https://ec.europa.eu/eurostat/web/microdata/european-union-statistics-on-income-and-living-conditions) + Household Budget Survey | Income & consumption, **harmonized across all EU states** | Microdata by application; aggregates open |
| Academic synthetic populations (e.g. the [NRW 17.5M-person model](https://ieeexplore.ieee.org/document/9715369/), ~98% attribute accuracy) | Proof that census-grounded German populations are buildable | Published research |

Building **census-grounded German consumer personas** from these sources is on
this project's roadmap — as an open CC-BY dataset, because a market simulation
is only as credible as its population.

Note on German commercial segmentations (Sinus-Milieus, Limbic Types, GfK
Roper): these are proprietary and trademarked — do not copy them into
personas. An equivalent open values-based milieu layer can be derived from
ALLBUS / European Values Study distributions instead.

## What about real people / social media data?

**Never build personas from identifiable individuals** — scraping social
profiles violates platform terms and, in the EU, the GDPR; it would also
poison the credibility this project depends on. Realism comes from
*distributions*, not from cloning real persons. Legitimate uses of
commercial audience data:

- **Validation of segment sizes** — ad-platform audience estimates and panel
  products ([YouGov Profiles](https://yougov.com/en-us/business/products/profiles),
  [GWI](https://www.gwi.com/), Statista Consumer Insights) can check whether
  your simulated population's segment proportions match reality. These are
  licensed products: use them in private deployments, don't redistribute.
- **Voice grounding** — public product-review corpora can inform how consumer
  archetypes talk about a category. Treat as analysis input, not as
  redistributable data.

## Calibration: proving realism instead of claiming it

The deepest form of grounding is behavioral: have the persona population
answer questions whose true population distributions are known (ALLBUS,
Eurostat, EVS marginals) and score the deviation. A persona pool that can
show "simulated answer distributions within X points of official statistics"
is *demonstrably* realistic — that calibration harness is part of the
[validation roadmap](validation.md). The
[Stanford generative-agents result](https://github.com/StanfordHCI/genagents)
(interview-grounded agents reproducing individuals' survey answers with ~85%
of test-retest accuracy) is the methodological north star: if you have real
qualitative interviews, ground private personas in them.
