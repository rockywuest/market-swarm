"""Automotive prompt builder."""


class AutomotivePromptBuilder:
    """Constructs evaluation prompts for automotive product launches."""

    def build_evaluation_prompt(self, product, focus_areas: list[str]) -> str:
        attrs = product.attributes
        pricing = product.pricing

        # Competitors
        competitors_text = ""
        if product.competitors:
            competitors_text = "\n\nCompetitors:\n"
            for c in product.competitors:
                line = f"- {c.name}"
                if c.brand:
                    line += f" ({c.brand})"
                if c.listenpreis_eur:
                    line += f": {c.listenpreis_eur:,.0f} EUR"
                if c.leistung_kw:
                    line += f", {c.leistung_kw} kW"
                if c.reichweite_wltp_km:
                    line += f", {c.reichweite_wltp_km} km WLTP"
                if c.key_differentiator:
                    line += f" — {c.key_differentiator}"
                competitors_text += line + "\n"

        # Focus areas
        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nPlease especially evaluate: {', '.join(focus_areas)}"

        # Assistants
        assist_text = ", ".join(attrs.assistenzsysteme) if attrs.assistenzsysteme else "n/a"

        return f"""Evaluate this vehicle from your perspective:

VEHICLE: {product.name}
MANUFACTURER: {product.brand}
CLASS: {product.category}{f" / {product.subcategory}" if product.subcategory else ""}

TECHNICAL SPECIFICATIONS:
- Powertrain: {attrs.antrieb}
- Power: {attrs.leistung_kw} kW ({int(attrs.leistung_kw * 1.36)} hp)
- CO2 (WLTP): {f"{attrs.co2_wltp_g_km} g/km" if attrs.co2_wltp_g_km else "0 g/km (BEV)"}
- Range (WLTP): {f"{attrs.reichweite_wltp_km} km" if attrs.reichweite_wltp_km else "n/a"}
- Consumption: {f"{attrs.verbrauch_l_100km} l/100km" if attrs.verbrauch_l_100km else "n/a"}
- Seats: {attrs.sitzplaetze}
- Boot capacity: {attrs.kofferraum_liter} litres
- Length: {f"{attrs.laenge_mm} mm" if attrs.laenge_mm else "n/a"}
- Warranty: {attrs.garantie_jahre} years
- Euro NCAP: {f"{attrs.sicherheit_euro_ncap} stars" if attrs.sicherheit_euro_ncap else "n/a"}
- Driver assistance systems: {assist_text}
- Infotainment: {attrs.infotainment or "n/a"}

PRICING:
- MSRP (list price): {pricing.listenpreis_eur:,.0f} EUR
- Base price: {f"{pricing.basispreis_eur:,.0f} EUR" if pricing.basispreis_eur else "n/a"}
- Lease from: {f"{pricing.leasing_rate_eur:,.0f} EUR/month" if pricing.leasing_rate_eur else "n/a"}
- Environmental incentive: {f"{pricing.bafa_foerderung_eur:,.0f} EUR" if pricing.bafa_foerderung_eur else "not eligible"}
- Operating costs: {f"ca. {pricing.unterhaltskosten_monat_eur:,.0f} EUR/month" if pricing.unterhaltskosten_monat_eur else "n/a"}
- Residual value (36M): {f"{pricing.restwert_36m_pct}%" if pricing.restwert_36m_pct else "n/a"}

CLAIMS: {", ".join(product.claims) if product.claims else "none"}

POSITIONING: {product.positioning}

TARGET CHANNELS: {", ".join(product.target_channels) if product.target_channels else "n/a"}
{competitors_text}{focus_text}

Respond in JSON format:
{{
    "score": <0-10>,
    "would_list": <true/false>,
    "key_feedback": "<One-sentence summary>",
    "objections": ["<Objection 1>", "<Objection 2>", ...],
    "suggestions": ["<Suggestion 1>", "<Suggestion 2>", ...],
    "price_feedback": "<Price assessment>",
    "detailed_reasoning": "<2-3 sentences of detailed reasoning>"
}}

Note: "would_list" means: Would you recommend, purchase, or add this vehicle to your programme?

Be honest and direct. No marketing speak."""

    def build_panel_info(self, product) -> dict[str, str]:
        price = f"{product.pricing.listenpreis_eur:,.0f} EUR"
        power = f"{product.attributes.leistung_kw} kW"
        drive = product.attributes.antrieb
        return {
            "title": "Market Swarm Simulation (Automotive)",
            "pricing_line": f"{price} | {power} | {drive}",
            "rate_label": "Recommendation rate",
        }


prompt_builder = AutomotivePromptBuilder()
