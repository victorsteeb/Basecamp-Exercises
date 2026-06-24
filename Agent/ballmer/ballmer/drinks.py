"""The drink library — data model + recipe-level ethanol math.

Kept separate from the BAC engine and the agent so the menu can grow without
touching either. A drink is defined by its INGREDIENTS, never a flat ABV, so the
ethanol content is computed from the actual recipe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import config
from .bac_model import ethanol_grams


@dataclass(frozen=True)
class Ingredient:
    name: str
    oz: float
    abv: float   # fraction, e.g. 0.40 for 80-proof

    @property
    def volume_ml(self) -> float:
        return self.oz * config.OZ_TO_ML

    @property
    def ethanol_g(self) -> float:
        return ethanol_grams(self.volume_ml, self.abv)


@dataclass(frozen=True)
class Drink:
    name: str
    ingredients: tuple[Ingredient, ...]
    category: str = ""
    notes: str = ""
    vibe_score: int = 5   # 1-10 subjective desirability for a Ballmer Peak session

    @property
    def total_ethanol_g(self) -> float:
        """Total pure ethanol in grams: sum(volume_ml * abv * 0.789) over ingredients."""
        return sum(ing.ethanol_g for ing in self.ingredients)

    @property
    def standard_drinks(self) -> float:
        """Ethanol expressed in US standard-drink units (14 g each)."""
        return self.total_ethanol_g / config.STANDARD_DRINK_G

    @property
    def is_alcoholic(self) -> bool:
        return self.total_ethanol_g > 1e-6


def _drink_from_dict(d: dict) -> Drink:
    ings = tuple(Ingredient(name=i["name"], oz=i["oz"], abv=i["abv"])
                 for i in d["ingredients"])
    return Drink(name=d["name"], ingredients=ings,
                 category=d.get("category", ""), notes=d.get("notes", ""),
                 vibe_score=int(d.get("vibe", 5)))


def load_library(path: str | Path = "drink-library.json") -> list[Drink]:
    """Load the menu from the JSON state file into Drink objects."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_drink_from_dict(d) for d in data["drinks"]]


def find_drink(library: list[Drink], name: str) -> Drink | None:
    for d in library:
        if d.name.lower() == name.lower():
            return d
    return None
