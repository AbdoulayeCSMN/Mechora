import { useState } from "react";
import { Calculator, Loader2, Wand2 } from "lucide-react";

import AdviceCard from "../AdviceCard";
import GearInput from "../GearInput";
import GearOptimizeInput from "../GearOptimizeInput";
import GearResultPanel from "../GearResultPanel";
import GearOptimizeResults from "../GearOptimizeResults";
import { ApiError, calculateGear, optimizeGear } from "../../api/client";
import type {
  GearOptimizeRequest,
  GearOptimizeResponse,
  GearRequest,
  GearResponse,
} from "../../types";

import KPIRow, { type KPI } from "../dashboard/KPIRow";
import TopBar from "../dashboard/TopBar";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type Mode = "verify" | "optimize";

const DEFAULT_GEAR: GearRequest = {
  m_mm: 3,
  z1: 20,
  z2: 40,
  b_mm: 30,
  Mt1_Nm: 50,
  n1_rpm: 1000,
  material_pinion: "S235",
  material_gear: "S235",
  K_A: 1.0,
};

const DEFAULT_OPT: GearOptimizeRequest = {
  z1: 20,
  z2: 40,
  Mt1_Nm: 50,
  n1_rpm: 1000,
  material_pinion: "S235",
  material_gear: "S235",
  target_cs: 1.5,
  K_A: 1.0,
  psi_m: 10,
};

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

