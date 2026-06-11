"""Catalogues of normalized rolled steel profiles.

Families covered:
    IPE  — narrow-flange I-beams (Euronorm 19-57 / DIN 1025-5)
    HEA  — wide-flange I-beams, light series (Euronorm 53)
    HEB  — wide-flange I-beams, normal series (Euronorm 53)
    UPN  — U-channels
    SHS  — square hollow sections (EN 10219)
    CHS  — circular hollow sections (EN 10210)

Tabulated values come from the official catalogues (DIN / EN). We deliberately
store the NORMALIZED values (Iy, Wy, A, mass) rather than recompute them from
a naive geometry: real profiles have fillets and tapered flanges that change
Iy by a few percent.

A CatalogProfile exposes the same `area / inertia / extreme_fiber /
section_modulus` interface as the geometric Section classes, so it plugs
directly into `Beam` (the discriminated `Section` union in `sections.py`
includes it).
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------------------------------------------------------------------------- #
# CatalogProfile model                                                         #
# --------------------------------------------------------------------------- #
class CatalogProfile(BaseModel):
    """A normalized rolled profile (e.g. IPE 160, HEA 200, SHS 100×5).

    Stored dimensions are in their tabular units (mm, cm², cm⁴, cm³, kg/m).
    The `area`, `inertia`, `section_modulus`, `extreme_fiber` properties
    return SI values so the beam engine consumes them transparently.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["profile"] = "profile"
    family: str = Field(..., description="Family : 'IPE', 'HEA', 'HEB', 'UPN', 'SHS', 'CHS'")
    designation: str = Field(..., description="Full designation, e.g. 'IPE 160' or 'SHS 100×5'")
    h_mm: float = Field(..., description="Overall depth h (or outer dimension), in mm")
    b_mm: float = Field(..., description="Flange width b (or outer dim for hollow), in mm")
    area_cm2: float = Field(..., description="Cross-section area A, in cm²")
    Iy_cm4: float = Field(..., description="Second moment of area about strong axis y, in cm⁴")
    Wy_cm3: float = Field(..., description="Elastic section modulus W = I/v, in cm³")
    mass_kg_per_m: float = Field(..., description="Linear mass, in kg/m")

    @field_validator("h_mm", "b_mm", "area_cm2", "Iy_cm4", "Wy_cm3", "mass_kg_per_m")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("profile property must be > 0")
        return v

    # ---- SI-facing properties (match the Section informal interface) ------
    @property
    def area(self) -> float:               # m²
        return self.area_cm2 * 1e-4

    @property
    def inertia(self) -> float:            # m⁴
        return self.Iy_cm4 * 1e-8

    @property
    def section_modulus(self) -> float:    # m³
        return self.Wy_cm3 * 1e-6

    @property
    def extreme_fiber(self) -> float:      # m
        return (self.h_mm / 2.0) * 1e-3


# --------------------------------------------------------------------------- #
# Generic builder                                                              #
# --------------------------------------------------------------------------- #
def _mk(family, designation, h, b, A, Iy, Wy, mass) -> CatalogProfile:
    return CatalogProfile(
        family=family, designation=designation,
        h_mm=h, b_mm=b,
        area_cm2=A, Iy_cm4=Iy, Wy_cm3=Wy,
        mass_kg_per_m=mass,
    )


# --------------------------------------------------------------------------- #
# IPE — Euronorm 19-57 / DIN 1025-5                                            #
# --------------------------------------------------------------------------- #
IPE_CATALOG: list[CatalogProfile] = [
    _mk("IPE", "IPE 80",  80,  46,  7.64,  80.1,   20.0,  6.0),
    _mk("IPE", "IPE 100", 100, 55,  10.3,  171.0,  34.2,  8.1),
    _mk("IPE", "IPE 120", 120, 64,  13.2,  318.0,  53.0,  10.4),
    _mk("IPE", "IPE 140", 140, 73,  16.4,  541.0,  77.3,  12.9),
    _mk("IPE", "IPE 160", 160, 82,  20.1,  869.0,  109.0, 15.8),
    _mk("IPE", "IPE 180", 180, 91,  23.9,  1317.0, 146.0, 18.8),
    _mk("IPE", "IPE 200", 200, 100, 28.5,  1943.0, 194.0, 22.4),
    _mk("IPE", "IPE 220", 220, 110, 33.4,  2772.0, 252.0, 26.2),
    _mk("IPE", "IPE 240", 240, 120, 39.1,  3892.0, 324.0, 30.7),
]


