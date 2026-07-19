"""FMCG prompt builder."""


class FMCGPromptBuilder:
    def build_evaluation_prompt(self, product, focus_areas: list[str]) -> str:
        competitors_text = ""
        if product.competitors:
            competitors_text = "\n\nMarket competitors:\n"
            for c in product.competitors:
                competitors_text += f"- {c.name} ({c.brand}): {c.price_eur}\u20ac"
                if c.weight_g:
                    competitors_text += f", {c.weight_g}g"
                if c.protein_g:
                    competitors_text += f", {c.protein_g}g protein"
                if c.channel:
                    competitors_text += f" [{c.channel}]"
                competitors_text += "\n"

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nPlease pay special attention to: {', '.join(focus_areas)}"

        return f"""Evaluate this product from your perspective:

PRODUCT: {product.name}
BRAND: {product.brand}
CATEGORY: {product.category} / {product.subcategory or "-"}

ATTRIBUTES:
- Weight: {product.attributes.weight_g}g
- Protein: {product.attributes.protein_g or "N/A"}g
- Sugar: {product.attributes.sugar_g or "N/A"}g
- Fiber: {product.attributes.fiber_g or "N/A"}g
- Organic: {"Yes" if product.attributes.organic else "No"}
- Vegan: {"Yes" if product.attributes.vegan else "No"}

PRICING:
- RRP: {product.pricing.rrp_eur}\u20ac
- Trade price: {product.pricing.trade_price_eur}\u20ac
- Retail margin: {product.pricing.margin_retail_pct}%

CLAIMS: {", ".join(product.claims)}

POSITIONING: {product.positioning}

TARGET CHANNELS: {", ".join(product.target_channels)}
{competitors_text}{focus_text}

Respond in the following JSON format:
{{
    "score": <0-10>,
    "would_list": <true/false>,
    "key_feedback": "<One sentence summary>",
    "objections": ["<Objection 1>", "<Objection 2>", ...],
    "suggestions": ["<Suggestion 1>", "<Suggestion 2>", ...],
    "price_feedback": "<Price evaluation>",
    "detailed_reasoning": "<2-3 sentences detailed reasoning>"
}}

Be honest and direct. No marketing speak. Genuine assessment."""

    def build_panel_info(self, product) -> dict[str, str]:
        return {
            "title": "Market Swarm Simulation",
            "pricing_line": f"{product.pricing.rrp_eur}\u20ac RRP | {product.pricing.trade_price_eur}\u20ac trade price",
            "rate_label": "Listing Rate",
        }


prompt_builder = FMCGPromptBuilder()