const LIMITING_LABEL: Record<string, string> = {
  flexion_pignon: "flexion (pignon)",
  flexion_roue: "flexion (roue)",
  pression_superficielle: "pression de contact",
};

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
  verifyResult: GearResponse | null,
  optimizeResult: GearOptimizeResponse | null,
): KPI[] {
  if (mode === "verify" && verifyResult) {
    const v = verifyResult;
    return [
      { label: "Verdict", value: v.verdict, tone: verdictTone(v.verdict), caption: `Cs = ${fmt(v.Cs, 3)} · ${LIMITING_LABEL[v.limiting_criterion] ?? v.limiting_criterion}` },
      { label: "σ_F1 pignon", value: fmt(v.sigma_F1_MPa, 4), unit: "MPa", caption: `Cs = ${fmt(v.Cs_F1, 3)}` },
      { label: "σ_F2 roue", value: fmt(v.sigma_F2_MPa, 4), unit: "MPa", caption: `Cs = ${fmt(v.Cs_F2, 3)}` },
      { label: "σ_H contact", value: fmt(v.sigma_H_MPa, 4), unit: "MPa", caption: `Cs = ${fmt(v.Cs_H, 3)}` },
      { label: "Entraxe a", value: fmt(v.geometry.a_mm, 4), unit: "mm" },
    ];
  }
  if (mode === "optimize" && optimizeResult) {
    const o = optimizeResult;
    if (!o.found || !o.result || o.m_optimal_mm === null) {
      return [
        { label: "Résultat", value: "Aucune solution", tone: "destructive", caption: `${o.evaluations.length} modules essayés` },
        { label: "Cs cible", value: fmt(o.target_safety_factor, 3) },
        { label: "ψ_m = b/m", value: fmt(o.psi_m, 3) },
      ];
    }
    return [
      { label: "Module optimal", value: fmt(o.m_optimal_mm, 4), unit: "mm", tone: "success", trend: "down", caption: `Cs = ${fmt(o.result.Cs, 3)}` },
      { label: "Largeur b", value: fmt(o.result.geometry.b_mm, 4), unit: "mm" },
      { label: "Entraxe a", value: fmt(o.result.geometry.a_mm, 4), unit: "mm" },
      { label: "Cs pression contact", value: fmt(o.result.Cs_H, 3) },
      { label: "Limitant", value: LIMITING_LABEL[o.result.limiting_criterion] ?? o.result.limiting_criterion },
    ];
  }
  return [
    { label: "Verdict", value: "—", caption: "En attente de calcul" },
    { label: "σ_F1 pignon", value: "—", unit: "MPa" },
    { label: "σ_F2 roue", value: "—", unit: "MPa" },
    { label: "σ_H contact", value: "—", unit: "MPa" },
    { label: "Entraxe a", value: "—", unit: "mm" },
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

export default function GearsView() {
  const [mode, setMode] = useState<Mode>("verify");
  const [verifyReq, setVerifyReq] = useState<GearRequest>(DEFAULT_GEAR);
  const [optReq, setOptReq] = useState<GearOptimizeRequest>(DEFAULT_OPT);

  const [verifyResult, setVerifyResult] = useState<GearResponse | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<GearOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastComputed, setLastComputed] = useState<Date | null>(null);

  const handleVerify = async () => {
    setLoading(true); setError(null);
    try {
      const r = await calculateGear(verifyReq);
      setVerifyResult(r);
      setLastComputed(new Date());
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setError(msg); setVerifyResult(null);
    } finally { setLoading(false); }
  };

  const handleOptimize = async () => {
    setLoading(true); setError(null);
    try {
      const r = await optimizeGear(optReq);
      setOptimizeResult(r);
      setLastComputed(new Date());
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setError(msg); setOptimizeResult(null);
    } finally { setLoading(false); }
  };

  const handleExport = () => {
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    if (mode === "verify" && verifyResult) {
      downloadJson(`mechora-gear-verify-${ts}.json`, {
        module: "gears", mode, request: verifyReq, response: verifyResult,
        exported_at: new Date().toISOString(),
      });
    } else if (mode === "optimize" && optimizeResult) {
      downloadJson(`mechora-gear-optimize-${ts}.json`, {
        module: "gears", mode, request: optReq, response: optimizeResult,
        exported_at: new Date().toISOString(),
      });
    }
  };

  const handleReset = () => {
    setVerifyReq(DEFAULT_GEAR); setOptReq(DEFAULT_OPT);
    setVerifyResult(null); setOptimizeResult(null);
    setError(null); setLastComputed(null);
  };

  const switchMode = (m: Mode) => { setMode(m); setError(null); };

  const canExport =
    (mode === "verify" && verifyResult !== null) ||
    (mode === "optimize" && optimizeResult !== null);

  const kpis = buildKpis(mode, verifyResult, optimizeResult);

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      <TopBar
        module="gears"
        mode={mode}
        lastComputed={lastComputed}
        onReset={handleReset}
        onExport={handleExport}
        canExport={canExport}
      />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1640px] mx-auto p-4 md:p-6 space-y-5">
          <div className="md:hidden">
            <ToggleGroup type="single" value={mode} onValueChange={(v) => v && switchMode(v as Mode)}>
              <ToggleGroupItem value="verify"><Calculator className="mr-2 h-4 w-4" /> Vérif.</ToggleGroupItem>
              <ToggleGroupItem value="optimize"><Wand2 className="mr-2 h-4 w-4" /> Optim.</ToggleGroupItem>
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
                    <ToggleGroupItem value="verify" className="text-[11px] px-2 py-1 h-6">Vérif.</ToggleGroupItem>
                    <ToggleGroupItem value="optimize" className="text-[11px] px-2 py-1 h-6">Optim.</ToggleGroupItem>
                  </ToggleGroup>
                </div>
              </CardHeader>
              <CardContent className="space-y-0">
                {mode === "verify"
                  ? <GearInput state={verifyReq} setState={setVerifyReq} />
                  : <GearOptimizeInput state={optReq} setState={setOptReq} />}
                <Separator className="my-4" />
                <Button
                  className="w-full"
                  onClick={mode === "verify" ? handleVerify : handleOptimize}
                  disabled={loading}
                >
                  {loading
                    ? <><Loader2 className="h-4 w-4 animate-spin" />{mode === "verify" ? "Calcul…" : "Recherche…"}</>
                    : mode === "verify"
                      ? <><Calculator className="h-4 w-4" />Lancer le calcul</>
                      : <><Wand2 className="h-4 w-4" />Trouver le module optimal</>}
                </Button>
                {error && (
                  <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive font-mono whitespace-pre-wrap">
                    <span className="font-sans font-semibold">Erreur · </span>{error}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-5 min-w-0">
              {mode === "verify" && verifyResult && <GearResultPanel result={verifyResult} />}
              {mode === "verify" && !verifyResult && !error && <EmptyState mode={mode} />}
              {mode === "optimize" && optimizeResult && <GearOptimizeResults response={optimizeResult} />}
              {mode === "optimize" && !optimizeResult && !error && <EmptyState mode={mode} />}
            </div>
          </div>

          {mode === "verify" && verifyResult && (
            <AdviceCard advice={verifyResult.advice} verdict={verifyResult.verdict}
              onOptimize={verifyResult.verdict === "Surdimensionné" ? () => switchMode("optimize") : undefined} />
          )}
          {mode === "optimize" && optimizeResult && (
            <AdviceCard advice={optimizeResult.advice} verdict={optimizeResult.result?.verdict} />
          )}
        </div>
      </main>
    </div>
  );
}

function EmptyState({ mode }: { mode: Mode }) {
  return (
    <Card>
      <CardContent className="pt-10 pb-10 text-center text-muted-foreground text-sm">
        {mode === "verify"
          ? "Configure l'engrenage puis lance le calcul pour vérifier la flexion (Lewis) et la pression de contact (Hertz)."
          : "Saisis le couple, la vitesse et les critères, puis lance la recherche du module minimal."}
      </CardContent>
    </Card>
  );
}
