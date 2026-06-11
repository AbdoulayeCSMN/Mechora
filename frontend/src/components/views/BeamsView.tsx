import { useMemo, useState } from "react";
import { Calculator, Loader2, Wand2 } from "lucide-react";

import AdviceCard from "../AdviceCard";
import BeamInput from "../BeamInput";
import BeamDiagram from "../BeamDiagram";
import Charts from "../Charts";
import OptimizeInput from "../OptimizeInput";
import OptimizeResults from "../OptimizeResults";
import ResultPanel from "../ResultPanel";
import { ApiError, calculateBeam, optimizeBeam } from "../../api/client";
import type {
  BeamRequest,
  BeamResponse,
  LoadInput,
  OptimizeRequest,
  OptimizeResponse,
  SectionInput,
  SupportType,
} from "../../types";

import KPIRow, { type KPI } from "../dashboard/KPIRow";
import TopBar from "../dashboard/TopBar";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type Mode = "verify" | "optimize";

interface Common {
  length_m: number;
  material: string;
  support: SupportType;
  loads: LoadInput[];
}

const DEFAULT_COMMON: Common = {
  length_m: 4.0,
  material: "S235",
  support: "simply_supported",
  loads: [{ type: "point", magnitude_kN: 10, position_m: 2.0 }],
};

const DEFAULT_SECTION: SectionInput = {
  type: "rectangular",
  width_mm: 50,
  height_mm: 100,
};

const DEFAULT_OPT_PARAMS = {
  target_safety_factor: 2.0,
  deflection_ratio: 200.0,
  catalogs: ["IPE", "HEA"],
};

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

function verdictTone(v?: string): KPI["tone"] {
  switch (v) {
    case "OK":              return "success";
    case "Limite":          return "warning";
    case "Sous-dimensionné": return "destructive";
    case "Surdimensionné": return "info";
    default:                 return "neutral";
  }
}

function buildKpis(
  mode: Mode,
  verifyResult: BeamResponse | null,
  optimizeResult: OptimizeResponse | null,
): KPI[] {
  if (mode === "verify" && verifyResult) {
    const v = verifyResult;
    return [
      { label: "Verdict", value: v.verdict, tone: verdictTone(v.verdict), caption: `Cs = ${fmt(v.Cs, 3)}` },
      { label: "Contrainte max", value: fmt(v.sigma_max_MPa, 4), unit: "MPa", tone: v.Cs < 1 ? "destructive" : v.Cs < 1.5 ? "warning" : "neutral" },
      { label: "Flèche max", value: fmt(v.f_max_mm, 4), unit: "mm" },
      { label: "Moment max", value: fmt(v.M_max_kNm, 4), unit: "kN·m" },
      { label: "Inertie I", value: fmt(v.section_properties.inertia_mm4, 4), unit: "mm⁴" },
    ];
  }
  if (mode === "optimize" && optimizeResult) {
    const o = optimizeResult;
    if (!o.found || !o.optimal || !o.result) {
      return [
        { label: "Résultat", value: "Aucune solution", tone: "destructive", caption: `${o.evaluations.length} profilés évalués` },
        { label: "Cs cible", value: fmt(o.target_safety_factor, 3) },
        { label: "Flèche admise", value: fmt(o.deflection_limit_mm, 4), unit: "mm" },
        { label: "Profilés évalués", value: String(o.evaluations.length), caption: "Aucun ne tient" },
      ];
    }
    return [
      { label: "Profilé retenu", value: o.optimal.designation, tone: "success", caption: `Cs = ${fmt(o.result.Cs, 3)}` },
      { label: "Masse linéique", value: fmt(o.optimal.mass_kg_per_m, 3), unit: "kg/m", tone: "success", trend: "down" },
      { label: "Flèche f", value: fmt(o.result.f_max_mm, 4), unit: "mm", caption: `≤ ${fmt(o.deflection_limit_mm, 4)} mm` },
      { label: "Contrainte σ", value: fmt(o.result.sigma_max_MPa, 4), unit: "MPa" },
      { label: "Module Wy", value: fmt(o.optimal.section_modulus_mm3, 4), unit: "mm³" },
    ];
  }
  return [
    { label: "Verdict", value: "—", caption: "En attente de calcul" },
    { label: "Contrainte max σ", value: "—", unit: "MPa" },
    { label: "Flèche max f", value: "—", unit: "mm" },
    { label: "Moment max M", value: "—", unit: "kN·m" },
    { label: "Inertie I", value: "—", unit: "mm⁴" },
  ];
}