# --------------------------------------------------------------------------- #
# HEA — Euronorm 53, série légère                                              #
# --------------------------------------------------------------------------- #
HEA_CATALOG: list[CatalogProfile] = [
    _mk("HEA", "HEA 100", 96,  100, 21.2,  349.0,   72.8,  16.7),
    _mk("HEA", "HEA 120", 114, 120, 25.3,  606.0,   106.0, 19.9),
    _mk("HEA", "HEA 140", 133, 140, 31.4,  1033.0,  155.0, 24.7),
    _mk("HEA", "HEA 160", 152, 160, 38.8,  1673.0,  220.0, 30.4),
    _mk("HEA", "HEA 180", 171, 180, 45.3,  2510.0,  294.0, 35.5),
    _mk("HEA", "HEA 200", 190, 200, 53.8,  3692.0,  389.0, 42.3),
    _mk("HEA", "HEA 220", 210, 220, 64.3,  5410.0,  515.0, 50.5),
    _mk("HEA", "HEA 240", 230, 240, 76.8,  7763.0,  675.0, 60.3),
    _mk("HEA", "HEA 260", 250, 260, 86.8,  10450.0, 836.0, 68.2),
    _mk("HEA", "HEA 280", 270, 280, 97.3,  13670.0, 1013.0, 76.4),
    _mk("HEA", "HEA 300", 290, 300, 112.0, 18260.0, 1260.0, 88.3),
]


# --------------------------------------------------------------------------- #
# HEB — Euronorm 53, série normale                                             #
# --------------------------------------------------------------------------- #
HEB_CATALOG: list[CatalogProfile] = [
    _mk("HEB", "HEB 100", 100, 100, 26.0,  450.0,   89.9,   20.4),
    _mk("HEB", "HEB 120", 120, 120, 34.0,  864.0,   144.0,  26.7),
    _mk("HEB", "HEB 140", 140, 140, 43.0,  1509.0,  216.0,  33.7),
    _mk("HEB", "HEB 160", 160, 160, 54.3,  2492.0,  311.0,  42.6),
    _mk("HEB", "HEB 180", 180, 180, 65.3,  3831.0,  426.0,  51.2),
    _mk("HEB", "HEB 200", 200, 200, 78.1,  5696.0,  570.0,  61.3),
    _mk("HEB", "HEB 220", 220, 220, 91.0,  8091.0,  736.0,  71.5),
    _mk("HEB", "HEB 240", 240, 240, 106.0, 11260.0, 938.0,  83.2),
    _mk("HEB", "HEB 260", 260, 260, 118.0, 14920.0, 1148.0, 93.0),
    _mk("HEB", "HEB 280", 280, 280, 131.0, 19270.0, 1376.0, 103.0),
    _mk("HEB", "HEB 300", 300, 300, 149.0, 25170.0, 1678.0, 117.0),
]


# --------------------------------------------------------------------------- #
# UPN — U-channels                                                             #
# --------------------------------------------------------------------------- #
UPN_CATALOG: list[CatalogProfile] = [
    _mk("UPN", "UPN 80",  80,  45, 8.0,   106.0,  26.5, 6.3),
    _mk("UPN", "UPN 100", 100, 50, 10.6,  206.0,  41.2, 8.3),
    _mk("UPN", "UPN 120", 120, 55, 13.4,  364.0,  60.7, 10.5),
    _mk("UPN", "UPN 140", 140, 60, 16.4,  605.0,  86.4, 12.9),
    _mk("UPN", "UPN 160", 160, 65, 19.5,  925.0,  116.0, 15.3),
    _mk("UPN", "UPN 180", 180, 70, 23.0,  1350.0, 150.0, 18.1),
    _mk("UPN", "UPN 200", 200, 75, 26.2,  1910.0, 191.0, 20.6),
    _mk("UPN", "UPN 220", 220, 80, 29.4,  2690.0, 245.0, 23.1),
    _mk("UPN", "UPN 240", 240, 85, 33.2,  3600.0, 300.0, 26.1),
]


