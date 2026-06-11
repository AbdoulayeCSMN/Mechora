// Mirror of backend/api/schemas.py — kept in sync manually.

export type MaterialName = "S235" | "S355" | "AL6060";
export type SupportType = "simply_supported" | "cantilever";

export type SectionInput =
  | { type: "rectangular"; width_mm: number; height_mm: number }
  | { type: "circular"; diameter_mm: number }
  | { type: "tube"; outer_diameter_mm: number; inner_diameter_mm: number };

export type LoadInput =
  | { type: "point"; magnitude_kN: number; position_m: number }
  | {
      type: "distributed";
      magnitude_kN_per_m: number;
      start_m: number;
      end_m: number;
    };

export interface BeamRequest {
  length_m: number;
  material: MaterialName | string;
  section: SectionInput;
  support: SupportType;
  loads: LoadInput[];
}

export interface SectionProperties {
  area_mm2: number;
  inertia_mm4: number;
  extreme_fiber_mm: number;
  section_modulus_mm3: number;
}

export type LimitingFactor = "contrainte" | "flèche" | "les deux" | "aucun";

export interface Advice {
  diagnostic: string;
  cause: string;
  conseil: string;
  facteur_limitant: LimitingFactor;
}

export interface BeamResponse {
  section_properties: SectionProperties;
  reactions_kN: Record<string, number>;
  x_m: number[];
  V_kN: number[];
  M_kNm: number[];
  M_max_kNm: number;
  sigma_max_MPa: number;
  f_max_mm: number;
  Cs: number;
  verdict: string;
  advice: Advice;
}

// Young's moduli (Pa) — mirrors core/materials.py. Used client-side for the
// deflection curve only (the API returns f_max, not f(x)).
export const E_BY_MATERIAL: Record<string, number> = {
  S235: 210e9,
  S355: 210e9,
  AL6060: 69e9,
};

// --- Catalog optimization (POST /optimize/beam) ---------------------------

export type ProfileFamily = "IPE" | "HEA" | "HEB" | "UPN" | "SHS" | "CHS";

export interface OptimizeRequest {
  length_m: number;
  material: MaterialName | string;
  support: SupportType;
  loads: LoadInput[];
  target_safety_factor: number;
  deflection_ratio: number;       // f_max <= L / deflection_ratio
  catalogs: ProfileFamily[] | string[];  // ["IPE", "HEA"]
}

export interface OptimalProfile {
  designation: string;
  family: string;
  mass_kg_per_m: number;
  h_mm: number;
  b_mm: number;
  area_mm2: number;
  inertia_mm4: number;
  section_modulus_mm3: number;
}

export type EvalStatus = "OK" | "Cs_insuffisant" | "fleche_excessive";

export interface ProfileEvaluation {
  designation: string;
  family: string;
  mass_kg_per_m: number;
  status: EvalStatus;
  Cs: number;
  f_max_mm: number;
  sigma_max_MPa: number;
  M_max_kNm: number;
  reason: string | null;
}

export interface OptimizeResponse {
  found: boolean;
  optimal: OptimalProfile | null;
  result: BeamResponse | null;
  evaluations: ProfileEvaluation[];
  deflection_limit_mm: number;
  target_safety_factor: number;
  advice: Advice;
}

// --- Shaft module (Von Mises) ---------------------------------------------

export type ShaftType = "solid" | "hollow";

export interface ShaftRequest {
  type: ShaftType;
  d_ext_mm: number;
  d_int_mm: number;          // 0 for solid
  material: MaterialName | string;
  Mf_Nm: number;
  Mt_Nm: number;
}

export interface ShaftSectionPropertiesOut {
  type: ShaftType;
  d_ext_mm: number;
  d_int_mm: number;
  area_mm2: number;
  W_f_mm3: number;
  W_t_mm3: number;
}

export interface ShaftResponse {
  section: ShaftSectionPropertiesOut;
  sigma_f_MPa: number;
  tau_MPa: number;
  sigma_eq_MPa: number;
  Cs: number;
  verdict: string;
  advice: Advice;
}

export interface ShaftOptimizeRequest {
  type: ShaftType;
  material: MaterialName | string;
  Mf_Nm: number;
  Mt_Nm: number;
  target_cs: number;
  d_min_mm: number;
  d_max_mm: number;
  step_mm: number;
  d_int_ratio: number;       // for hollow only
}

export interface ShaftOptimizeResponse {
  found: boolean;
  d_optimal_mm: number | null;
  result: ShaftResponse | null;
  target_safety_factor: number;
  d_min_mm: number;
  d_max_mm: number;
  step_mm: number;
  candidates_evaluated: number;
  advice: Advice;
}

// --- Key (clavette parallèle) ---------------------------------------------

export type HubMaterial = "steel" | "cast_iron" | "aluminum";
export type KeyLimitingCriterion = "cisaillement" | "matage";

export interface KeyRequest {
  shaft_diameter_mm: number;
  Mt_Nm: number;
  material_shaft: MaterialName | string;
  hub_material: HubMaterial;
  l_total_mm: number;
}

export interface KeySectionOut {
  b_mm: number;
  h_mm: number;
  l_total_mm: number;
  l_active_mm: number;
}

