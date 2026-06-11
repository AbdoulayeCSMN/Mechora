import { useState } from "react";
import { Calculator, Loader2, Wand2 } from "lucide-react";

import AdviceCard from "../AdviceCard";
import BearingInput from "../BearingInput";
import BearingOptimizeInput from "../BearingOptimizeInput";
import BearingResultPanel from "../BearingResultPanel";
import BearingOptimizeResults from "../BearingOptimizeResults";
import { ApiError, calculateBearing, optimizeBearing } from "../../api/client";
import type {
  BearingOptimizeRequest,
  BearingOptimizeResponse,
  BearingRequest,
  BearingResponse,
} from "../../types";

import KPIRow, { type KPI } from "../dashboard/KPIRow";
import TopBar from "../dashboard/TopBar";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type Mode = "verify" | "optimize";

const DEFAULT_BEARING: BearingRequest = {
  bearing_type: "ball_radial",
  C_N: 12_800,
  C0_N: 6_600,
  Fr_N: 4_000,
  Fa_N: 2_500,
  n_rpm: 200,
  target_hours: 20_000,
};

const DEFAULT_OPT: BearingOptimizeRequest = {
  bearing_type: "ball_radial",
  Fr_N: 3_000,
  Fa_N: 0,
  n_rpm: 1_500,
  target_hours: 20_000,
  S0_target: 1.0,
};

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

const fmtHours = (n: number) =>
  Number.isFinite(n)
    ? n >= 1e6 ? (n / 1e6).toFixed(1) + " M" : Math.round(n).toLocaleString("fr-FR")
    : "–";

function dynamicTone(v?: string): KPI["tone"] {
  switch (v) {
    case "OK":             return "success";
    case "Limite":         return "warning";
    case "Insuffisant":    return "destructive";
    case "Surdimensionné": return "info";
    default:               return "neutral";
  }
}

function staticTone(v?: string): KPI["tone"] {
  if (!v) return "neutral";
  if (v.startsWith("Insuffisant")) return "destructive";
  if (v.includes("limite")) return "warning";
  if (v.includes("chocs OK")) return "info";
  return "success";
}