function downloadJson(filename: string, payload: unknown) {
  const data = JSON.stringify(payload, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function BeamsView() {
  const [mode, setMode] = useState<Mode>("verify");
  const [common, setCommon] = useState<Common>(DEFAULT_COMMON);
  const [section, setSection] = useState<SectionInput>(DEFAULT_SECTION);
  const [optParams, setOptParams] = useState(DEFAULT_OPT_PARAMS);

  const [verifyResult, setVerifyResult] = useState<BeamResponse | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastComputed, setLastComputed] = useState<Date | null>(null);

  const verifyBeam: BeamRequest = useMemo(
    () => ({ ...common, section }),
    [common, section],
  );

  const optimizeReq: OptimizeRequest = useMemo(
    () => ({ ...common, ...optParams }),
    [common, optParams],
  );

  const setVerifyBeam = (b: BeamRequest) => {
    setCommon({
      length_m: b.length_m,
      material: b.material,
      support: b.support,
      loads: b.loads,
    });
    setSection(b.section);
  };

  const setOptimizeReq = (r: OptimizeRequest) => {
    setCommon({
      length_m: r.length_m,
      material: r.material,
      support: r.support,
      loads: r.loads,
    });
    setOptParams({
      target_safety_factor: r.target_safety_factor,
      deflection_ratio: r.deflection_ratio,
      catalogs: r.catalogs,
    });
  };

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await calculateBeam(verifyBeam);
      setVerifyResult(r);
      setLastComputed(new Date());
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setError(msg);
      setVerifyResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await optimizeBeam(optimizeReq);
      setOptimizeResult(r);
      setLastComputed(new Date());
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setError(msg);
      setOptimizeResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    if (mode === "verify" && verifyResult) {
      downloadJson(`mechora-beam-verify-${ts}.json`, {
        module: "beams", mode,
        request: verifyBeam, response: verifyResult,
        exported_at: new Date().toISOString(),
      });
    } else if (mode === "optimize" && optimizeResult) {
      downloadJson(`mechora-beam-optimize-${ts}.json`, {
        module: "beams", mode,
        request: optimizeReq, response: optimizeResult,
        exported_at: new Date().toISOString(),
      });
    }
  };

  const handleReset = () => {
    setCommon(DEFAULT_COMMON);
    setSection(DEFAULT_SECTION);
    setOptParams(DEFAULT_OPT_PARAMS);
    setVerifyResult(null);
    setOptimizeResult(null);
    setError(null);
    setLastComputed(null);
  };

  const switchMode = (m: Mode) => {
    setMode(m);
    setError(null);
  };

  const canExport =
    (mode === "verify" && verifyResult !== null) ||
    (mode === "optimize" && optimizeResult !== null);

  const kpis = buildKpis(mode, verifyResult, optimizeResult);

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      <TopBar
        module="beams"
        mode={mode}
        lastComputed={lastComputed}
        onReset={handleReset}
        onExport={handleExport}
        canExport={canExport}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1640px] mx-auto p-4 md:p-6 space-y-5">
          <div className="md:hidden">
            <ToggleGroup
              type="single"
              value={mode}
              onValueChange={(v) => v && switchMode(v as Mode)}
            >
              <ToggleGroupItem value="verify">
                <Calculator className="mr-2 h-4 w-4" /> Vérification
              </ToggleGroupItem>
              <ToggleGroupItem value="optimize">
                <Wand2 className="mr-2 h-4 w-4" /> Optimisation
              </ToggleGroupItem>
            </ToggleGroup>
          </div>

          <KPIRow items={kpis} />

          <div className="grid grid-cols-1 xl:grid-cols-[400px_minmax(0,1fr)] gap-5">
            <Card className="xl:sticky xl:top-4 xl:self-start">
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle>Configuration</CardTitle>
                <div className="hidden md:block">
                  <ToggleGroup
                    type="single"
                    value={mode}
                    onValueChange={(v) => v && switchMode(v as Mode)}
                    className="h-7 p-0.5 w-auto"
                  >
                    <ToggleGroupItem value="verify" className="text-[11px] px-2 py-1 h-6">
                      Vérif.
                    </ToggleGroupItem>
                    <ToggleGroupItem value="optimize" className="text-[11px] px-2 py-1 h-6">
                      Optim.
                    </ToggleGroupItem>
                  </ToggleGroup>
                </div>
              </CardHeader>
              <CardContent className="space-y-0">
                {mode === "verify" ? (
                  <BeamInput state={verifyBeam} setState={setVerifyBeam} />
                ) : (
                  <OptimizeInput state={optimizeReq} setState={setOptimizeReq} />
                )}

                <Separator className="my-4" />

                <Button
                  className="w-full"
                  onClick={mode === "verify" ? handleVerify : handleOptimize}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {mode === "verify" ? "Calcul…" : "Recherche…"}
                    </>
                  ) : mode === "verify" ? (
                    <>
                      <Calculator className="h-4 w-4" />
                      Lancer le calcul
                    </>
                  ) : (
                    <>
                      <Wand2 className="h-4 w-4" />
                      Trouver le profilé optimal
                    </>
                  )}
                </Button>

                {error && (
                  <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive font-mono whitespace-pre-wrap">
                    <span className="font-sans font-semibold">Erreur · </span>
                    {error}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-5 min-w-0">
              <BeamDiagram
                length_m={common.length_m}
                support={common.support}
                loads={common.loads}
              />
              {mode === "verify" && verifyResult && <ResultPanel result={verifyResult} />}
              {mode === "verify" && !verifyResult && !error && <EmptyState mode={mode} />}
            </div>
          </div>

          {mode === "verify" && verifyResult && (
            <>
              <AdviceCard
                advice={verifyResult.advice}
                verdict={verifyResult.verdict}
                onOptimize={
                  verifyResult.verdict === "Surdimensionné"
                    ? () => switchMode("optimize")
                    : undefined
                }
              />
              <Charts result={verifyResult} material={common.material} support={common.support} />
            </>
          )}

          {mode === "optimize" && optimizeResult && (
            <>
              <OptimizeResults response={optimizeResult} />
              <AdviceCard advice={optimizeResult.advice} verdict={optimizeResult.result?.verdict} />
              {optimizeResult.found && optimizeResult.result && (
                <Charts
                  result={optimizeResult.result}
                  material={common.material}
                  support={common.support}
                />
              )}
            </>
          )}

          {mode === "optimize" && !optimizeResult && !error && <EmptyState mode={mode} />}
        </div>
      </main>
    </div>
  );
}

function EmptyState({ mode }: { mode: Mode }) {
  return (
    <Card>
      <CardContent className="pt-10 pb-10 text-center text-muted-foreground text-sm">
        {mode === "verify" ? (
          <>
            Configure la poutre dans le panneau Configuration puis lance le
            calcul pour remplir les KPI, le panneau Résultats et les diagrammes.
          </>
        ) : (
          <>
            Saisis le chargement et les critères dans le panneau Configuration,
            puis lance la recherche pour trouver le profilé normalisé le plus léger.
          </>
        )}
      </CardContent>
    </Card>
  );
}
