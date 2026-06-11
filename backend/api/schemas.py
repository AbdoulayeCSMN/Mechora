"""API-facing Pydantic schemas.

Engineering units are used at the boundary (mm, kN, kN/m, MPa, kN*m).
Conversion to SI happens in `routes.py` before calling `core`.
Field names carry their unit as a suffix (`_mm`, `_kN`, `_m`, ...) so the
contract is self-documenting in /docs.
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------------------------------------------------------------------------- #
# Section inputs (dimensions in mm)                                            #
# --------------------------------------------------------------------------- #
class RectangularSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["rectangular"] = "rectangular"
    width_mm: float = Field(..., gt=0, description="Largeur b, en mm (> 0)")
    height_mm: float = Field(..., gt=0, description="Hauteur h, en mm (> 0)")


class CircularSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["circular"] = "circular"
    diameter_mm: float = Field(..., gt=0, description="Diamètre d, en mm (> 0)")


class TubeSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["tube"] = "tube"
    outer_diameter_mm: float = Field(..., gt=0, description="Diamètre extérieur D, en mm")
    inner_diameter_mm: float = Field(..., gt=0, description="Diamètre intérieur d, en mm")


SectionInput = Annotated[
    Union[RectangularSectionIn, CircularSectionIn, TubeSectionIn],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Load inputs                                                                  #
# --------------------------------------------------------------------------- #
class PointLoadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["point"] = "point"
    magnitude_kN: float = Field(..., gt=0, description="Charge ponctuelle descendante, en kN (> 0)")
    position_m: float = Field(..., ge=0, description="Position depuis l'extrémité gauche, en m (>= 0)")


class DistributedLoadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["distributed"] = "distributed"
    magnitude_kN_per_m: float = Field(..., gt=0, description="Intensité linéique q, en kN/m (> 0)")
    start_m: float = Field(..., ge=0, description="Début du tronçon chargé, en m")
    end_m: float = Field(..., gt=0, description="Fin du tronçon chargé, en m (> start)")


LoadInput = Annotated[
    Union[PointLoadIn, DistributedLoadIn],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Beam request                                                                 #
# --------------------------------------------------------------------------- #
class BeamRequest(BaseModel):
    """Requête de calcul d'une poutre en flexion."""

    model_config = ConfigDict(extra="forbid")

    length_m: float = Field(..., gt=0, description="Longueur de la poutre L, en m (> 0)")
    material: str = Field(..., description="Nom du matériau (ex. 'S235', 'S355', 'AL6060')")
    section: SectionInput
    support: Literal["simply_supported", "cantilever"] = Field(
        ..., description="Type d'appui : appui simple ou encastrement (console)"
    )
    loads: List[LoadInput] = Field(
        default_factory=list,
        description="Charges appliquées : ponctuelles (kN) ou réparties (kN/m)",
    )

    @field_validator("material")
    @classmethod
    def _strip_material(cls, v: str) -> str:
        return v.strip()


# --------------------------------------------------------------------------- #
# Beam response                                                                #
# --------------------------------------------------------------------------- #
class SectionProperties(BaseModel):
    area_mm2: float = Field(..., description="Aire de section A, en mm²")
    inertia_mm4: float = Field(..., description="Moment d'inertie I, en mm⁴")
    extreme_fiber_mm: float = Field(..., description="Distance fibre extrême v, en mm")
    section_modulus_mm3: float = Field(..., description="Module de flexion W = I/v, en mm³")


class AdviceOut(BaseModel):
    """Diagnostic décisionnel (transformation des chiffres en conseil)."""

    diagnostic: str = Field(..., description="Phrase courte expliquant ce qui limite la poutre")
    cause: str = Field(..., description="Valeur(s) chiffrée(s) qui posent problème")
    conseil: str = Field(..., description="Action concrète recommandée")
    facteur_limitant: Literal["contrainte", "flèche", "les deux", "aucun"] = Field(
        ..., description="Critère qui dimensionne la poutre"
    )


