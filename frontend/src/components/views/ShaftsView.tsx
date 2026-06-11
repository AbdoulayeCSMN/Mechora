import { useState } from "react";
import { Calculator, Loader2, Wand2 } from "lucide-react";

import AdviceCard from "../AdviceCard";
import ShaftInput from "../ShaftInput";
import ShaftOptimizeInput from "../ShaftOptimizeInput";
import ShaftDiagram from "../ShaftDiagram";
import ShaftResultPanel from "../ShaftResultPanel";
import ShaftOptimizeResults from "../ShaftOptimizeResults";
import { ApiError, calculateShaft, optimizeShaft } from "../../api/client";
import type {
  ShaftOptimizeRequest,
  ShaftOptimizeResponse,
  ShaftRequest,
  ShaftResponse,
} from "../../types";

import KPIRow, { type KPI } from "../dashboard/KPIRow";
import TopBar from "../dashboard/TopBar";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type Mode = "verify" | "optimize";

const DEFAULT_SHAFT: ShaftRequest = {
  type: "solid",
  d_ext_mm: 40,
  d_int_mm: 0,
  material: "S235",
  Mf_Nm: 200,
  Mt_Nm: 150,
};

const DEFAULT_OPT: ShaftOptimizeRequest = {
  type: "solid",
  material: "S235",
  Mf_Nm: 200,
  Mt_Nm: 150,
  target_cs: 2.0,
  d_min_mm: 10,
  d_max_mm: 200,
  step_mm: 1,
  d_int_ratio: 0.7,
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
  verifyResult: ShaftResponse | null,
  optimizeResult: ShaftOptimizeResponse | null,
): KPI[] {
  if (mode === "verify" && verifyResult) {
    const v = verifyResult;
    return [
      { label: "Verdict", value: v.verdict, tone: verdictTone(v.verdict), caption: `Cs = ${fmt(v.Cs, 3)}` },
      { label: "σ_eq Von Mises", value: fmt(v.sigma_eq_MPa, 4), unit: "MPa", tone: v.Cs < 1 ? "destructive" : v.Cs < 1.5 ? "warning" : "neutral" },
      { label: "σ_f flexion", value: fmt(v.sigma_f_MPa, 4), unit: "MPa" },
      { label: "τ torsion", value: fmt(v.tau_MPa, 4), unit: "MPa" },
      { label: "W_f", value: fmt(v.section.W_f_mm3, 4), unit: "mm³" },
    ];
  }
  if (mode === "optimize" && optimizeResult) {
    const o = optimizeResult;
    if (!o.found || !o.result || o.d_optimal_mm === null) {
      return [
        { label: "Résultat", value: "Aucune solution", tone: "destructive", caption: `${o.candidates_evaluated} diamètres essayés` },
        { label: "Cs cible", value: fmt(o.target_safety_factor, 3) },
        { label: "Plage d", value: `${o.d_min_mm}–${o.d_max_mm}`, unit: "mm" },
        { label: "Pas", value: fmt(o.step_mm, 3), unit: "mm" },
      ];
    }
    return [
      { label: "Diamètre optimal", value: fmt(o.d_optimal_mm, 4), unit: "mm", tone: "success", trend: "down", caption: `Cs = ${fmt(o.result.Cs, 3)}` },
      { label: "σ_eq Von Mises", value: fmt(o.result.sigma_eq_MPa, 4), unit: "MPa" },
      { label: "σ_f flexion", value: fmt(o.result.sigma_f_MPa, 4), unit: "MPa" },
      { label: "τ torsion", value: fmt(o.result.tau_MPa, 4), unit: "MPa" },
      { label: "Diamètres testés", value: String(o.candidates_evaluated) },
    ];
  }
  return [
    { label: "Verdict", value: "—", caption: "En attente de calcul" },
    { label: "σ_eq Von Mises", value: "—", unit: "MPa" },
    { label: "σ_f flexion", value: "—", unit: "MPa" },
    { label: "τ torsion", value: "—", unit: "MPa" },
    { label: "W_f", value: "—", unit: "mm³" },
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

export default function ShaftsView() {
  const [mode, setMode] = useState<Mode>("verify");
  const [shaft, setShaft] = useState<ShaftRequest>(DEFAULT_SHAFT);
  const [optReq, setOptReq] = useState<ShaftOptimizeRequest>(DEFAULT_OPT);

  const [verifyResult, setVerifyResult] = useState<ShaftResponse | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<ShaftOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastComputed, setLastComputed] = useState<Date | null>(null);

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await calculateShaft(shaft);
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
      const r = await optimizeShaft(optReq);
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
      downloadJson(`mechora-shaft-verify-${ts}.json`, {
        module: "shafts", mode,
        request: shaft, response: verifyResult,
        exported_at: new Date().toISOString(),
      });
    } else if (mode === "optimize" && optimizeResult) {
      downloadJson(`mechora-shaft-optimize-${ts}.json`, {
        module: "shafts", mode,
        request: optReq, response: optimizeResult,
        exported_at: new Date().toISOString(),
      });
    }
  };

  const handleReset = () => {
    setShaft(DEFAULT_SHAFT);
    setOptReq(DEFAULT_OPT);
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

  // For the SVG diagram we want to show the user's current input
  const diagSection =
    mode === "verify"
      ? { type: shaft.type, d_ext_mm: shaft.d_ext_mm, d_int_mm: shaft.d_int_mm }
      : optimizeResult?.found && optimizeResult.result
      ? {
          type: optimizeResult.result.section.type,
          d_ext_mm: optimizeResult.result.section.d_ext_mm,
          d_int_mm: optimizeResult.result.section.d_int_mm,
        }
      : { type: optReq.type, d_ext_mm: optReq.d_max_mm, d_int_mm: optReq.type === "hollow" ? optReq.d_max_mm * optReq.d_int_ratio : 0 };

  const diagMf = mode === "verify" ? shaft.Mf_Nm : optReq.Mf_Nm;
  const diagMt = mode === "verify" ? shaft.Mt_Nm : optReq.Mt_Nm;

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      <TopBar
        module="shafts"
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
                  <ShaftInput state={shaft} setState={setShaft} />
                ) : (
                  <ShaftOptimizeInput state={optReq} setState={setOptReq} />
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
                      Trouver le diamètre optimal
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
              <ShaftDiagram
                type={diagSection.type}
                d_ext_mm={diagSection.d_ext_mm}
                d_int_mm={diagSection.d_int_mm}
                Mf_Nm={diagMf}
                Mt_Nm={diagMt}
              />
              {mode === "verify" && verifyResult && <ShaftResultPanel result={verifyResult} />}
              {mode === "verify" && !verifyResult && !error && <EmptyState mode={mode} />}
            </div>
          </div>

          {mode === "verify" && verifyResult && (
            <AdviceCard
              advice={verifyResult.advice}
              verdict={verifyResult.verdict}
              onOptimize={
                verifyResult.verdict === "Surdimensionné"
                  ? () => switchMode("optimize")
                  : undefined
              }
            />
          )}

          {mode === "optimize" && optimizeResult && (
            <>
              <ShaftOptimizeResults response={optimizeResult} />
              <AdviceCard
                advice={optimizeResult.advice}
                verdict={optimizeResult.result?.verdict}
              />
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
            Configure l'arbre dans le panneau Configuration puis lance le
            calcul pour afficher la contrainte équivalente de Von Mises et le verdict.
          </>
        ) : (
          <>
            Saisis les moments et les critères, puis lance la recherche
            du diamètre minimum qui satisfait le Cs cible.
          </>
        )}
      </CardContent>
    </Card>
  );
}