export interface KeyResponse {
  section: KeySectionOut;
  shaft_diameter_mm: number;
  Mt_Nm: number;
  hub_material: HubMaterial;
  tau_MPa: number;
  sigma_m_MPa: number;
  Re_shear_MPa: number;
  sigma_m_adm_MPa: number;
  Cs_shear: number;
  Cs_bearing: number;
  Cs: number;
  limiting_criterion: KeyLimitingCriterion;
  verdict: string;
  advice: Advice;
}

export interface KeyOptimizeRequest {
  shaft_diameter_mm: number;
  Mt_Nm: number;
  material_shaft: MaterialName | string;
  hub_material: HubMaterial;
  target_cs: number;
  l_min_mm: number | null;
  l_max_mm: number;
  step_mm: number;
}

export interface KeyOptimizeResponse {
  found: boolean;
  l_total_optimal_mm: number | null;
  result: KeyResponse | null;
  target_safety_factor: number;
  l_min_mm: number;
  l_max_mm: number;
  step_mm: number;
  candidates_evaluated: number;
  advice: Advice;
}

// --- Bearing (roulement, ISO 281 + ISO 76) --------------------------------

export type BearingType = "ball_radial" | "roller_cylindrical";
export type BearingEvalStatus = "OK" | "Insuffisant";

export interface BearingRequest {
  bearing_type: BearingType;
  C_N: number;
  C0_N: number;
  Fr_N: number;
  Fa_N: number;
  n_rpm: number;
  target_hours: number;
}

export interface BearingResponse {
  bearing_type: BearingType;
  C_N: number;
  C0_N: number;
  Fr_N: number;
  Fa_N: number;
  n_rpm: number;
  target_hours: number;

  // Dynamic
  P_N: number;
  e_used: number | null;
  X_used: number;
  Y_used: number;
  L10_millions: number;
  L10_hours: number;
  verdict_dynamic: string;

  // Static
  P0_N: number;
  S0: number;
  verdict_static: string;

  advice: Advice;
}

export interface BearingOptimizeRequest {
  bearing_type: BearingType;
  Fr_N: number;
  Fa_N: number;
  n_rpm: number;
  target_hours: number;
  S0_target: number;
}

export interface BearingCatalogOut {
  designation: string;
  type: BearingType;
  C_N: number;
  C0_N: number;
  d_bore_mm: number | null;
}

export interface BearingEvaluation {
  designation: string;
  type: BearingType;
  C_N: number;
  C0_N: number;
  d_bore_mm: number | null;
  L10_hours: number;
  S0: number;
  status_dyn: BearingEvalStatus;
  status_stat: BearingEvalStatus;
}

export interface BearingOptimizeResponse {
  found: boolean;
  C_required_N: number;
  C0_required_N: number;
  P_N: number;
  P0_N: number;
  e_used: number | null;
  X_used: number;
  Y_used: number;
  S0_target: number;
  optimal: BearingCatalogOut | null;
  result: BearingResponse | null;
  target_hours: number;
  bearing_type: BearingType;
  evaluations: BearingEvaluation[];
  advice: Advice;
}

// --- Gear (engrenage droit, Lewis + Hertz) --------------------------------

export type GearLimitingCriterion =
  | "flexion_pignon"
  | "flexion_roue"
  | "pression_superficielle";

export interface GearRequest {
  m_mm: number;
  z1: number;
  z2: number;
  b_mm: number;
  Mt1_Nm: number;
  n1_rpm: number;
  material_pinion: MaterialName | string;
  material_gear: MaterialName | string;
  K_A: number;
}

export interface GearGeometryOut {
  m_mm: number;
  z1: number;
  z2: number;
  b_mm: number;
  d1_mm: number;
  d2_mm: number;
  a_mm: number;
  u: number;
}

export interface GearResponse {
  geometry: GearGeometryOut;
  Mt1_Nm: number;
  n1_rpm: number;
  Ft_N: number;
  Fr_N: number;
  v_m_s: number;
  K_A: number;
  K_V: number;
  sigma_F1_MPa: number;
  sigma_F2_MPa: number;
  sigma_F1_adm_MPa: number;
  sigma_F2_adm_MPa: number;
  sigma_H_MPa: number;
  sigma_H_adm_MPa: number;
  Cs_F1: number;
  Cs_F2: number;
  Cs_H: number;
  Cs: number;
  limiting_criterion: GearLimitingCriterion;
  verdict: string;
  advice: Advice;
}

export interface GearOptimizeRequest {
  z1: number;
  z2: number;
  Mt1_Nm: number;
  n1_rpm: number;
  material_pinion: MaterialName | string;
  material_gear: MaterialName | string;
  target_cs: number;
  K_A: number;
  psi_m: number;
}

export type GearEvalStatus = "OK" | "insuffisant";

export interface GearEvaluation {
  m_mm: number;
  b_mm: number;
  Cs: number;
  status: GearEvalStatus;
  limiting_criterion: GearLimitingCriterion;
}

export interface GearOptimizeResponse {
  found: boolean;
  m_optimal_mm: number | null;
  result: GearResponse | null;
  target_safety_factor: number;
  psi_m: number;
  evaluations: GearEvaluation[];
  advice: Advice;
}