class BeamResponse(BaseModel):
    """Résultats du calcul. Unités ingénieur (kN, m, mm, MPa)."""

    section_properties: SectionProperties
    reactions_kN: dict[str, float] = Field(
        ..., description="Réactions d'appui (kN pour les forces, kN·m pour le moment encastrement)"
    )
    x_m: List[float] = Field(..., description="Abscisses d'échantillonnage le long de la poutre, en m")
    V_kN: List[float] = Field(..., description="Effort tranchant V(x), en kN")
    M_kNm: List[float] = Field(..., description="Moment fléchissant M(x), en kN·m")
    M_max_kNm: float = Field(..., description="Moment fléchissant max (|M|), en kN·m")
    sigma_max_MPa: float = Field(..., description="Contrainte normale max σ = M_max / W, en MPa")
    f_max_mm: float = Field(..., description="Flèche maximale, en mm")
    Cs: float = Field(..., description="Coefficient de sécurité Cs = Re / σ_max (sans unité)")
    verdict: str = Field(..., description="Verdict : Sous-dimensionné / Limite / OK / Surdimensionné")
    advice: AdviceOut = Field(..., description="Diagnostic décisionnel et conseil actionnable")


# --------------------------------------------------------------------------- #
# Catalog optimization — request                                               #
# --------------------------------------------------------------------------- #
class BeamOptimizeRequest(BaseModel):
    """Requête de recherche du profilé normalisé le plus léger satisfaisant
    Cs >= target_safety_factor ET flèche <= L / deflection_ratio."""

    model_config = ConfigDict(extra="forbid")

    length_m: float = Field(..., gt=0, description="Longueur de la poutre L, en m")
    material: str = Field(..., description="Nom du matériau (ex. 'S235', 'S355', 'AL6060')")
    support: Literal["simply_supported", "cantilever"] = Field(
        ..., description="Type d'appui"
    )
    loads: List[LoadInput] = Field(
        default_factory=list,
        description="Charges appliquées : ponctuelles (kN) ou réparties (kN/m)",
    )
    target_safety_factor: float = Field(
        ..., gt=0,
        description="Coefficient de sécurité cible Cs (sans unité, > 0)",
    )
    deflection_ratio: float = Field(
        200.0, gt=0,
        description="Flèche admissible = L / deflection_ratio (ex. 200 pour L/200)",
    )
    catalogs: List[str] = Field(
        default_factory=lambda: ["IPE", "HEA"],
        description=(
            "Catalogues à fusionner pour la recherche multi-famille. "
            "Valeurs possibles : 'IPE', 'HEA', 'HEB', 'UPN', 'SHS', 'CHS'."
        ),
        min_length=1,
    )

    @field_validator("material")
    @classmethod
    def _strip_mat(cls, v: str) -> str:
        return v.strip()

    @field_validator("catalogs")
    @classmethod
    def _strip_catalogs(cls, v: List[str]) -> List[str]:
        return [c.strip() for c in v]


# --------------------------------------------------------------------------- #
# Catalog optimization — response                                              #
# --------------------------------------------------------------------------- #
class OptimalProfileOut(BaseModel):
    """Profilé optimal retenu (présenté en unités ingénieur)."""

    designation: str = Field(..., description="Désignation (ex. 'IPE 160')")
    family: str = Field(..., description="Famille du profilé (ex. 'IPE')")
    mass_kg_per_m: float = Field(..., description="Masse linéique, en kg/m")
    h_mm: float = Field(..., description="Hauteur h, en mm")
    b_mm: float = Field(..., description="Largeur b, en mm")
    area_mm2: float = Field(..., description="Aire A, en mm²")
    inertia_mm4: float = Field(..., description="Moment d'inertie Iy, en mm⁴")
    section_modulus_mm3: float = Field(..., description="Module de flexion Wy, en mm³")


class ProfileEvalOut(BaseModel):
    """Évaluation d'un profilé candidat (pour le tableau comparatif)."""

    designation: str
    family: str
    mass_kg_per_m: float
    status: Literal["OK", "Cs_insuffisant", "fleche_excessive"]
    Cs: float
    f_max_mm: float
    sigma_max_MPa: float
    M_max_kNm: float
    reason: Optional[str] = Field(None, description="Explication quand status != 'OK'")