# --------------------------------------------------------------------------- #
# SHS — square hollow sections (EN 10219)                                      #
# (h = b = side length)                                                        #
# --------------------------------------------------------------------------- #
SHS_CATALOG: list[CatalogProfile] = [
    _mk("SHS", "SHS 40×3",  40,  40,  4.39, 10.7,   5.35, 3.45),
    _mk("SHS", "SHS 50×3",  50,  50,  5.59, 21.8,   8.70, 4.39),
    _mk("SHS", "SHS 60×4",  60,  60,  8.69, 50.5,   16.8, 6.82),
    _mk("SHS", "SHS 80×4",  80,  80,  11.9, 121.0,  30.3, 9.35),
    _mk("SHS", "SHS 100×5", 100, 100, 18.5, 291.0,  58.2, 14.5),
    _mk("SHS", "SHS 120×5", 120, 120, 22.5, 513.0,  85.5, 17.7),
    _mk("SHS", "SHS 150×6", 150, 150, 33.5, 1150.0, 153.0, 26.3),
    _mk("SHS", "SHS 200×8", 200, 200, 59.6, 3560.0, 356.0, 46.8),
]


# --------------------------------------------------------------------------- #
# CHS — circular hollow sections (EN 10210)                                    #
# (h = b = outer diameter)                                                     #
# --------------------------------------------------------------------------- #
CHS_CATALOG: list[CatalogProfile] = [
    _mk("CHS", "CHS 42.4×3",  42.4,  42.4,  3.73, 8.07,    3.81,  2.93),
    _mk("CHS", "CHS 48.3×3",  48.3,  48.3,  4.28, 12.2,    5.04,  3.56),
    _mk("CHS", "CHS 60.3×4",  60.3,  60.3,  7.07, 31.0,    10.3,  5.55),
    _mk("CHS", "CHS 76.1×4",  76.1,  76.1,  9.07, 64.0,    16.8,  7.11),
    _mk("CHS", "CHS 88.9×5",  88.9,  88.9,  13.2, 128.0,   28.7,  10.3),
    _mk("CHS", "CHS 114.3×5", 114.3, 114.3, 17.2, 278.0,   48.7,  13.5),
    _mk("CHS", "CHS 139.7×6", 139.7, 139.7, 25.2, 704.0,   101.0, 19.8),
    _mk("CHS", "CHS 168.3×6", 168.3, 168.3, 30.6, 1240.0,  147.0, 24.0),
]


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
CATALOGS: dict[str, list[CatalogProfile]] = {
    "IPE": IPE_CATALOG,
    "HEA": HEA_CATALOG,
    "HEB": HEB_CATALOG,
    "UPN": UPN_CATALOG,
    "SHS": SHS_CATALOG,
    "CHS": CHS_CATALOG,
}


def get_catalog(name: str) -> list[CatalogProfile]:
    """Lookup a single catalogue by family name. Raises ValueError if unknown."""
    if name not in CATALOGS:
        known = ", ".join(sorted(CATALOGS))
        raise ValueError(f"unknown profile catalog '{name}'. Known: {known}") from None
    return CATALOGS[name]


def get_all_catalogs() -> dict[str, list[CatalogProfile]]:
    """Return every catalogue keyed by family name."""
    return dict(CATALOGS)


def get_combined_catalog(
    families: Optional[List[str]] = None,
) -> list[CatalogProfile]:
    """Merge several catalogues into one list sorted by ascending mass.

    Used by the multi-family optimization. Duplicate designations across
    families are kept distinct (different physical sections).

    Raises ValueError if any family name is unknown.
    """
    if not families:
        # Default to every catalogue
        families = list(CATALOGS)
    unknown = [f for f in families if f not in CATALOGS]
    if unknown:
        known = ", ".join(sorted(CATALOGS))
        raise ValueError(
            f"unknown profile catalog(s): {unknown}. Known: {known}"
        )

    combined: list[CatalogProfile] = []
    for fam in families:
        combined.extend(CATALOGS[fam])
    combined.sort(key=lambda p: p.mass_kg_per_m)
    return combined
