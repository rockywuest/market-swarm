"""Pharma / Healthcare data models."""

from typing import Optional

from pydantic import BaseModel, Field


class Attributes(BaseModel):
    wirkstoff: str = Field(
        description="INN (International Nonproprietary Name) or active ingredient"
    )
    darreichungsform: str = Field(
        description="e.g. film-coated tablet, injection solution, sustained-release capsule"
    )
    zulassungsstatus: str = Field(
        description="Central (EMA), decentralized, or national approval (BfArM)"
    )
    indikation: str = Field(description="Approved indication(s)")
    vergleichstherapie: str = Field(
        description="Appropriate Comparative Therapy (Zweckmaessige Vergleichstherapie, per G-BA)"
    )
    evidenzlevel: str = Field(
        description="e.g. Ia (meta-analysis of RCTs), Ib (single RCT), IIa, etc."
    )
    nebenwirkungsprofil: str = Field(description="Summary of most common adverse events")
    applikation: str = Field(description="e.g. oral once daily, subcutaneous once weekly")
    besondere_patientengruppen: list[str] = Field(
        default_factory=list,
        description="e.g. children, pregnant women, renal impairment, geriatric patients",
    )


class Pricing(BaseModel):
    apothekenverkaufspreis_eur: float = Field(description="Pharmacy retail price incl. VAT")
    herstellerabgabepreis_eur: float = Field(description="Manufacturer price (HAP)")
    festbetrag_eur: Optional[float] = Field(
        default=None, description="Reference price (Festbetrag) if applicable"
    )
    ddd_preis_eur: float = Field(description="Price per defined daily dose (DDD)")
    gkv_erstattung: bool = Field(description="Reimbursable by statutory health insurance (GKV)")
    rabattvertrag_moeglich: bool = Field(
        description="Eligible for rebate agreements (Rabattvertraege) per SGB V §130a"
    )


class Competitor(BaseModel):
    name: str = Field(description="Active ingredient or product name of competitor")
    brand: Optional[str] = Field(default=None, description="Brand name")
    ddd_preis_eur: Optional[float] = Field(default=None, description="DDD price in EUR")
    market_position: Optional[str] = Field(
        default=None, description="e.g. market leader, generic, biosimilar"
    )
    key_differentiator: Optional[str] = Field(
        default=None, description="Key difference vs. own product"
    )