class BeamOptimizeResponse(BaseModel):
    """Résultat d'optimisation : profilé optimal + table des candidats évalués."""

    found: bool = Field(..., description="True si un profilé satisfait les critères")
    optimal: Optional[OptimalProfileOut] = None
    result: Optional[BeamResponse] = Field(
        None, description="Résultats du calcul pour le profilé optimal (None si aucun)",
    )
    evaluations: List[ProfileEvalOut] = Field(
        ..., description="Tous les profilés du catalogue évalués, avec leur statut",
    )
    deflection_limit_mm: float = Field(..., description="Flèche admissible utilisée, en mm")
    target_safety_factor: float = Field(..., description="Cs cible utilisé")
    advice: AdviceOut = Field(..., description="Diagnostic décisionnel sur le résultat")


# --------------------------------------------------------------------------- #
# Shaft module — request                                                       #
# --------------------------------------------------------------------------- #
class ShaftRequest(BaseModel):
    """Requête de calcul d'un arbre en flexion + torsion combinées."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["solid", "hollow"] = Field(..., description="Arbre plein ou creux")
    d_ext_mm: float = Field(..., gt=0, description="Diamètre extérieur, en mm")
    d_int_mm: float = Field(
        0.0, ge=0,
        description="Diamètre intérieur, en mm (0 pour un arbre plein)",
    )
    material: str = Field(..., description="Nom du matériau (S235, S355, AL6060)")
    Mf_Nm: float = Field(..., ge=0, description="Moment fléchissant Mf, en N·m (≥ 0)")
    Mt_Nm: float = Field(..., ge=0, description="Moment de torsion Mt, en N·m (≥ 0)")

    @field_validator("material")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


# --------------------------------------------------------------------------- #
# Shaft module — response                                                      #
# --------------------------------------------------------------------------- #
class ShaftSectionProperties(BaseModel):
    type: Literal["solid", "hollow"]
    d_ext_mm: float = Field(..., description="Diamètre extérieur, en mm")
    d_int_mm: float = Field(..., description="Diamètre intérieur, en mm")
    area_mm2: float = Field(..., description="Aire de section A, en mm²")
    W_f_mm3: float = Field(..., description="Module de flexion W_f = π·d³/32, en mm³")
    W_t_mm3: float = Field(..., description="Module de torsion W_t = π·d³/16, en mm³")


class ShaftResponse(BaseModel):
    """Résultat de calcul d'un arbre. Unités ingénieur (mm, MPa, N·m)."""

    section: ShaftSectionProperties
    sigma_f_MPa: float = Field(..., description="Contrainte de flexion σ_f = Mf/W_f")
    tau_MPa: float = Field(..., description="Contrainte de torsion τ = Mt/W_t")
    sigma_eq_MPa: float = Field(
        ..., description="Contrainte équivalente de Von Mises √(σ_f² + 3τ²)"
    )
    Cs: float = Field(..., description="Coefficient de sécurité Cs = Re / σ_eq")
    verdict: str = Field(..., description="Verdict (Sous-dimensionné / Limite / OK / Surdimensionné)")
    advice: AdviceOut = Field(..., description="Diagnostic décisionnel")


