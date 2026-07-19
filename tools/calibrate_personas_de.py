"""One-off async calibration of the Personas-DE dataset (real LLM calls).

Runs N sampled personas through the EU consumer question set concurrently,
skips unparsable answers (no first-option fallback bias), and reports TVD
per question plus the overall calibration score.

    .venv/bin/python tools/calibrate_personas_de.py --n 100 --concurrency 8
"""

import argparse
import asyncio
import json
import random
from collections import Counter

from market_swarm.calibration import (
    _total_variation_distance,
    load_question_set,
)
from market_swarm.engine import _get_async_client, _parse_llm_response, _resolve_model
from market_swarm.population import load_population


async def ask(client, backend, model, persona, question, sem):
    options = question.options.copy()
    random.Random(hash(f"{persona.name}:{question.id}") % (2**31)).shuffle(options)
    prompt = (
        f"Beantworte die Frage mit einem JSON-Objekt. Wähle genau EINE Option.\n\n"
        f"Frage: {question.question}\n\nOptionen:\n"
        + "\n".join(f"- {o}" for o in options)
        + '\n\nAntwort als JSON: {"choice": "<option_text>"} — wähle die Option, '
        "die am besten zu deiner Perspektive passt."
    )
    async with sem:
        try:
            if backend == "anthropic":
                r = await client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=persona.to_system_message(),
                    messages=[{"role": "user", "content": prompt}],
                )
                text = r.content[0].text
            else:
                resolved, _ = _resolve_model(backend, model)
                r = await client.chat.completions.create(
                    model=resolved,
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": persona.to_system_message()},
                        {"role": "user", "content": prompt},
                    ],
                )
                text = r.choices[0].message.content
            choice = _parse_llm_response(text).get("choice")
            return question.id, choice if choice in question.options else None
        except Exception:
            return question.id, None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--questions", default="data/calibration/consumer_basics_eu.yaml")
    ap.add_argument("--output", default="data/personas-de/calibration_v0.1.json")
    args = ap.parse_args()

    personas = load_population("personas-de", args.n, seed=7)
    questions = load_question_set(args.questions)
    backend, client = _get_async_client()
    sem = asyncio.Semaphore(args.concurrency)
    from market_swarm.engine import DEFAULT_MODEL

    tasks = [ask(client, backend, DEFAULT_MODEL, p, q, sem) for p in personas for q in questions]
    print(f"{len(personas)} personas × {len(questions)} questions = {len(tasks)} calls …")
    results = await asyncio.gather(*tasks)

    by_q: dict[str, Counter] = {}
    skipped = 0
    for qid, choice in results:
        if choice is None:
            skipped += 1
            continue
        by_q.setdefault(qid, Counter())[choice] += 1

    report = {"n_personas": len(personas), "skipped_answers": skipped, "questions": {}}
    tvds = []
    for q in questions:
        counts = by_q.get(q.id, Counter())
        total = sum(counts.values()) or 1
        sim = {opt: counts.get(opt, 0) / total for opt in q.options}
        tvd = _total_variation_distance(sim, q.reference)
        tvds.append(tvd)
        report["questions"][q.id] = {
            "tvd": round(tvd, 4),
            "simulated": {k: round(v, 3) for k, v in sim.items()},
            "reference": q.reference,
        }
        print(f"  {q.id}: TVD {tvd:.3f}")

    score = 100 * (1 - sum(tvds) / len(tvds))
    report["calibration_score"] = round(score, 1)
    print(f"\nCalibration Score: {score:.1f}%  (skipped: {skipped}/{len(tasks)})")
    json.dump(report, open(args.output, "w"), indent=1, ensure_ascii=False)
    print(f"Report → {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
