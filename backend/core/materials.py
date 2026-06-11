"""Engineering material library.

A Material carries the properties needed for elementary mechanical design:

    family          : category (steel, cast iron, aluminium, stainless, other)
    E               : Young's modulus           (Pa)
    Re              : nominal yield strength    (Pa) — may be None for materials
                      without a nominal yield (typically grey cast iron)
    Rm              : ultimate tensile strength (Pa)
    sigma_D         : fatigue limit, alternating bending (Pa) —
                      auto-derived from Rm × family ratio if not given
    poisson_ratio ν : Poisson's ratio  (default 0.30)
    density ρ       : density          (kg/m³)

The catalogue covers the materials commonly encountered in a French
mechanical design office: EN 10025 structural steels, machine steels
(quenched/tempered, case-hardened), 304L / 316L stainless, FGL / FGS cast
irons, and common aluminium alloys (AU4G, AS7G, 6060, 6061, 7075).

For materials without a nominal yield (FGL200), `Re_effective` returns
Rm/3 — a conventional design value — so the beam and shaft engines can
compute a safety factor unchanged.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# --------------------------------------------------------------------------- #
# Family + family-driven fatigue ratio                                         #
# --------------------------------------------------------------------------- #
class MaterialFamily(str, Enum):
    STEEL = "steel"
    CAST_IRON = "cast_iron"
    ALUMINUM = "aluminum"
    STAINLESS = "stainless"
    OTHER = "other"


FATIGUE_RATIO_BY_FAMILY: dict[MaterialFamily, float] = {
    MaterialFamily.STEEL:     0.45,
    MaterialFamily.STAINLESS: 0.45,
    MaterialFamily.CAST_IRON: 0.36,
    MaterialFamily.ALUMINUM:  0.40,
    MaterialFamily.OTHER:     0.40,
}


# --------------------------------------------------------------------------- #
# Contact-fatigue (Hertz/pitting) limit estimate, used by the gear module      #
#                                                                              #
# σ_H_lim ≈ 0.58 × Rm + 200 MPa is a common Niemann-style estimate for         #
# through-hardened steel gears, relating the Hertzian pitting limit to the     #
# tensile strength (via HB ≈ Rm/3.45 and σ_Hlim ≈ 2·HB + 200 MPa). Used as a   #
# generic, indicative admissible contact stress when no dedicated gear-grade   #
# value is available.                                                          #
# --------------------------------------------------------------------------- #
CONTACT_FATIGUE_RATIO = 0.58
CONTACT_FATIGUE_OFFSET_PA = 200e6


# --------------------------------------------------------------------------- #
# Material model                                                               #
# --------------------------------------------------------------------------- #
class Material(BaseModel):
    """Linear elastic isotropic engineering material (SI units)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Designation (e.g. 'S355', '42CrMo4')")
    family: MaterialFamily = Field(..., description="Family / category")
    E: float = Field(..., gt=0, description="Young's modulus E, Pa")
    Re: Optional[float] = Field(
        ...,
        description=(
            "Yield strength Re, Pa. May be None for materials without a "
            "nominal yield (e.g. grey cast iron) — in that case "
            "`Re_effective` returns Rm/3 as a conventional design value."
        ),
    )
    Rm: float = Field(..., gt=0, description="Ultimate tensile strength Rm, Pa")
    sigma_D: Optional[float] = Field(
        None,
        description=(
            "Fatigue limit σ_D in alternating bending, Pa. "
            "Auto-derived from Rm × family ratio if not provided."
        ),
    )
    poisson_ratio: float = Field(
        0.30, gt=0, lt=0.5,
        description="Poisson's ratio ν (default 0.30 steel, 0.33 aluminium).",
    )
    density: float = Field(..., gt=0, description="Density ρ, kg/m³")

    @field_validator("Re")
    @classmethod
    def _re_positive_or_none(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Re must be > 0 when given (or None for no nominal yield)")
        return v

    @model_validator(mode="before")
    @classmethod
    def _derive_sigma_D(cls, data):
        """If sigma_D is missing/None, derive from Rm × family ratio."""
        if not isinstance(data, dict):
            return data
        if data.get("sigma_D") is not None:
            return data
        if "Rm" not in data or "family" not in data:
            return data
        fam = data["family"]
        if not isinstance(fam, MaterialFamily):
            try:
                fam = MaterialFamily(fam)
            except ValueError:
                return data
        ratio = FATIGUE_RATIO_BY_FAMILY.get(fam, 0.40)
        rm = data["Rm"]
        if isinstance(rm, (int, float)) and rm > 0:
            data["sigma_D"] = float(rm) * ratio
        return data

    @property
    def Re_effective(self) -> float:
        """Yield-equivalent value actually used in stress checks.

        Returns Re when defined, else Rm/3 (conventional design value for
        grey cast iron which has no nominal yield).
        """
        if self.Re is None:
            return self.Rm / 3.0
        return self.Re

    @property
    def sigma_H_lim(self) -> float:
        """Estimated contact-fatigue (pitting) limit, Pa.

        See `CONTACT_FATIGUE_RATIO` / `CONTACT_FATIGUE_OFFSET_PA` for the
        empirical relation used.
        """
        return CONTACT_FATIGUE_RATIO * self.Rm + CONTACT_FATIGUE_OFFSET_PA


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
_STEEL = MaterialFamily.STEEL
_CAST_IRON = MaterialFamily.CAST_IRON
_ALUMINUM = MaterialFamily.ALUMINUM
_STAINLESS = MaterialFamily.STAINLESS


def _m(
    *, name, family, E, Re, Rm, density, poisson_ratio=None
) -> Material:
    """Tiny builder so the catalogue stays one entry per line."""
    kw = dict(name=name, family=family, E=E, Re=Re, Rm=Rm, density=density)
    if poisson_ratio is not None:
        kw["poisson_ratio"] = poisson_ratio
    return Material(**kw)


_CATALOGUE: list[Material] = [
    # -- Construction steels (EN 10025) -----------------------------------
    _m(name="S235", family=_STEEL, E=210e9, Re=235e6, Rm=360e6, density=7850),
    _m(name="S275", family=_STEEL, E=210e9, Re=275e6, Rm=430e6, density=7850),
    _m(name="S355", family=_STEEL, E=210e9, Re=355e6, Rm=510e6, density=7850),
    _m(name="S460", family=_STEEL, E=210e9, Re=460e6, Rm=550e6, density=7850),

    # -- Machine steels (mi-durs / traités / cémentés) --------------------
    _m(name="C45",     family=_STEEL, E=210e9, Re=390e6, Rm=620e6, density=7850),
    _m(name="C45E",    family=_STEEL, E=210e9, Re=490e6, Rm=700e6, density=7850),
    _m(name="42CrMo4", family=_STEEL, E=210e9, Re=650e6, Rm=900e6, density=7850),
    _m(name="16NiCr6", family=_STEEL, E=210e9, Re=700e6, Rm=950e6, density=7850),

    # -- Stainless steels --------------------------------------------------
    _m(name="304L", family=_STAINLESS, E=196e9, Re=170e6, Rm=485e6, density=7900),
    _m(name="316L", family=_STAINLESS, E=196e9, Re=170e6, Rm=485e6, density=7980),

    # -- Cast irons --------------------------------------------------------
    # FGL200: grey cast iron has no nominal yield → Re=None, Re_effective = Rm/3.
    _m(name="FGL200", family=_CAST_IRON, E=110e9, Re=None,  Rm=200e6, density=7200, poisson_ratio=0.27),
    _m(name="FGS500", family=_CAST_IRON, E=170e9, Re=320e6, Rm=500e6, density=7100, poisson_ratio=0.27),

    # -- Aluminium alloys --------------------------------------------------
    _m(name="AU4G",    family=_ALUMINUM, E=72e9, Re=275e6, Rm=425e6, density=2790, poisson_ratio=0.33),
    _m(name="AS7G",    family=_ALUMINUM, E=72e9, Re=210e6, Rm=310e6, density=2680, poisson_ratio=0.33),
    _m(name="AL6060",  family=_ALUMINUM, E=69e9, Re=160e6, Rm=215e6, density=2700, poisson_ratio=0.33),
    _m(name="6061-T6", family=_ALUMINUM, E=69e9, Re=276e6, Rm=310e6, density=2700, poisson_ratio=0.33),
    _m(name="7075-T6", family=_ALUMINUM, E=72e9, Re=503e6, Rm=572e6, density=2810, poisson_ratio=0.33),
]


MATERIALS: dict[str, Material] = {m.name: m for m in _CATALOGUE}


def get_material(name: str) -> Material:
    """Lookup a material by name. Raises ValueError if unknown."""
    if name not in MATERIALS:
        known = ", ".join(sorted(MATERIALS))
        raise ValueError(f"unknown material '{name}'. Known: {known}") from None
    return MATERIALS[name]


def list_materials(family: Optional[MaterialFamily] = None) -> List[Material]:
    """Return the materials of the catalogue, optionally filtered by family."""
    if family is None:
        return list(MATERIALS.values())
    return [m for m in MATERIALS.values() if m.family == family]