# --------------------------------------------------------------------------- #
# Shaft optimization                                                           #
# --------------------------------------------------------------------------- #
class ShaftOptimizeRequest(BaseModel):
    """Recherche du plus petit diamètre satisfaisant Cs ≥ target_cs."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["solid", "hollow"] = Field(..., description="Arbre plein ou creux")
    material: str = Field(..., description="Nom du matériau")
    Mf_Nm: float = Field(..., ge=0, description="Moment fléchissant Mf, en N·m")
    Mt_Nm: float = Field(..., ge=0, description="Moment de torsion Mt, en N·m")
    target_cs: float = Field(..., gt=0, description="Coefficient de sécurité cible")
    d_min_mm: float = Field(10.0, gt=0, description="Diamètre minimum à essayer, en mm")
    d_max_mm: float = Field(200.0, gt=0, description="Diamètre maximum à essayer, en mm")
    step_mm: float = Field(1.0, gt=0, description="Pas de diamètre, en mm")
    d_int_ratio: float = Field(
        0.7, gt=0, lt=1,
        description="Pour creux uniquement : d_int = d_int_ratio × d_ext",
    )

    @field_validator("material")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ShaftOptimizeResponse(BaseModel):
    found: bool = Field(..., description="True si un diamètre satisfait Cs cible")
    d_optimal_mm: Optional[float] = Field(
        None, description="Diamètre extérieur optimal en mm (None si aucun)"
    )
    result: Optional[ShaftResponse] = Field(
        None, description="Résultat de calcul pour le diamètre optimal"
    )
    target_safety_factor: float
    d_min_mm: float
    d_max_mm: float
    step_mm: float
    candidates_evaluated: int = Field(
        ..., description="Nombre de diamètres essayés avant de trouver (ou jusqu'au max)"
    )
    advice: AdviceOut = Field(..., description="Diagnostic décisionnel sur le résultat")


# --------------------------------------------------------------------------- #
# Key module — request / response                                              #
# --------------------------------------------------------------------------- #
class KeyRequest(BaseModel):
    """Vérification d'une clavette parallèle (ISO 773)."""

    model_config = ConfigDict(extra="forbid")

    shaft_diameter_mm: float = Field(..., gt=0, description="Diamètre de l'arbre, mm (6–75)")
    Mt_Nm: float = Field(..., gt=0, description="Couple transmis Mt, N·m (> 0)")
    material_shaft: str = Field(..., description="Matériau de l'arbre (et de la clavette)")
    hub_material: Literal["steel", "cast_iron", "aluminum"] = Field(
        ..., description="Matériau du moyeu (détermine σ_m_admissible)"
    )
    l_total_mm: float = Field(..., gt=0, description="Longueur totale de la clavette, mm")

    @field_validator("material_shaft")
    @classmethod
    def _strip_mat(cls, v: str) -> str:
        return v.strip()


class KeySectionOut(BaseModel):
    b_mm: float
    h_mm: float
    l_total_mm: float
    l_active_mm: float


class KeyResponse(BaseModel):
    section: KeySectionOut
    shaft_diameter_mm: float
    Mt_Nm: float
    hub_material: Literal["steel", "cast_iron", "aluminum"]
    tau_MPa: float
    sigma_m_MPa: float
    Re_shear_MPa: float
    sigma_m_adm_MPa: float
    Cs_shear: float
    Cs_bearing: float
    Cs: float
    limiting_criterion: Literal["cisaillement", "matage"]
    verdict: str
    advice: AdviceOut


class KeyOptimizeRequest(BaseModel):
    """Cherche la plus petite longueur de clavette satisfaisant Cs cible."""

    model_config = ConfigDict(extra="forbid")

    shaft_diameter_mm: float = Field(..., gt=0)
    Mt_Nm: float = Field(..., gt=0)
    material_shaft: str
    hub_material: Literal["steel", "cast_iron", "aluminum"]
    target_cs: float = Field(..., gt=0)
    l_min_mm: Optional[float] = Field(
        None, gt=0, description="Longueur min à essayer (mm) ; défaut = b + 5",
    )
    l_max_mm: float = Field(200.0, gt=0)
    step_mm: float = Field(1.0, gt=0)

    @field_validator("material_shaft")
    @classmethod
    def _strip_mat(cls, v: str) -> str:
        return v.strip()


class KeyOptimizeResponse(BaseModel):
    found: bool
    l_total_optimal_mm: Optional[float] = None
    result: Optional[KeyResponse] = None
    target_safety_factor: float
    l_min_mm: float
    l_max_mm: float
    step_mm: float
    candidates_evaluated: int
    advice: AdviceOut


# --------------------------------------------------------------------------- #
# Bearing module — request / response (ISO 281 dynamic + ISO 76 static)        #
# --------------------------------------------------------------------------- #
BearingTypeLit = Literal[
    "ball_radial",          # alias historique (= 1ROW)
    "ball_radial_1row",
    "ball_radial_2row",
    "ball_oblique_1row",    # nécessite alpha_deg
    "roller_cylindrical",
    "roller_conical",       # paramétrable Y_conical / e_conical
]


