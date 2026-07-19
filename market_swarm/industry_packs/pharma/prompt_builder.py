"""Pharma / Healthcare prompt builder."""


class PharmaPromptBuilder:
    def build_evaluation_prompt(self, product, focus_areas: list[str]) -> str:
        competitors_text = ""
        if product.competitors:
            competitors_text = "\n\nMarket Competitors:\n"
            for c in product.competitors:
                competitors_text += f"- {c.name}"
                if c.brand:
                    competitors_text += f" ({c.brand})"
                if c.ddd_preis_eur:
                    competitors_text += f": DDD \u20ac{c.ddd_preis_eur}"
                if c.market_position:
                    competitors_text += f" [{c.market_position}]"
                if c.key_differentiator:
                    competitors_text += f" \u2014 {c.key_differentiator}"
                competitors_text += "\n"

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nPlease evaluate particularly: {', '.join(focus_areas)}"

        special_groups = ", ".join(product.attributes.besondere_patientengruppen) or "none"

        reimbursed_text = "Yes" if product.pricing.gkv_erstattung else "No"
        rabatt_text = "Yes" if product.pricing.rabattvertrag_moeglich else "No"
        reference_price_text = (
            f"\u20ac{product.pricing.festbetrag_eur}"
            if product.pricing.festbetrag_eur is not None
            else "No reference price"
        )

        return f"""Evaluate the following pharmaceutical product from your perspective:

PRODUCT: {product.name}
BRAND: {product.brand}
CATEGORY: {product.category} / {product.subcategory or "-"}

PHARMACEUTICAL PROPERTIES:
- Active Ingredient (INN): {product.attributes.wirkstoff}
- Dosage Form: {product.attributes.darreichungsform}
- Indication: {product.attributes.indikation}
- Administration: {product.attributes.applikation}
- Evidence Level: {product.attributes.evidenzlevel}
- Approval Status: {product.attributes.zulassungsstatus}
- Comparative Therapy: {product.attributes.vergleichstherapie}
- Adverse Event Profile: {product.attributes.nebenwirkungsprofil}
- Special Patient Groups: {special_groups}

PRICING STRUCTURE:
- Pharmacy Retail Price: \u20ac{product.pricing.apothekenverkaufspreis_eur}
- Manufacturer Price: \u20ac{product.pricing.herstellerabgabepreis_eur}
- Reference Price: {reference_price_text}
- DDD Price: \u20ac{product.pricing.ddd_preis_eur}
- GKV Reimbursement: {reimbursed_text}
- Eligible for Rebate Agreements: {rabatt_text}

CLAIMS: {", ".join(product.claims)}

POSITIONING: {product.positioning}

TARGET CHANNELS: {", ".join(product.target_channels)}
{competitors_text}{focus_text}

Respond in the following JSON format:
{{
    "score": <0-10>,
    "would_list": <true/false>,
    "key_feedback": "<One-sentence summary>",
    "objections": ["<Objection 1>", "<Objection 2>", ...],
    "suggestions": ["<Suggestion 1>", "<Suggestion 2>", ...],
    "price_feedback": "<Price assessment>",
    "detailed_reasoning": "<2-3 sentences detailed reasoning>"
}}

Be honest and direct. No marketing speak. Evidence-based assessment."""

    def build_panel_info(self, product) -> dict[str, str]:
        return {
            "title": "Market Swarm Simulation (Pharma)",
            "pricing_line": f"\u20ac{product.pricing.apothekenverkaufspreis_eur} Pharmacy Price | \u20ac{product.pricing.ddd_preis_eur} DDD Price",
            "rate_label": "Recommendation Rate",
        }


prompt_builder = PharmaPromptBuilder()