function buildKpis(
  mode: Mode,
  verifyResult: BearingResponse | null,
  optimizeResult: BearingOptimizeResponse | null,
): KPI[] {
  if (mode === "verify" && verifyResult) {
    const v = verifyResult;
    const ratio = v.target_hours > 0 ? v.L10_hours / v.target_hours : 0;
    return [
      { label: "Dynamique", value: v.verdict_dynamic, tone: dynamicTone(v.verdict_dynamic), caption: `L10 / cible = ${fmt(ratio, 3)}` },
      { label: "Statique S0", value: fmt(v.S0, 3), tone: staticTone(v.verdict_static), caption: v.verdict_static },
      { label: "L10h", value: fmtHours(v.L10_hours), unit: "h" },
      { label: "P / P0", value: `${fmt(v.P_N, 4)} / ${fmt(v.P0_N, 4)}`, unit: "N" },
      { label: "C / C0", value: `${fmt(v.C_N, 4)} / ${fmt(v.C0_N, 4)}`, unit: "N" },
    ];
  }
  if (mode === "optimize" && optimizeResult) {
    const o = optimizeResult;
    if (!o.found || !o.result || !o.optimal) {
      return [
        { label: "Résultat", value: "Aucune solution", tone: "destructive", caption: `${o.evaluations.length} roulements évalués` },
        { label: "C requise", value: fmt(o.C_required_N, 4), unit: "N" },
        { label: "C0 requise", value: fmt(o.C0_required_N, 4), unit: "N" },
        { label: "Cible L10h", value: fmtHours(o.target_hours), unit: "h" },
      ];
    }
    return [
      { label: "Roulement retenu", value: o.optimal.designation, tone: "success", caption: `C/C0 = ${fmt(o.optimal.C_N, 4)} / ${fmt(o.optimal.C0_N, 4)} N` },
      { label: "L10h obtenu", value: fmtHours(o.result.L10_hours), unit: "h", caption: `cible ${fmtHours(o.target_hours)} h` },
      { label: "S0 obtenu", value: fmt(o.result.S0, 3), caption: `cible ≥ ${fmt(o.S0_target, 3)}` },
      { label: "C / C0 requises", value: `${fmt(o.C_required_N, 4)} / ${fmt(o.C0_required_N, 4)}`, unit: "N" },
      { label: "P / P0", value: `${fmt(o.P_N, 4)} / ${fmt(o.P0_N, 4)}`, unit: "N" },
    ];
  }
  return [
    { label: "Dynamique", value: "—", caption: "En attente de calcul" },
    { label: "Statique S0", value: "—" },
    { label: "L10h", value: "—", unit: "h" },
    { label: "P / P0", value: "—", unit: "N" },
    { label: "C / C0", value: "—", unit: "N" },
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

export default function BearingsView() {
  const [mode, setMode] = useState<Mode>("verify");
  const [verifyReq, setVerifyReq] = useState<BearingRequest>(DEFAULT_BEARING);
  const [optReq, setOptReq] = useState<BearingOptimizeRequest>(DEFAULT_OPT);

  const [verifyResult, setVerifyResult] = useState<BearingResponse | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<BearingOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastComputed, setLastComputed] = useState<Date | null>(null);

  const handleVerify = async () => {
    setLoading(true); setError(null);
    try {
      const r = await calculateBearing(verifyReq);
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
      const r = await optimizeBearing(optReq);
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
      downloadJson(`mechora-bearing-verify-${ts}.json`, {
        module: "bearings", mode, request: verifyReq, response: verifyResult,
        exported_at: new Date().toISOString(),
      });
    } else if (mode === "optimize" && optimizeResult) {
      downloadJson(`mechora-bearing-optimize-${ts}.json`, {
        module: "bearings", mode, request: optReq, response: optimizeResult,
        exported_at: new Date().toISOString(),
      });
    }
  };

  const handleReset = () => {
    setVerifyReq(DEFAULT_BEARING); setOptReq(DEFAULT_OPT);
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
        module="bearings"
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
                  ? <BearingInput state={verifyReq} setState={setVerifyReq} />
                  : <BearingOptimizeInput state={optReq} setState={setOptReq} />}
                <Separator className="my-4" />
                <Button
                  className="w-full"
                  onClick={mode === "verify" ? handleVerify : handleOptimize}
                  disabled={loading}
                >
                  {loading
                    ? <><Loader2 className="h-4 w-4 animate-spin" />{mode === "verify" ? "Calcul…" : "Recherche…"}</>
                    : mode === "verify"
                      ? <><Calculator className="h-4 w-4" />Calculer L10 + S0</>
                      : <><Wand2 className="h-4 w-4" />Trouver le roulement optimal</>}
                </Button>
                {error && (
                  <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive font-mono whitespace-pre-wrap">
                    <span className="font-sans font-semibold">Erreur · </span>{error}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-5 min-w-0">
              {mode === "verify" && verifyResult && <BearingResultPanel result={verifyResult} />}
              {mode === "verify" && !verifyResult && !error && <EmptyState mode={mode} />}
              {mode === "optimize" && optimizeResult && <BearingOptimizeResults response={optimizeResult} />}
              {mode === "optimize" && !optimizeResult && !error && <EmptyState mode={mode} />}
            </div>
          </div>

          {mode === "verify" && verifyResult && (
            <AdviceCard advice={verifyResult.advice} verdict={verifyResult.verdict_dynamic}
              onOptimize={verifyResult.verdict_dynamic === "Surdimensionné" ? () => switchMode("optimize") : undefined} />
          )}
          {mode === "optimize" && optimizeResult && (
            <AdviceCard advice={optimizeResult.advice} verdict={optimizeResult.result?.verdict_dynamic} />
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
          ? "Configure le roulement (C, C0, Fr, Fa, n) puis lance le calcul pour estimer L10h et S0."
          : "Saisis les charges et la durée cible, puis lance la recherche dans le catalogue."}
      </CardContent>
    </Card>
  );
}