class BearingRequest(BaseModel):
    """Calcul d'un roulement : durée de vie L10 (ISO 281) + statique (ISO 76)."""

    model_config = ConfigDict(extra="forbid")

    bearing_type: BearingTypeLit = Field(..., description="Type de roulement")
    C_N: float = Field(..., gt=0, description="Charge dynamique de base C, N (catalogue)")
    C0_N: float = Field(
        ..., ge=0,
        description="Charge statique de base C0, N (catalogue). Requis si Fa>0 pour billes",
    )
    Fr_N: float = Field(..., ge=0, description="Charge radiale Fr, N")
    Fa_N: float = Field(0.0, ge=0, description="Charge axiale Fa, N")
    n_rpm: float = Field(..., gt=0, description="Vitesse de rotation, tr/min")
    target_hours: float = Field(20_000.0, gt=0, description="Durée de vie cible, h")
    # Paramètres spécifiques par type
    alpha_deg: Optional[float] = Field(
        None, gt=0,
        description="Angle de contact en degrés (15/20/25/30), requis pour ball_oblique_1row",
    )
    Y_conical: float = Field(
        1.5, gt=0,
        description="Coefficient Y pour rouleaux coniques au-dessus du seuil e",
    )
    e_conical: float = Field(
        0.4, gt=0,
        description="Seuil e pour rouleaux coniques (transition X=1,Y=0 ↔ X=0.4,Y=Y_conical)",
    )


class BearingResponse(BaseModel):
    bearing_type: BearingTypeLit
    C_N: float
    C0_N: float
    Fr_N: float
    Fa_N: float
    n_rpm: float
    target_hours: float

    # Dynamic
    P_N: float = Field(..., description="Charge équivalente dynamique P, N")
    e_used: Optional[float] = Field(
        None, description="Coefficient e ISO 281 (None si non applicable)"
    )
    X_used: float
    Y_used: float
    L10_millions: float = Field(..., description="Durée de vie L10 en millions de tours")
    L10_hours: float = Field(..., description="Durée de vie L10h en heures")
    verdict_dynamic: str

    # Static
    P0_N: float = Field(..., description="Charge équivalente statique P0, N")
    S0: float = Field(..., description="Facteur de sécurité statique S0 = C0/P0")
    verdict_static: str

    advice: AdviceOut


class BearingOptimizeRequest(BaseModel):
    """Sélection du plus petit roulement satisfaisant L10 cible ET S0 cible."""

    model_config = ConfigDict(extra="forbid")

    bearing_type: BearingTypeLit
    Fr_N: float = Field(..., ge=0)
    Fa_N: float = Field(0.0, ge=0)
    n_rpm: float = Field(..., gt=0)
    target_hours: float = Field(20_000.0, gt=0)
    S0_target: float = Field(1.0, gt=0, description="Facteur de sécurité statique cible")


class BearingCatalogOut(BaseModel):
    designation: str
    type: BearingTypeLit
    C_N: float
    C0_N: float
    d_bore_mm: Optional[float] = None


class BearingEvalOut(BaseModel):
    designation: str
    type: BearingTypeLit
    C_N: float
    C0_N: float
    d_bore_mm: Optional[float] = None
    L10_hours: float
    S0: float
    status_dyn: Literal["OK", "Insuffisant"]
    status_stat: Literal["OK", "Insuffisant"]


class BearingOptimizeResponse(BaseModel):
    found: bool
    C_required_N: float = Field(..., description="C minimale pour L10 ≥ cible")
    C0_required_N: float = Field(..., description="C0 minimale pour S0 ≥ S0_target")
    P_N: float
    P0_N: float
    e_used: Optional[float] = None
    X_used: float
    Y_used: float
    S0_target: float
    optimal: Optional[BearingCatalogOut] = None
    result: Optional[BearingResponse] = None
    target_hours: float
    bearing_type: BearingTypeLit
    evaluations: List[BearingEvalOut]
    advice: AdviceOut


# --------------------------------------------------------------------------- #
# Bearing set (LE10)                                                           #
# --------------------------------------------------------------------------- #
class BearingSetRequest(BaseModel):
    """LE10 d'un ensemble de roulements à partir des L10h individuels."""

    model_config = ConfigDict(extra="forbid")

    L10_hours_each: List[float] = Field(
        ..., min_length=1,
        description="L10h de chaque roulement de l'ensemble (en heures, > 0)",
    )


