"""B2B SaaS prompt builder."""


class SaaSPromptBuilder:
    def build_evaluation_prompt(self, product, focus_areas: list[str]) -> str:
        attrs = product.attributes
        pricing = product.pricing

        # Competitors
        competitors_text = ""
        if product.competitors:
            competitors_text = "\n\nMarket competitors:\n"
            for c in product.competitors:
                competitors_text += f"- {c.name}"
                if c.brand:
                    competitors_text += f" ({c.brand})"
                if c.monthly_price_eur:
                    competitors_text += f": \u20ac{c.monthly_price_eur}/month"
                if c.pricing_model:
                    competitors_text += f" [{c.pricing_model}]"
                if c.key_differentiator:
                    competitors_text += f" \u2014 {c.key_differentiator}"
                if c.market_position:
                    competitors_text += f" ({c.market_position})"
                competitors_text += "\n"

        # Pricing details
        pricing_lines = []
        if pricing.monthly_per_user_eur:
            pricing_lines.append(f"- Per user/month: \u20ac{pricing.monthly_per_user_eur}")
        if pricing.annual_per_user_eur:
            pricing_lines.append(
                f"- Per user/year (annual contract): \u20ac{pricing.annual_per_user_eur}/month"
            )
        if pricing.flat_monthly_eur:
            pricing_lines.append(f"- Flat rate/month: \u20ac{pricing.flat_monthly_eur}")
        if pricing.flat_annual_eur:
            pricing_lines.append(f"- Flat rate/year: \u20ac{pricing.flat_annual_eur}")
        pricing_lines.append(f"- Pricing model: {pricing.pricing_model}")
        pricing_lines.append(f"- Free trial: {'Yes' if pricing.free_trial else 'No'}")
        if pricing.enterprise_custom:
            pricing_lines.append("- Enterprise pricing: Custom")
        pricing_text = "\n".join(pricing_lines)

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nPlease evaluate especially: {', '.join(focus_areas)}"

        return f"""Evaluate this B2B SaaS product from your professional perspective:

PRODUCT: {product.name}
VENDOR: {product.brand}
CATEGORY: {product.category} / {product.subcategory or "N/A"}

PRODUCT ATTRIBUTES:
- Deployment: {attrs.deployment}
- Integration: {attrs.integration_effort or "N/A"}
- Data security: {attrs.data_security or "N/A"}
- AI-powered: {"Yes" if attrs.ai_powered else "No"}
- Languages: {", ".join(attrs.languages)}
- Certifications: {", ".join(attrs.certifications) if attrs.certifications else "N/A"}

PRICING:
{pricing_text}

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

Note: "would_list" means: Would you buy, implement, or recommend this product?

Be honest and direct. No marketing speak. Genuine assessment from your role. You respond in the simulation's requested output language. Be direct and specific."""

    def build_panel_info(self, product) -> dict[str, str]:
        pricing = product.pricing
        if pricing.monthly_per_user_eur:
            pricing_line = f"\u20ac{pricing.monthly_per_user_eur}/user/month"
        elif pricing.flat_monthly_eur:
            pricing_line = f"\u20ac{pricing.flat_monthly_eur}/month"
        else:
            pricing_line = "Enterprise"
        return {
            "title": "Market Swarm Simulation (B2B SaaS)",
            "pricing_line": pricing_line,
            "rate_label": "Adoption Rate",
        }


prompt_builder = SaaSPromptBuilder()
