import { useState } from "react";
import { Calculator, Loader2, Wand2 } from "lucide-react";

import AdviceCard from "../AdviceCard";
import KeyInput from "../KeyInput";
import KeyOptimizeInput from "../KeyOptimizeInput";
import KeyResultPanel from "../KeyResultPanel";
import KeyOptimizeResults from "../KeyOptimizeResults";
import { ApiError, calculateKey, optimizeKey } from "../../api/client";
import type {
  KeyOptimizeRequest,
  KeyOptimizeResponse,
  KeyRequest,
  KeyResponse,
} from "../../types";

import KPIRow, { type KPI } from "../dashboard/KPIRow";
import TopBar from "../dashboard/TopBar";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type Mode = "verify" | "optimize";

const DEFAULT_KEY: KeyRequest = {
  shaft_diameter_mm: 25,
  Mt_Nm: 80,
  material_shaft: "S235",
  hub_material: "steel",
  l_total_mm: 40,
};

const DEFAULT_OPT: KeyOptimizeRequest = {
  shaft_diameter_mm: 25,
  Mt_Nm: 120,
  material_shaft: "S235",
  hub_material: "steel",
  target_cs: 2.0,
  l_min_mm: null,
  l_max_mm: 200,
  step_mm: 1,
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
  verifyResult: KeyResponse | null,
  optimizeResult: KeyOptimizeResponse | null,
): KPI[] {
  if (mode === "verify" && verifyResult) {
    const v = verifyResult;
    return [
      { label: "Verdict", value: v.verdict, tone: verdictTone(v.verdict), caption: `Cs = ${fmt(v.Cs, 3)} · ${v.limiting_criterion}` },
      { label: "τ cisaillement", value: fmt(v.tau_MPa, 4), unit: "MPa", caption: `adm ${fmt(v.Re_shear_MPa, 4)} MPa` },
      { label: "σ_m matage", value: fmt(v.sigma_m_MPa, 4), unit: "MPa", caption: `adm ${fmt(v.sigma_m_adm_MPa, 4)} MPa` },
      { label: "Cs cisaillement", value: fmt(v.Cs_shear, 3) },
      { label: "Cs matage", value: fmt(v.Cs_bearing, 3) },
    ];
  }
  if (mode === "optimize" && optimizeResult) {
    const o = optimizeResult;
    if (!o.found || !o.result || o.l_total_optimal_mm === null) {
      return [
        { label: "Résultat", value: "Aucune solution", tone: "destructive", caption: `${o.candidates_evaluated} longueurs essayées` },
        { label: "Cs cible", value: fmt(o.target_safety_factor, 3) },
        { label: "Plage l", value: `${o.l_min_mm}–${o.l_max_mm}`, unit: "mm" },
        { label: "Pas", value: fmt(o.step_mm, 3), unit: "mm" },
      ];
    }
    return [
      { label: "l_total optimal", value: fmt(o.l_total_optimal_mm, 4), unit: "mm", tone: "success", trend: "down", caption: `Cs = ${fmt(o.result.Cs, 3)}` },
      { label: "Section ISO", value: `${o.result.section.b_mm} × ${o.result.section.h_mm}`, unit: "mm" },
      { label: "Cs cisaillement", value: fmt(o.result.Cs_shear, 3) },
      { label: "Cs matage", value: fmt(o.result.Cs_bearing, 3) },
      { label: "Limitant", value: o.result.limiting_criterion },
    ];
  }
  return [
    { label: "Verdict", value: "—", caption: "En attente de calcul" },
    { label: "τ cisaillement", value: "—", unit: "MPa" },
    { label: "σ_m matage", value: "—", unit: "MPa" },
    { label: "Cs cisaillement", value: "—" },
    { label: "Cs matage", value: "—" },
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

export default function KeysView() {
  const [mode, setMode] = useState<Mode>("verify");
  const [verifyReq, setVerifyReq] = useState<KeyRequest>(DEFAULT_KEY);
  const [optReq, setOptReq] = useState<KeyOptimizeRequest>(DEFAULT_OPT);

  const [verifyResult, setVerifyResult] = useState<KeyResponse | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<KeyOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastComputed, setLastComputed] = useState<Date | null>(null);

  const handleVerify = async () => {
    setLoading(true); setError(null);
    try {
      const r = await calculateKey(verifyReq);
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
      const r = await optimizeKey(optReq);
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
      downloadJson(`mechora-key-verify-${ts}.json`, {
        module: "keys", mode, request: verifyReq, response: verifyResult,
        exported_at: new Date().toISOString(),
      });
    } else if (mode === "optimize" && optimizeResult) {
      downloadJson(`mechora-key-optimize-${ts}.json`, {
        module: "keys", mode, request: optReq, response: optimizeResult,
        exported_at: new Date().toISOString(),
      });
    }
  };

  const handleReset = () => {
    setVerifyReq(DEFAULT_KEY); setOptReq(DEFAULT_OPT);
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
        module="keys"
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
                  ? <KeyInput state={verifyReq} setState={setVerifyReq} />
                  : <KeyOptimizeInput state={optReq} setState={setOptReq} />}
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
                      : <><Wand2 className="h-4 w-4" />Trouver la longueur optimale</>}
                </Button>
                {error && (
                  <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive font-mono whitespace-pre-wrap">
                    <span className="font-sans font-semibold">Erreur · </span>{error}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-5 min-w-0">
              {mode === "verify" && verifyResult && <KeyResultPanel result={verifyResult} />}
              {mode === "verify" && !verifyResult && !error && <EmptyState mode={mode} />}
              {mode === "optimize" && optimizeResult && <KeyOptimizeResults response={optimizeResult} />}
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
          ? "Configure la clavette puis lance le calcul pour vérifier les critères de cisaillement et matage."
          : "Saisis le couple et les critères, puis lance la recherche de la longueur minimale."}
      </CardContent>
    </Card>
  );
}