class BearingSetResponse(BaseModel):
    LE10_hours: float = Field(..., description="Durée de vie équivalente de l'ensemble (h)")
    weakest_index: int = Field(..., description="Index 0-based du roulement le plus faible")
    weakest_L10_hours: float
    L10_hours_each: List[float]


# --------------------------------------------------------------------------- #
# Variable loading (Pe)                                                        #
# --------------------------------------------------------------------------- #
class VariableLoadPeriodIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    P_N: float = Field(..., gt=0, description="Charge équivalente pendant la période, N")
    a_fraction: float = Field(..., ge=0, le=1, description="Fraction de temps (0..1)")


class BearingVariableLoadRequest(BaseModel):
    """Charge équivalente Pe pour un profil de chargement variable."""

    model_config = ConfigDict(extra="forbid")

    bearing_type: BearingTypeLit
    periods: List[VariableLoadPeriodIn] = Field(..., min_length=1)


class BearingVariableLoadResponse(BaseModel):
    Pe_N: float
    n_exponent: float
    bearing_type: BearingTypeLit
    periods: List[VariableLoadPeriodIn]


# --------------------------------------------------------------------------- #
# Optimize bearing catalog (real catalogue)                                    #
# --------------------------------------------------------------------------- #
class BearingCatalogOptimizeRequest(BaseModel):
    """Recherche dans le catalogue réel (série 6000) avec filtre d_arbre."""

    model_config = ConfigDict(extra="forbid")

    bearing_type: BearingTypeLit
    Fr_N: float = Field(..., ge=0)
    Fa_N: float = Field(0.0, ge=0)
    C0_estimate_N: float = Field(..., gt=0, description="Estimation initiale de C0")
    n_rpm: float = Field(..., gt=0)
    target_hours: float = Field(..., gt=0)
    d_arbre_mm: Optional[float] = Field(
        None, gt=0,
        description="Si précisé, filtre le catalogue sur l'alésage d_arbre",
    )
    S0_target: float = Field(1.0, gt=0)
    # Paramètres spécifiques
    alpha_deg: Optional[float] = Field(None, gt=0)
    Y_conical: float = Field(1.5, gt=0)
    e_conical: float = Field(0.4, gt=0)


class RealBearingOut(BaseModel):
    designation: str
    type: BearingTypeLit
    d_bore_mm: float
    D_outer_mm: float
    B_width_mm: float
    C_N: float
    C0_N: float


class RealCatalogEvalOut(BaseModel):
    designation: str
    type: BearingTypeLit
    d_bore_mm: float
    D_outer_mm: float
    B_width_mm: float
    C_N: float
    C0_N: float
    L10_hours: float
    S0: float
    status_dyn: Literal["OK", "Insuffisant"]
    status_stat: Literal["OK", "Insuffisant"]


class BearingCatalogOptimizeResponse(BaseModel):
    found: bool
    C_required_N: float
    optimal: Optional[RealBearingOut] = None
    result: Optional[BearingResponse] = None
    target_hours: float
    bearing_type: BearingTypeLit
    d_arbre_mm: Optional[float] = None
    evaluations: List[RealCatalogEvalOut]
    advice: AdviceOut


# --------------------------------------------------------------------------- #
# Gear module — request / response (engrenage droit, Lewis + Hertz)           #
# --------------------------------------------------------------------------- #
GearLimitingCriterion = Literal[
    "flexion_pignon", "flexion_roue", "pression_superficielle"
]


