"""Industry Pack registry — discovery, loading, and dispatch."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import yaml

from .industry_packs.base import PackConfig, PersonaDefinition

_PACKS: dict[str, PackConfig] = {}
_loaded = False

PACKS_DIR = Path(__file__).parent / "industry_packs"


def _load_module_from_path(module_name: str, file_path: Path) -> Any:
    """Dynamically import a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_personas(personas_dir: Path) -> list[PersonaDefinition]:
    """Load all persona YAML files from a directory."""
    personas = []
    if not personas_dir.exists():
        return personas
    for yaml_file in sorted(personas_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        personas.append(PersonaDefinition(**data))
    return personas


def _discover_packs() -> None:
    """Scan industry_packs/ for pack.yaml files and load each pack."""
    global _loaded
    if _loaded:
        return

    for pack_dir in sorted(PACKS_DIR.iterdir()):
        if not pack_dir.is_dir():
            continue
        pack_yaml = pack_dir / "pack.yaml"
        if not pack_yaml.exists():
            continue

        with open(pack_yaml) as f:
            meta = yaml.safe_load(f)

        product_type = meta["product_type"]

        # Load models module
        models_path = pack_dir / "models.py"
        models_mod = None
        if models_path.exists():
            models_mod = _load_module_from_path(
                f"market_swarm.industry_packs.{pack_dir.name}.models",
                models_path,
            )

        # Load prompt builder module
        pb_path = pack_dir / "prompt_builder.py"
        prompt_builder = None
        if pb_path.exists():
            pb_mod = _load_module_from_path(
                f"market_swarm.industry_packs.{pack_dir.name}.prompt_builder",
                pb_path,
            )
            if hasattr(pb_mod, "prompt_builder"):
                prompt_builder = pb_mod.prompt_builder
            elif hasattr(pb_mod, "PromptBuilder"):
                prompt_builder = pb_mod.PromptBuilder()

        # Load personas
        personas = _load_personas(pack_dir / "personas")

        config = PackConfig(
            name=meta["name"],
            display_name=meta.get("display_name", meta["name"]),
            version=meta.get("version", "0.1.0"),
            product_type=product_type,
            description=meta.get("description", ""),
            attributes_model=getattr(models_mod, "Attributes", None) if models_mod else None,
            pricing_model=getattr(models_mod, "Pricing", None) if models_mod else None,
            competitor_model=getattr(models_mod, "Competitor", None) if models_mod else None,
            prompt_builder=prompt_builder,
            personas=personas,
            pack_dir=str(pack_dir),
        )

        _PACKS[product_type] = config

    _loaded = True


def get_pack(product_type: str) -> PackConfig:
    """Get a loaded pack by product_type. Triggers discovery if needed."""
    _discover_packs()
    if product_type not in _PACKS:
        available = ", ".join(_PACKS.keys()) or "(none)"
        raise ValueError(
            f"No Industry Pack found for product_type '{product_type}'. "
            f"Available packs: {available}"
        )
    return _PACKS[product_type]


def list_packs() -> list[PackConfig]:
    """List all discovered packs."""
    _discover_packs()
    return list(_PACKS.values())


def get_all_personas() -> list[PersonaDefinition]:
    """Get all personas from all packs."""
    _discover_packs()
    all_p = []
    for pack in _PACKS.values():
        all_p.extend(pack.personas)
    return all_p
