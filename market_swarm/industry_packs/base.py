"""Base classes and protocols for Industry Packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class PromptBuilder(Protocol):
    """Protocol for industry-specific prompt construction."""

    def build_evaluation_prompt(self, product: Any, focus_areas: list[str]) -> str: ...

    def build_panel_info(self, product: Any) -> dict[str, str]:
        """Return display info for Rich Panel.

        Keys: 'title', 'pricing_line', 'rate_label'.
        """
        ...


@dataclass
class PersonaDefinition:
    """A persona loaded from YAML."""

    name: str
    type: str
    retailer: str | None = None
    system_prompt: str = ""
    evaluation_criteria: list[str] = field(default_factory=list)

    def to_system_message(self) -> str:
        return self.system_prompt


@dataclass
class PackConfig:
    """Metadata and components of an Industry Pack."""

    name: str
    display_name: str
    version: str
    product_type: str
    description: str = ""

    attributes_model: type[BaseModel] | None = None
    pricing_model: type[BaseModel] | None = None
    competitor_model: type[BaseModel] | None = None

    prompt_builder: PromptBuilder | None = None
    personas: list[PersonaDefinition] = field(default_factory=list)
    pack_dir: str = ""