class GearRequest(BaseModel):
    """Vérification d'un engrenage droit extérieur (flexion Lewis + pression Hertz)."""

    model_config = ConfigDict(extra="forbid")

    m_mm: float = Field(..., gt=0, description="Module, mm")
    z1: int = Field(..., ge=12, description="Nombre de dents du pignon (≥ 12)")
    z2: int = Field(..., ge=12, description="Nombre de dents de la roue (≥ 12)")
    b_mm: float = Field(..., gt=0, description="Largeur de denture, mm")
    Mt1_Nm: float = Field(..., gt=0, description="Couple sur l'arbre pignon, N·m (> 0)")
    n1_rpm: float = Field(..., gt=0, description="Vitesse de rotation du pignon, tr/min (> 0)")
    material_pinion: str = Field(..., description="Matériau du pignon")
    material_gear: str = Field(..., description="Matériau de la roue")
    K_A: float = Field(1.0, gt=0, description="Facteur d'application (sévérité de charge)")

    @field_validator("material_pinion", "material_gear")
    @classmethod
    def _strip_mat(cls, v: str) -> str:
        return v.strip()


class GearGeometryOut(BaseModel):
    m_mm: float = Field(..., description="Module, mm")
    z1: int
    z2: int
    b_mm: float = Field(..., description="Largeur de denture, mm")
    d1_mm: float = Field(..., description="Diamètre primitif du pignon, mm")
    d2_mm: float = Field(..., description="Diamètre primitif de la roue, mm")
    a_mm: float = Field(..., description="Entraxe, mm")
    u: float = Field(..., description="Rapport de réduction u = z2/z1")


class GearResponse(BaseModel):
    geometry: GearGeometryOut
    Mt1_Nm: float
    n1_rpm: float
    Ft_N: float = Field(..., description="Effort tangentiel, N")
    Fr_N: float = Field(..., description="Effort radial, N")
    v_m_s: float = Field(..., description="Vitesse tangentielle au primitif, m/s")
    K_A: float
    K_V: float = Field(..., description="Facteur dynamique simplifié K_V = 1 + v/6")
    sigma_F1_MPa: float = Field(..., description="Contrainte de flexion en pied de dent, pignon")
    sigma_F2_MPa: float = Field(..., description="Contrainte de flexion en pied de dent, roue")
    sigma_F1_adm_MPa: float = Field(..., description="σ_F admissible pignon (= σ_D matériau)")
    sigma_F2_adm_MPa: float = Field(..., description="σ_F admissible roue (= σ_D matériau)")
    sigma_H_MPa: float = Field(..., description="Pression de contact (Hertz)")
    sigma_H_adm_MPa: float = Field(..., description="Pression de contact admissible")
    Cs_F1: float
    Cs_F2: float
    Cs_H: float
    Cs: float = Field(..., description="Cs global = min(Cs_F1, Cs_F2, Cs_H)")
    limiting_criterion: GearLimitingCriterion
    verdict: str
    advice: AdviceOut


class GearOptimizeRequest(BaseModel):
    """Recherche du plus petit module normalisé satisfaisant Cs ≥ target_cs."""

    model_config = ConfigDict(extra="forbid")

    z1: int = Field(..., ge=12, description="Nombre de dents du pignon (≥ 12)")
    z2: int = Field(..., ge=12, description="Nombre de dents de la roue (≥ 12)")
    Mt1_Nm: float = Field(..., gt=0, description="Couple sur l'arbre pignon, N·m")
    n1_rpm: float = Field(..., gt=0, description="Vitesse de rotation du pignon, tr/min")
    material_pinion: str = Field(..., description="Matériau du pignon")
    material_gear: str = Field(..., description="Matériau de la roue")
    target_cs: float = Field(..., gt=0, description="Coefficient de sécurité cible")
    K_A: float = Field(1.0, gt=0, description="Facteur d'application")
    psi_m: float = Field(
        10.0, gt=0,
        description="Rapport largeur/module : b = psi_m × m",
    )

    @field_validator("material_pinion", "material_gear")
    @classmethod
    def _strip_mat(cls, v: str) -> str:
        return v.strip()


class GearEvalOut(BaseModel):
    m_mm: float
    b_mm: float
    Cs: float
    status: Literal["OK", "insuffisant"]
    limiting_criterion: GearLimitingCriterion


class GearOptimizeResponse(BaseModel):
    found: bool
    m_optimal_mm: Optional[float] = Field(None, description="Module optimal, mm (None si aucun)")
    result: Optional[GearResponse] = None
    target_safety_factor: float
    psi_m: float
    evaluations: List[GearEvalOut]
    advice: AdviceOut
