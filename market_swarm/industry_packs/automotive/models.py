"""Automotive-specific data models."""

from typing import Optional

from pydantic import BaseModel, Field


class Attributes(BaseModel):
    """Vehicle attributes."""

    antrieb: str = Field(description="e.g., petrol, diesel, hybrid, BEV")
    leistung_kw: float = Field(description="Engine power in kW")
    co2_wltp_g_km: Optional[float] = Field(default=None, description="CO2 emissions g/km (WLTP)")
    reichweite_wltp_km: Optional[int] = Field(default=None, description="Electric range WLTP in km")
    verbrauch_l_100km: Optional[float] = Field(
        default=None, description="Fuel consumption l/100km combined"
    )
    sitzplaetze: int = Field(default=5, description="Number of seats")
    kofferraum_liter: int = Field(default=400, description="Trunk/boot volume in litres")
    laenge_mm: Optional[int] = Field(default=None, description="Vehicle length in mm")
    garantie_jahre: int = Field(default=2, description="Warranty in years")
    sicherheit_euro_ncap: Optional[int] = Field(default=None, description="Euro NCAP stars (0-5)")
    assistenzsysteme: list[str] = Field(
        default_factory=list, description="Driver assistance systems"
    )
    infotainment: Optional[str] = Field(default=None, description="Infotainment and connectivity")


class Pricing(BaseModel):
    """Vehicle pricing structure."""

    listenpreis_eur: float = Field(
        description="Manufacturer's recommended retail price (MSRP) in EUR"
    )
    basispreis_eur: Optional[float] = Field(
        default=None, description="Base price without optional extras"
    )
    leasing_rate_eur: Optional[float] = Field(
        default=None, description="Example monthly leasing rate"
    )
    bafa_foerderung_eur: Optional[float] = Field(
        default=None, description="Environmental incentive (if BEV/PHEV)"
    )
    unterhaltskosten_monat_eur: Optional[float] = Field(
        default=None, description="Estimated monthly operating costs"
    )
    restwert_36m_pct: Optional[float] = Field(
        default=None, description="Projected residual value after 36 months (%)"
    )


class Competitor(BaseModel):
    """Competing vehicle."""

    name: str
    brand: Optional[str] = None
    listenpreis_eur: Optional[float] = None
    leistung_kw: Optional[float] = None
    reichweite_wltp_km: Optional[int] = None
    market_position: Optional[str] = None
    key_differentiator: Optional[str] = None
