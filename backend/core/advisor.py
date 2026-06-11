"""Decisional advisor: turn raw numbers into an actionable diagnosis.

`generate_advice` is a pure function over a `BeamResult` + the beam's
material + length (so it can phrase σ vs. Re and f vs. f_admissible). It
returns an `Advice` value object — never raises, never decides for the user
(only suggests).

Defaults: when no explicit deflection limit is given (typical Verification
flow), L/250 is used as a commonly accepted SLS limit for steel beams in
buildings; the message states this explicitly so the user knows it's a
default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .beam import BeamResult
from .materials import Material


LimitingFactor = Literal["contrainte", "flèche", "les deux", "aucun"]

DEFAULT_DEFLECTION_RATIO = 250.0   # SLS reference for steel building beams


@dataclass(frozen=True)
class Advice:
    diagnostic: str
    cause: str
    conseil: str
    facteur_limitant: LimitingFactor


def _fmt_mpa(pa: float) -> str:
    return f"{pa * 1e-6:.1f} MPa"


def _fmt_mm(m: float) -> str:
    return f"{m * 1e3:.2f} mm"


def generate_advice(
    result: BeamResult,
    *,
    material: Material,
    length_m: float,
    deflection_limit_m: Optional[float] = None,
) -> Advice:
    """Diagnose a BeamResult and return human-readable advice.

    Parameters
    ----------
    result : BeamResult
        Output of `analyze(beam)`.
    material : Material
        The beam's material (needed to phrase σ vs. Re).
    length_m : float
        Beam length L, in m (used for fallback deflection limit).
    deflection_limit_m : float, optional
        Maximum admissible deflection (m). If None, defaults to L / 250
        and the message says so.

    Returns
    -------
    Advice
        Structured diagnosis with diagnostic / cause / conseil / facteur_limitant.
    """
    used_default = deflection_limit_m is None
    if deflection_limit_m is None:
        deflection_limit_m = length_m / DEFAULT_DEFLECTION_RATIO

    Re = material.Re_effective
    sigma = result.sigma_max
    f = result.f_max
    cs = result.Cs

    has_stress = sigma > Re                # equivalent to cs < 1
    has_defl = f > deflection_limit_m

    limit_label = (
        f"L/{DEFAULT_DEFLECTION_RATIO:.0f} = {_fmt_mm(deflection_limit_m)} "
        "(valeur courante en construction)"
        if used_default
        else f"{_fmt_mm(deflection_limit_m)} (valeur fournie)"
    )

    # ---- Both ULS and SLS exceeded ----------------------------------------
    if has_stress and has_defl:
        return Advice(
            diagnostic=(
                "La poutre est sous-dimensionnée à la fois en contrainte "
                "et en flèche."
            ),
            cause=(
                f"σ_max = {_fmt_mpa(sigma)} dépasse Re = {_fmt_mpa(Re)} "
                f"(Cs = {cs:.2f} < 1), et f_max = {_fmt_mm(f)} dépasse la "
                f"flèche admissible {limit_label}."
            ),
            conseil=(
                "Augmenter significativement la hauteur de la section "
                "(elle augmente à la fois W et I), ou choisir un matériau "
                "à limite élastique plus élevée (ex. S355)."
            ),
            facteur_limitant="les deux",
        )

    # ---- Strength only ----------------------------------------------------
    if has_stress:
        return Advice(
            diagnostic="La poutre est sous-dimensionnée : la contrainte "
                       "dépasse la limite élastique du matériau.",
            cause=(
                f"σ_max = {_fmt_mpa(sigma)} dépasse Re = {_fmt_mpa(Re)} "
                f"(Cs = {cs:.2f} < 1)."
            ),
            conseil=(
                "Augmenter la section (W = I/v) ou choisir un matériau de "
                "limite élastique plus élevée (ex. S355)."
            ),
            facteur_limitant="contrainte",
        )

    # ---- Deflection only --------------------------------------------------
    if has_defl:
        return Advice(
            diagnostic="La poutre est sous-dimensionnée en service : la "
                       "flèche dépasse la limite admissible.",
            cause=(
                f"f_max = {_fmt_mm(f)} dépasse la flèche admissible "
                f"{limit_label} (la résistance est elle satisfaisante : "
                f"Cs = {cs:.2f})."
            ),
            conseil=(
                "Augmenter l'inertie de la section (typiquement en augmentant "
                "la hauteur de poutre) ou réduire la portée."
            ),
            facteur_limitant="flèche",
        )

    # ---- No strict failure: use the verdict to nuance ---------------------
    if result.verdict == "Limite":
        return Advice(
            diagnostic="Marge de sécurité insuffisante.",
            cause=(
                f"Cs = {cs:.2f} (entre 1 et 1.5), σ_max = {_fmt_mpa(sigma)} "
                f"proche de Re = {_fmt_mpa(Re)}."
            ),
            conseil=(
                "Envisager un coefficient de sécurité cible de 1.5 minimum "
                "en augmentant la section."
            ),
            facteur_limitant="contrainte",
        )

    if result.verdict == "Surdimensionné":
        return Advice(
            diagnostic="La section est largement surdimensionnée.",
            cause=(
                f"Cs = {cs:.2f} (> 4) : σ_max = {_fmt_mpa(sigma)} très faible "
                f"devant Re = {_fmt_mpa(Re)}, et f_max = {_fmt_mm(f)} très "
                f"inférieure à la flèche admissible {limit_label}."
            ),
            conseil=(
                "Un profilé plus léger suffirait. Lancer l'optimisation "
                "catalogue pour trouver la section minimale qui passe."
            ),
            facteur_limitant="aucun",
        )

    # ---- OK ---------------------------------------------------------------
    return Advice(
        diagnostic="Dimensionnement satisfaisant.",
        cause=(
            f"Cs = {cs:.2f}, σ_max = {_fmt_mpa(sigma)} (Re = {_fmt_mpa(Re)}), "
            f"f_max = {_fmt_mm(f)} (admissible {limit_label})."
        ),
        conseil="Dimensionnement satisfaisant.",
        facteur_limitant="aucun",
    )


# --------------------------------------------------------------------------- #
# Shaft advisor (Von Mises, no deflection check)                               #
# --------------------------------------------------------------------------- #
def generate_shaft_advice(
    *,
    material: Material,
    sigma_f_Pa: float,
    tau_Pa: float,
    sigma_eq_Pa: float,
    cs: float,
    verdict_str: str,
) -> Advice:
    """Diagnose a shaft loaded in combined bending + torsion.

    Unlike beams there is no deflection criterion here — only the Von Mises
    equivalent stress matters. The advisor identifies whether bending or
    torsion dominates so the conseil can target the right lever.
    """
    Re = material.Re_effective
    bending_contrib = sigma_f_Pa ** 2
    torsion_contrib = 3.0 * tau_Pa ** 2
    total = bending_contrib + torsion_contrib
    dominant = (
        "torsion" if total > 0 and torsion_contrib / total >= 0.6
        else "flexion" if total > 0 and bending_contrib / total >= 0.6
        else "mixte"
    )

    breakdown = (
        f"σ_f = {_fmt_mpa(sigma_f_Pa)} (flexion), "
        f"τ = {_fmt_mpa(tau_Pa)} (torsion), "
        f"σ_eq = {_fmt_mpa(sigma_eq_Pa)}, "
        f"Re = {_fmt_mpa(Re)}"
    )

    # ---- Under-designed (Cs < 1) -----------------------------------------
    if sigma_eq_Pa > Re:
        if dominant == "torsion":
            conseil = (
                "La torsion domine. Augmenter le diamètre (W_t = π·d³/16 "
                "varie en d³) ou ajouter un couplage qui réduit le couple "
                "à transmettre."
            )
        elif dominant == "flexion":
            conseil = (
                "La flexion domine. Augmenter le diamètre (W_f = π·d³/32 "
                "varie en d³) ou réduire le porte-à-faux des paliers pour "
                "diminuer Mf."
            )
        else:
            conseil = (
                "Augmenter le diamètre (effet en d³ sur W_f et W_t) ou "
                "utiliser un matériau à limite élastique plus élevée "
                "(ex. acier traité)."
            )
        return Advice(
            diagnostic=(
                "Arbre sous-dimensionné : la contrainte équivalente de "
                "Von Mises dépasse la limite élastique."
            ),
            cause=f"{breakdown} → Cs = {cs:.2f} < 1. Charge dominante : {dominant}.",
            conseil=conseil,
            facteur_limitant="contrainte",
        )

    # ---- Limite ----------------------------------------------------------
    if verdict_str == "Limite":
        return Advice(
            diagnostic="Marge de sécurité insuffisante sur l'arbre.",
            cause=f"{breakdown} → Cs = {cs:.2f} (entre 1 et 1.5).",
            conseil=(
                "Passer au diamètre normalisé supérieur ou choisir un acier "
                "à plus haute résistance (Cs ≥ 1.5 recommandé pour la fatigue)."
            ),
            facteur_limitant="contrainte",
        )

    # ---- Surdimensionné --------------------------------------------------
    if verdict_str == "Surdimensionné":
        return Advice(
            diagnostic="Arbre largement surdimensionné.",
            cause=(
                f"Cs = {cs:.2f} (> 4) : σ_eq = {_fmt_mpa(sigma_eq_Pa)} très "
                f"faible devant Re = {_fmt_mpa(Re)}."
            ),
            conseil=(
                "Réduire le diamètre. Lancer l'optimisation pour trouver le "
                "diamètre minimal qui passe."
            ),
            facteur_limitant="aucun",
        )

    # ---- OK --------------------------------------------------------------
    return Advice(
        diagnostic="Dimensionnement satisfaisant.",
        cause=(
            f"{breakdown}, Cs = {cs:.2f}. Charge dominante : {dominant}."
        ),
        conseil="Dimensionnement satisfaisant.",
        facteur_limitant="aucun",
    )


# --------------------------------------------------------------------------- #
# Key (clavette) advisor                                                       #
# --------------------------------------------------------------------------- #
def generate_key_advice(
    *,
    material_shaft,
    hub_material,
    tau_Pa: float,
    sigma_m_Pa: float,
    Re_shear_Pa: float,
    sigma_m_adm_Pa: float,
    cs_shear: float,
    cs_bearing: float,
    cs_global: float,
    limiting: str,                # "cisaillement" | "matage"
    verdict_str: str,
) -> Advice:
    """Diagnose a parallel-key assembly. Identifies which criterion limits."""
    # Avoid coupling to enum/Material classes by extracting fields late
    hub_name = getattr(hub_material, "value", str(hub_material))
    breakdown = (
        f"τ = {_fmt_mpa(tau_Pa)} (admissible {_fmt_mpa(Re_shear_Pa)}), "
        f"σ_m = {_fmt_mpa(sigma_m_Pa)} (admissible {_fmt_mpa(sigma_m_adm_Pa)} "
        f"pour moyeu {hub_name})"
    )

    # --- Under-designed -----------------------------------------------------
    if cs_global < 1.0:
        if limiting == "cisaillement":
            conseil = (
                "Le cisaillement de la clavette est le facteur limitant. "
                "Augmenter la longueur active (l_active = l_total − b) "
                "diminue τ. Si la longueur disponible est contrainte, "
                "envisager un acier plus dur ou passer à un assemblage "
                "cannelé (split) pour répartir l'effort."
            )
        else:
            conseil = (
                "Le matage des flancs est le facteur limitant. "
                "Augmenter la longueur active OU choisir un moyeu en "
                "matériau plus dur (acier au lieu de fonte/alu) augmente "
                "σ_m_admissible."
            )
        return Advice(
            diagnostic=(
                f"Clavette sous-dimensionnée ({limiting})."
            ),
            cause=f"{breakdown}. Cs_global = {cs_global:.2f} < 1.",
            conseil=conseil,
            facteur_limitant="contrainte",
        )

    # --- Limite -------------------------------------------------------------
    if verdict_str == "Limite":
        return Advice(
            diagnostic=f"Clavette à la limite ({limiting}).",
            cause=(
                f"{breakdown}. Cs_shear = {cs_shear:.2f}, "
                f"Cs_bearing = {cs_bearing:.2f}. Marge insuffisante."
            ),
            conseil=(
                "Augmenter la longueur d'un cran (5–10 mm) ou passer à un "
                "moyeu en matériau plus dur pour viser Cs ≥ 1.5."
            ),
            facteur_limitant="contrainte",
        )

    # --- Surdimensionné -----------------------------------------------------
    if verdict_str == "Surdimensionné":
        return Advice(
            diagnostic="Clavette largement surdimensionnée.",
            cause=(
                f"Cs_shear = {cs_shear:.2f}, Cs_bearing = {cs_bearing:.2f}. "
                f"{breakdown}."
            ),
            conseil=(
                "La longueur peut être réduite. Lancer l'optimisation pour "
                "trouver la longueur minimale au Cs cible."
            ),
            facteur_limitant="aucun",
        )

    # --- OK -----------------------------------------------------------------
    return Advice(
        diagnostic="Clavette correctement dimensionnée.",
        cause=(
            f"{breakdown}. Cs_shear = {cs_shear:.2f}, "
            f"Cs_bearing = {cs_bearing:.2f} (facteur limitant : {limiting})."
        ),
        conseil="Dimensionnement satisfaisant.",
        facteur_limitant="aucun",
    )


# --------------------------------------------------------------------------- #
# Bearing (roulement) advisor                                                  #
# --------------------------------------------------------------------------- #
def generate_bearing_advice(
    *,
    L10_hours: float,
    target_hours: float,
    Fr_N: float,
    Fa_N: float,
    P_N: float,
    P0_N: float,
    S0: float,
    bearing_type,
    verdict_dynamic: str,
    verdict_static: str,
) -> Advice:
    """Diagnose a bearing on BOTH the dynamic (L10) and static (S0) checks."""
    type_name = getattr(bearing_type, "value", str(bearing_type))
    breakdown = (
        f"Dynamique : P = {P_N:.0f} N, L10 = {L10_hours:,.0f} h "
        f"(cible {target_hours:,.0f} h). "
        f"Statique : P0 = {P0_N:.0f} N, S0 = {S0:.2f}."
    ).replace(",", " ")

    is_dyn_under = verdict_dynamic == "Insuffisant"
    is_stat_under = verdict_static.startswith("Insuffisant")

    # ---- Both failing -----------------------------------------------------
    if is_dyn_under and is_stat_under:
        return Advice(
            diagnostic=(
                "Roulement sous-dimensionné en dynamique ET en statique."
            ),
            cause=f"{breakdown}",
            conseil=(
                "Choisir un roulement avec C ET C0 plus élevés (taille "
                "supérieure dans le catalogue). Vérifier aussi si la charge "
                "réelle n'a pas été sous-estimée."
            ),
            facteur_limitant="les deux",
        )

    # ---- Dynamic only failing --------------------------------------------
    if is_dyn_under:
        conseils: list[str] = []
        if Fa_N > 0.5 * Fr_N and type_name == "ball_radial":
            conseils.append(
                "la charge axiale est élevée → envisager un roulement à "
                "contact oblique ou à rouleaux coniques"
            )
        conseils.append("choisir un C catalogue plus élevé (taille supérieure)")
        conseils.append("réduire la vitesse de rotation ou la charge")
        return Advice(
            diagnostic="Durée de vie L10 insuffisante (< 50 % de la cible).",
            cause=f"{breakdown}",
            conseil="Pistes : " + " ; ".join(conseils) + ".",
            facteur_limitant="contrainte",
        )

    # ---- Static only failing ---------------------------------------------
    if is_stat_under:
        return Advice(
            diagnostic=(
                "Capacité de charge statique insuffisante (risque de "
                "déformation permanente)."
            ),
            cause=f"{breakdown} S0 = {S0:.2f} < 0.5.",
            conseil=(
                "Choisir un roulement avec C0 plus élevée OU dimensionner la "
                "fixation pour éviter les pics de charge statique."
            ),
            facteur_limitant="contrainte",
        )

    # ---- Limit cases (no fail but warn) ----------------------------------
    if verdict_dynamic == "Limite":
        return Advice(
            diagnostic="Durée de vie L10 légèrement sous la cible.",
            cause=f"{breakdown}",
            conseil=(
                "Monter d'une taille au catalogue pour viser L10 ≥ "
                f"{target_hours:,.0f} h.".replace(",", " ")
            ),
            facteur_limitant="contrainte",
        )

    if verdict_dynamic == "Surdimensionné":
        return Advice(
            diagnostic="Roulement largement surdimensionné en dynamique.",
            cause=f"{breakdown} (> 3 × cible).",
            conseil=(
                "Une taille inférieure du catalogue suffirait probablement. "
                "Lancer l'optimisation pour identifier le minimum."
            ),
            facteur_limitant="aucun",
        )

    # ---- OK ---------------------------------------------------------------
    return Advice(
        diagnostic="Roulement correctement dimensionné (dynamique + statique).",
        cause=f"{breakdown}",
        conseil="Dimensionnement satisfaisant.",
        facteur_limitant="aucun",
    )


# --------------------------------------------------------------------------- #
# Gear (engrenage droit) advisor                                               #
# --------------------------------------------------------------------------- #
def generate_gear_advice(
    *,
    sigma_F1_Pa: float,
    sigma_F2_Pa: float,
    sigma_F1_adm_Pa: float,
    sigma_F2_adm_Pa: float,
    sigma_H_Pa: float,
    sigma_H_adm_Pa: float,
    cs_f1: float,
    cs_f2: float,
    cs_h: float,
    cs_global: float,
    limiting: str,   # "flexion_pignon" | "flexion_roue" | "pression_superficielle"
    verdict_str: str,
) -> Advice:
    """Diagnose a spur-gear pair (Lewis bending + Hertz contact)."""
    breakdown = (
        f"σ_F1 = {_fmt_mpa(sigma_F1_Pa)} (adm {_fmt_mpa(sigma_F1_adm_Pa)}, "
        f"Cs={cs_f1:.2f}), σ_F2 = {_fmt_mpa(sigma_F2_Pa)} "
        f"(adm {_fmt_mpa(sigma_F2_adm_Pa)}, Cs={cs_f2:.2f}), "
        f"σ_H = {_fmt_mpa(sigma_H_Pa)} (adm {_fmt_mpa(sigma_H_adm_Pa)}, "
        f"Cs={cs_h:.2f})"
    )

    # --- Under-designed -----------------------------------------------------
    if cs_global < 1.0:
        if limiting == "pression_superficielle":
            conseil = (
                "La pression de contact (Hertz) est limitante. Augmenter le "
                "module (d1 et b augmentent proportionnellement) ou choisir des "
                "matériaux plus durs (traitement thermique) pour augmenter "
                "σ_H_lim."
            )
        else:
            dent = "du pignon" if limiting == "flexion_pignon" else "de la roue"
            conseil = (
                f"La flexion en pied de dent {dent} est limitante. Augmenter "
                "le module m (σ_F varie en 1/m) ou la largeur de denture b, ou "
                "choisir un acier de limite de fatigue plus élevée."
            )
        return Advice(
            diagnostic="Engrenage sous-dimensionné.",
            cause=f"{breakdown}. Cs_global = {cs_global:.2f} < 1.",
            conseil=conseil,
            facteur_limitant="contrainte",
        )

    # --- Limite ---------------------------------------------------------------
    if verdict_str == "Limite":
        return Advice(
            diagnostic="Marge de sécurité insuffisante sur l'engrenage.",
            cause=f"{breakdown}. Cs_global = {cs_global:.2f} (entre 1 et 1.5).",
            conseil=(
                "Passer au module normalisé supérieur pour viser Cs ≥ 1.5."
            ),
            facteur_limitant="contrainte",
        )

    # --- Surdimensionné --------------------------------------------------------
    if verdict_str == "Surdimensionné":
        return Advice(
            diagnostic="Engrenage largement surdimensionné.",
            cause=f"{breakdown}. Cs_global = {cs_global:.2f} (> 4).",
            conseil=(
                "Un module inférieur suffirait probablement. Lancer "
                "l'optimisation pour trouver le module minimal au Cs cible."
            ),
            facteur_limitant="aucun",
        )

    # --- OK ---------------------------------------------------------------
    return Advice(
        diagnostic="Engrenage correctement dimensionné.",
        cause=f"{breakdown}. Cs_global = {cs_global:.2f} (limitant : {limiting}).",
        conseil="Dimensionnement satisfaisant.",
        facteur_limitant="aucun",
    )
