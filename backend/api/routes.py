"""HTTP routes — convert API schemas to core models, call core, convert back."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from core import (
    Beam,
    BearingType,
    CircularSection,
    DistributedLoad,
    GearGeometry,
    HubMaterial,
    PointLoad,
    RectangularSection,
    ShaftSection,
    SupportType,
    TubeSection,
    VariableLoadPeriod,
    analyze,
    calculate_bearing,
    calculate_bearing_set,
    calculate_gear,
    calculate_key,
    calculate_shaft,
    calculate_variable_load,
    generate_advice,
    get_combined_catalog,
    get_material,
    optimize_beam_catalog,
    optimize_bearing,
    optimize_bearing_catalog,
    optimize_gear,
    optimize_key,
    optimize_shaft,
)
from core import units as U

from .schemas import (
    AdviceOut,
    BeamOptimizeRequest,
    BeamOptimizeResponse,
    BeamRequest,
    BeamResponse,
    BearingCatalogOptimizeRequest,
    BearingCatalogOptimizeResponse,
    BearingCatalogOut,
    BearingEvalOut,
    BearingOptimizeRequest,
    BearingOptimizeResponse,
    BearingRequest,
    BearingResponse,
    BearingSetRequest,
    BearingSetResponse,
    BearingVariableLoadRequest,
    BearingVariableLoadResponse,
    CircularSectionIn,
    DistributedLoadIn,
    GearEvalOut,
    GearGeometryOut,
    GearOptimizeRequest,
    GearOptimizeResponse,
    GearRequest,
    GearResponse,
    KeyOptimizeRequest,
    KeyOptimizeResponse,
    KeyRequest,
    KeyResponse,
    KeySectionOut,
    OptimalProfileOut,
    PointLoadIn,
    ProfileEvalOut,
    RealBearingOut,
    RealCatalogEvalOut,
    RectangularSectionIn,
    SectionProperties,
    ShaftOptimizeRequest,
    ShaftOptimizeResponse,
    ShaftRequest,
    ShaftResponse,
    ShaftSectionProperties,
    TubeSectionIn,
    VariableLoadPeriodIn,
)

router = APIRouter(prefix="/calculate", tags=["calculate"])
optimize_router = APIRouter(prefix="/optimize", tags=["optimize"])


# --------------------------------------------------------------------------- #
# Boundary conversions: engineering units (mm, kN, kN/m) -> SI (m, N, N/m)     #
# --------------------------------------------------------------------------- #
def _to_core_section(s):
    if isinstance(s, RectangularSectionIn):
        return RectangularSection(
            width=U.mm_to_m(s.width_mm),
            height=U.mm_to_m(s.height_mm),
        )
    if isinstance(s, CircularSectionIn):
        return CircularSection(diameter=U.mm_to_m(s.diameter_mm))
    if isinstance(s, TubeSectionIn):
        return TubeSection(
            outer_diameter=U.mm_to_m(s.outer_diameter_mm),
            inner_diameter=U.mm_to_m(s.inner_diameter_mm),
        )
    raise TypeError(f"unknown section input type: {type(s).__name__}")


def _to_core_load(ld):
    if isinstance(ld, PointLoadIn):
        return PointLoad(
            magnitude=U.kn_to_n(ld.magnitude_kN),
            position=ld.position_m,
        )
    if isinstance(ld, DistributedLoadIn):
        return DistributedLoad(
            magnitude=U.kn_per_m_to_n_per_m(ld.magnitude_kN_per_m),
            start=ld.start_m,
            end=ld.end_m,
        )
    raise TypeError(f"unknown load input type: {type(ld).__name__}")


def _section_props(section) -> SectionProperties:
    return SectionProperties(
        area_mm2=section.area * 1e6,                   # m² -> mm²
        inertia_mm4=section.inertia * 1e12,            # m⁴ -> mm⁴
        extreme_fiber_mm=section.extreme_fiber * 1e3,  # m  -> mm
        section_modulus_mm3=section.section_modulus * 1e9,  # m³ -> mm³
    )


def _advice_to_out(advice) -> AdviceOut:
    return AdviceOut(
        diagnostic=advice.diagnostic,
        cause=advice.cause,
        conseil=advice.conseil,
        facteur_limitant=advice.facteur_limitant,
    )


# --------------------------------------------------------------------------- #
# Endpoint                                                                     #
# --------------------------------------------------------------------------- #
@router.post(
    "/beam",
    response_model=BeamResponse,
    summary="Dimensionnement d'une poutre en flexion",
    response_description="Réactions, V(x), M(x), σ_max, flèche, coefficient de sécurité, verdict",
)
def calculate_beam(req: BeamRequest) -> BeamResponse:
    # --- map material name to core.Material (422 if unknown) ----------------
    try:
        material = get_material(req.material)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # --- build core models (422 on any core-level validation error) ---------
    try:
        core_section = _to_core_section(req.section)
        core_loads = [_to_core_load(ld) for ld in req.loads]
        beam = Beam(
            length=req.length_m,
            material=material,
            section=core_section,
            support=SupportType(req.support),
            loads=core_loads,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # --- compute and convert back to engineering units ----------------------
    result = analyze(beam)
    advice = generate_advice(result, material=material, length_m=req.length_m)

    return BeamResponse(
        section_properties=_section_props(core_section),
        reactions_kN={k: v * 1e-3 for k, v in result.reactions.items()},
        x_m=result.x,
        V_kN=[v * 1e-3 for v in result.V],
        M_kNm=[m * 1e-3 for m in result.M],
        M_max_kNm=result.M_max * 1e-3,
        sigma_max_MPa=result.sigma_max * 1e-6,
        f_max_mm=result.f_max * 1e3,
        Cs=result.Cs,
        verdict=result.verdict,
        advice=_advice_to_out(advice),
    )


# --------------------------------------------------------------------------- #
# Catalog optimization endpoint                                                #
# --------------------------------------------------------------------------- #
def _profile_to_optimal_out(p) -> OptimalProfileOut:
    return OptimalProfileOut(
        designation=p.designation,
        family=p.family,
        mass_kg_per_m=p.mass_kg_per_m,
        h_mm=p.h_mm,
        b_mm=p.b_mm,
        area_mm2=p.area * 1e6,
        inertia_mm4=p.inertia * 1e12,
        section_modulus_mm3=p.section_modulus * 1e9,
    )


@optimize_router.post(
    "/beam",
    response_model=BeamOptimizeResponse,
    summary="Sélection du profilé normalisé le plus léger",
    response_description="Profilé optimal + tableau de tous les candidats évalués",
)
def optimize_beam(req: BeamOptimizeRequest) -> BeamOptimizeResponse:
    try:
        material = get_material(req.material)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        catalog = get_combined_catalog(req.catalogs)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        core_loads = [_to_core_load(ld) for ld in req.loads]
        opt = optimize_beam_catalog(
            length=req.length_m,
            material=material,
            support=SupportType(req.support),
            loads=core_loads,
            target_safety_factor=req.target_safety_factor,
            catalog=catalog,
            deflection_ratio=req.deflection_ratio,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    optimal_out = None
    result_out = None
    advice_out: AdviceOut
    if opt.optimal is not None and opt.optimal_result is not None:
        p = opt.optimal
        r = opt.optimal_result
        optimal_out = _profile_to_optimal_out(p)
        advice = generate_advice(
            r,
            material=material,
            length_m=req.length_m,
            deflection_limit_m=opt.deflection_limit_m,
        )
        advice_out = _advice_to_out(advice)
        result_out = BeamResponse(
            section_properties=_section_props(p),
            reactions_kN={k: v * 1e-3 for k, v in r.reactions.items()},
            x_m=r.x,
            V_kN=[v * 1e-3 for v in r.V],
            M_kNm=[m * 1e-3 for m in r.M],
            M_max_kNm=r.M_max * 1e-3,
            sigma_max_MPa=r.sigma_max * 1e-6,
            f_max_mm=r.f_max * 1e3,
            Cs=r.Cs,
            verdict=r.verdict,
            advice=advice_out,
        )
    else:
        # No solution: meta-advice pointing at how to relax the constraints.
        # Highlight the heaviest profile that came closest, if any.
        heaviest_ok_cs = max(opt.evaluations, key=lambda e: e.Cs, default=None)
        cause_bits = []
        if heaviest_ok_cs is not None:
            cause_bits.append(
                f"Le profilé le plus résistant du catalogue atteint "
                f"Cs = {heaviest_ok_cs.Cs:.2f} et f_max = "
                f"{heaviest_ok_cs.f_max_m * 1e3:.1f} mm."
            )
        advice_out = AdviceOut(
            diagnostic="Aucun profilé du catalogue ne satisfait les critères.",
            cause=(
                "Cs cible = "
                f"{req.target_safety_factor:.2f}, "
                f"flèche admissible = L/{req.deflection_ratio:g} "
                f"({opt.deflection_limit_m * 1e3:.2f} mm). "
                + " ".join(cause_bits)
            ).strip(),
            conseil=(
                "Relâcher la limite de flèche (ex. L/150 au lieu de "
                f"L/{req.deflection_ratio:g}), réduire le coefficient de "
                "sécurité cible, ou changer de matériau / catalogue."
            ),
            facteur_limitant="aucun",
        )

    evaluations_out = [
        ProfileEvalOut(
            designation=e.profile.designation,
            family=e.profile.family,
            mass_kg_per_m=e.profile.mass_kg_per_m,
            status=e.status,
            Cs=e.Cs,
            f_max_mm=e.f_max_m * 1e3,
            sigma_max_MPa=e.sigma_max_Pa * 1e-6,
            M_max_kNm=e.M_max_Nm * 1e-3,
            reason=e.reason,
        )
        for e in opt.evaluations
    ]

    return BeamOptimizeResponse(
        found=opt.optimal is not None,
        optimal=optimal_out,
        result=result_out,
        evaluations=evaluations_out,
        deflection_limit_mm=opt.deflection_limit_m * 1e3,
        target_safety_factor=opt.target_safety_factor,
        advice=advice_out,
    )


# --------------------------------------------------------------------------- #
# Shaft endpoints                                                              #
# --------------------------------------------------------------------------- #
def _shaft_section_props(section: ShaftSection) -> ShaftSectionProperties:
    return ShaftSectionProperties(
        type=section.type,
        d_ext_mm=section.d_ext * 1e3,
        d_int_mm=section.d_int * 1e3,
        area_mm2=section.area * 1e6,
        W_f_mm3=section.W_f * 1e9,
        W_t_mm3=section.W_t * 1e9,
    )


def _shaft_result_to_out(section: ShaftSection, result) -> ShaftResponse:
    return ShaftResponse(
        section=_shaft_section_props(section),
        sigma_f_MPa=result.sigma_f_Pa * 1e-6,
        tau_MPa=result.tau_Pa * 1e-6,
        sigma_eq_MPa=result.sigma_eq_Pa * 1e-6,
        Cs=result.Cs,
        verdict=result.verdict,
        advice=_advice_to_out(result.advice),
    )


@router.post(
    "/shaft",
    response_model=ShaftResponse,
    summary="Calcul d'un arbre en flexion + torsion combinées (Von Mises)",
)
def calculate_shaft_endpoint(req: ShaftRequest) -> ShaftResponse:
    try:
        material = get_material(req.material)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        section = ShaftSection(
            type=req.type,
            d_ext=U.mm_to_m(req.d_ext_mm),
            d_int=U.mm_to_m(req.d_int_mm),
        )
        result = calculate_shaft(
            section=section,
            material=material,
            Mf_Nm=req.Mf_Nm,
            Mt_Nm=req.Mt_Nm,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    return _shaft_result_to_out(section, result)


@optimize_router.post(
    "/shaft",
    response_model=ShaftOptimizeResponse,
    summary="Sélection du plus petit diamètre d'arbre satisfaisant Cs cible",
)
def optimize_shaft_endpoint(req: ShaftOptimizeRequest) -> ShaftOptimizeResponse:
    try:
        material = get_material(req.material)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        opt = optimize_shaft(
            material=material,
            Mf_Nm=req.Mf_Nm,
            Mt_Nm=req.Mt_Nm,
            shaft_type=req.type,
            target_cs=req.target_cs,
            d_min_mm=req.d_min_mm,
            d_max_mm=req.d_max_mm,
            step_mm=req.step_mm,
            d_int_ratio=req.d_int_ratio,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    result_out = None
    advice_out: AdviceOut
    if opt.found and opt.result is not None and opt.d_optimal_m is not None:
        result_out = _shaft_result_to_out(opt.result.section, opt.result)
        advice_out = _advice_to_out(opt.result.advice)
    else:
        advice_out = AdviceOut(
            diagnostic=(
                "Aucun diamètre dans la plage demandée ne satisfait le Cs cible."
            ),
            cause=(
                f"Cs cible = {req.target_cs:.2f}, plage = "
                f"{req.d_min_mm:.1f}–{req.d_max_mm:.1f} mm (pas {req.step_mm:g} mm). "
                f"{opt.candidates_evaluated} diamètres essayés."
            ),
            conseil=(
                "Élargir la plage de diamètres (augmenter d_max_mm), réduire le Cs "
                "cible, ou choisir un matériau à limite élastique plus élevée."
            ),
            facteur_limitant="contrainte",
        )

    return ShaftOptimizeResponse(
        found=opt.found,
        d_optimal_mm=(opt.d_optimal_m * 1e3) if opt.d_optimal_m is not None else None,
        result=result_out,
        target_safety_factor=opt.target_safety_factor,
        d_min_mm=opt.d_min_m * 1e3,
        d_max_mm=opt.d_max_m * 1e3,
        step_mm=opt.step_m * 1e3,
        candidates_evaluated=opt.candidates_evaluated,
        advice=advice_out,
    )


# --------------------------------------------------------------------------- #
# Key (clavette) endpoints                                                     #
# --------------------------------------------------------------------------- #
def _key_result_to_out(result) -> KeyResponse:
    return KeyResponse(
        section=KeySectionOut(
            b_mm=result.section.b * 1e3,
            h_mm=result.section.h * 1e3,
            l_total_mm=result.section.l_total * 1e3,
            l_active_mm=result.section.l_active * 1e3,
        ),
        shaft_diameter_mm=result.shaft_diameter_m * 1e3,
        Mt_Nm=result.Mt_Nm,
        hub_material=result.hub_material.value,
        tau_MPa=result.tau_Pa * 1e-6,
        sigma_m_MPa=result.sigma_m_Pa * 1e-6,
        Re_shear_MPa=result.Re_shear_Pa * 1e-6,
        sigma_m_adm_MPa=result.sigma_m_adm_Pa * 1e-6,
        Cs_shear=result.Cs_shear,
        Cs_bearing=result.Cs_bearing,
        Cs=result.Cs,
        limiting_criterion=result.limiting_criterion,
        verdict=result.verdict,
        advice=_advice_to_out(result.advice),
    )


@router.post(
    "/key",
    response_model=KeyResponse,
    summary="Vérification d'une clavette parallèle (ISO 773)",
)
def calculate_key_endpoint(req: KeyRequest) -> KeyResponse:
    try:
        mat = get_material(req.material_shaft)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    try:
        result = calculate_key(
            shaft_diameter_m=U.mm_to_m(req.shaft_diameter_mm),
            Mt_Nm=req.Mt_Nm,
            material_shaft=mat,
            hub_material=HubMaterial(req.hub_material),
            l_total_m=U.mm_to_m(req.l_total_mm),
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return _key_result_to_out(result)


@optimize_router.post(
    "/key",
    response_model=KeyOptimizeResponse,
    summary="Optimisation de la longueur d'une clavette parallèle",
)
def optimize_key_endpoint(req: KeyOptimizeRequest) -> KeyOptimizeResponse:
    try:
        mat = get_material(req.material_shaft)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    try:
        opt = optimize_key(
            shaft_diameter_m=U.mm_to_m(req.shaft_diameter_mm),
            Mt_Nm=req.Mt_Nm,
            material_shaft=mat,
            hub_material=HubMaterial(req.hub_material),
            target_cs=req.target_cs,
            l_min_mm=req.l_min_mm,
            l_max_mm=req.l_max_mm,
            step_mm=req.step_mm,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    result_out = _key_result_to_out(opt.result) if opt.found and opt.result else None
    if opt.found and opt.result is not None:
        advice_out = _advice_to_out(opt.result.advice)
    else:
        advice_out = AdviceOut(
            diagnostic=(
                "Aucune longueur dans la plage demandée ne satisfait le Cs cible."
            ),
            cause=(
                f"Cs cible = {req.target_cs:.2f}, plage = "
                f"{opt.l_min_m * 1e3:.1f}–{opt.l_max_m * 1e3:.1f} mm. "
                f"{opt.candidates_evaluated} longueurs essayées."
            ),
            conseil=(
                "Augmenter la longueur max, choisir un moyeu plus dur, ou utiliser "
                "un assemblage cannelé pour de plus fortes sollicitations."
            ),
            facteur_limitant="contrainte",
        )

    return KeyOptimizeResponse(
        found=opt.found,
        l_total_optimal_mm=(opt.l_total_optimal_m * 1e3) if opt.l_total_optimal_m is not None else None,
        result=result_out,
        target_safety_factor=opt.target_safety_factor,
        l_min_mm=opt.l_min_m * 1e3,
        l_max_mm=opt.l_max_m * 1e3,
        step_mm=opt.step_m * 1e3,
        candidates_evaluated=opt.candidates_evaluated,
        advice=advice_out,
    )


# --------------------------------------------------------------------------- #
# Bearing (roulement) endpoints                                                #
# --------------------------------------------------------------------------- #
def _bearing_result_to_out(result) -> BearingResponse:
    return BearingResponse(
        bearing_type=result.bearing_type.value,
        C_N=result.C_N,
        C0_N=result.C0_N,
        Fr_N=result.Fr_N,
        Fa_N=result.Fa_N,
        n_rpm=result.n_rpm,
        target_hours=result.target_hours,
        P_N=result.P_N,
        e_used=result.e_used,
        X_used=result.X_used,
        Y_used=result.Y_used,
        L10_millions=result.L10_millions,
        L10_hours=result.L10_hours,
        verdict_dynamic=result.verdict_dynamic,
        P0_N=result.P0_N,
        S0=result.S0,
        verdict_static=result.verdict_static,
        advice=_advice_to_out(result.advice),
    )


@router.post(
    "/bearing",
    response_model=BearingResponse,
    summary="Calcul d'un roulement : L10 (ISO 281) + statique (ISO 76)",
)
def calculate_bearing_endpoint(req: BearingRequest) -> BearingResponse:
    try:
        result = calculate_bearing(
            C_N=req.C_N,
            C0_N=req.C0_N,
            Fr_N=req.Fr_N,
            Fa_N=req.Fa_N,
            n_rpm=req.n_rpm,
            bearing_type=BearingType(req.bearing_type),
            target_hours=req.target_hours,
            alpha_deg=req.alpha_deg,
            Y_conical=req.Y_conical,
            e_conical=req.e_conical,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return _bearing_result_to_out(result)


@optimize_router.post(
    "/bearing",
    response_model=BearingOptimizeResponse,
    summary="Sélection du plus petit roulement satisfaisant L10 cible et S0 cible",
)
def optimize_bearing_endpoint(req: BearingOptimizeRequest) -> BearingOptimizeResponse:
    try:
        opt = optimize_bearing(
            Fr_N=req.Fr_N,
            Fa_N=req.Fa_N,
            n_rpm=req.n_rpm,
            bearing_type=BearingType(req.bearing_type),
            target_hours=req.target_hours,
            S0_target=req.S0_target,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    optimal_out = None
    result_out = None
    if opt.found and opt.optimal is not None and opt.result is not None:
        optimal_out = BearingCatalogOut(
            designation=opt.optimal.designation,
            type=opt.optimal.type.value,
            C_N=opt.optimal.C_N,
            C0_N=opt.optimal.C0_N,
            d_bore_mm=opt.optimal.d_bore_mm,
        )
        result_out = _bearing_result_to_out(opt.result)
        advice_out = _advice_to_out(opt.result.advice)
    else:
        advice_out = AdviceOut(
            diagnostic=(
                "Aucun roulement du catalogue ne satisfait à la fois L10 ≥ cible "
                "ET S0 ≥ S0 cible."
            ),
            cause=(
                f"C requise ≈ {opt.C_required_N:.0f} N (pour {req.target_hours:.0f} h), "
                f"C0 requise ≈ {opt.C0_required_N:.0f} N (pour S0 ≥ {req.S0_target:.2f})."
            ),
            conseil=(
                "Passer à un roulement à rouleaux (capacité supérieure à "
                "encombrement équivalent), réduire la vitesse, ou répartir la "
                "charge sur plusieurs roulements."
            ),
            facteur_limitant="contrainte",
        )

    evaluations_out = [
        BearingEvalOut(
            designation=e.entry.designation,
            type=e.entry.type.value,
            C_N=e.entry.C_N,
            C0_N=e.entry.C0_N,
            d_bore_mm=e.entry.d_bore_mm,
            L10_hours=e.L10_hours,
            S0=e.S0,
            status_dyn=e.status_dyn,
            status_stat=e.status_stat,
        )
        for e in opt.evaluations
    ]

    return BearingOptimizeResponse(
        found=opt.found,
        C_required_N=opt.C_required_N,
        C0_required_N=opt.C0_required_N,
        P_N=opt.P_N,
        P0_N=opt.P0_N,
        e_used=opt.e_used,
        X_used=opt.X_used,
        Y_used=opt.Y_used,
        S0_target=opt.S0_target,
        optimal=optimal_out,
        result=result_out,
        target_hours=opt.target_hours,
        bearing_type=opt.bearing_type.value,
        evaluations=evaluations_out,
        advice=advice_out,
    )


# --------------------------------------------------------------------------- #
# Gear (engrenage droit) endpoints                                             #
# --------------------------------------------------------------------------- #
def _gear_geometry_to_out(geometry: GearGeometry) -> GearGeometryOut:
    return GearGeometryOut(
        m_mm=geometry.m * 1e3,
        z1=geometry.z1,
        z2=geometry.z2,
        b_mm=geometry.b * 1e3,
        d1_mm=geometry.d1 * 1e3,
        d2_mm=geometry.d2 * 1e3,
        a_mm=geometry.a * 1e3,
        u=geometry.u,
    )


def _gear_result_to_out(result) -> GearResponse:
    return GearResponse(
        geometry=_gear_geometry_to_out(result.geometry),
        Mt1_Nm=result.Mt1_Nm,
        n1_rpm=result.n1_rpm,
        Ft_N=result.Ft_N,
        Fr_N=result.Fr_N,
        v_m_s=result.v_m_s,
        K_A=result.K_A,
        K_V=result.K_V,
        sigma_F1_MPa=result.sigma_F1_Pa * 1e-6,
        sigma_F2_MPa=result.sigma_F2_Pa * 1e-6,
        sigma_F1_adm_MPa=result.sigma_F1_adm_Pa * 1e-6,
        sigma_F2_adm_MPa=result.sigma_F2_adm_Pa * 1e-6,
        sigma_H_MPa=result.sigma_H_Pa * 1e-6,
        sigma_H_adm_MPa=result.sigma_H_adm_Pa * 1e-6,
        Cs_F1=result.Cs_F1,
        Cs_F2=result.Cs_F2,
        Cs_H=result.Cs_H,
        Cs=result.Cs,
        limiting_criterion=result.limiting_criterion,
        verdict=result.verdict,
        advice=_advice_to_out(result.advice),
    )


@router.post(
    "/gear",
    response_model=GearResponse,
    summary="Vérification d'un engrenage droit (flexion Lewis + pression de Hertz)",
)
def calculate_gear_endpoint(req: GearRequest) -> GearResponse:
    try:
        material_pinion = get_material(req.material_pinion)
        material_gear = get_material(req.material_gear)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        result = calculate_gear(
            m_m=U.mm_to_m(req.m_mm),
            z1=req.z1,
            z2=req.z2,
            b_m=U.mm_to_m(req.b_mm),
            Mt1_Nm=req.Mt1_Nm,
            n1_rpm=req.n1_rpm,
            material_pinion=material_pinion,
            material_gear=material_gear,
            K_A=req.K_A,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    return _gear_result_to_out(result)


@optimize_router.post(
    "/gear",
    response_model=GearOptimizeResponse,
    summary="Sélection du plus petit module normalisé satisfaisant Cs cible",
)
def optimize_gear_endpoint(req: GearOptimizeRequest) -> GearOptimizeResponse:
    try:
        material_pinion = get_material(req.material_pinion)
        material_gear = get_material(req.material_gear)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        opt = optimize_gear(
            z1=req.z1,
            z2=req.z2,
            Mt1_Nm=req.Mt1_Nm,
            n1_rpm=req.n1_rpm,
            material_pinion=material_pinion,
            material_gear=material_gear,
            target_cs=req.target_cs,
            K_A=req.K_A,
            psi_m=req.psi_m,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    result_out = _gear_result_to_out(opt.result) if opt.found and opt.result else None
    if opt.found and opt.result is not None:
        advice_out = _advice_to_out(opt.result.advice)
    else:
        advice_out = AdviceOut(
            diagnostic=(
                "Aucun module normalisé de la série essayée ne satisfait le Cs cible."
            ),
            cause=(
                f"Cs cible = {req.target_cs:.2f}. "
                f"{len(opt.evaluations)} modules essayés "
                f"({opt.evaluations[0].m_mm:g}–{opt.evaluations[-1].m_mm:g} mm)."
            ),
            conseil=(
                "Augmenter le nombre de dents (z1, z2), choisir des matériaux "
                "à limite de fatigue plus élevée, ou augmenter psi_m (largeur "
                "de denture relative au module)."
            ),
            facteur_limitant="contrainte",
        )

    evaluations_out = [
        GearEvalOut(
            m_mm=e.m_mm,
            b_mm=e.b_mm,
            Cs=e.Cs,
            status=e.status,
            limiting_criterion=e.limiting_criterion,
        )
        for e in opt.evaluations
    ]

    return GearOptimizeResponse(
        found=opt.found,
        m_optimal_mm=opt.m_optimal_mm,
        result=result_out,
        target_safety_factor=opt.target_safety_factor,
        psi_m=opt.psi_m,
        evaluations=evaluations_out,
        advice=advice_out,
    )
