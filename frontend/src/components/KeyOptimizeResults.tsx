import { CheckCircle2 } from "lucide-react";
import type { KeyOptimizeResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  response: KeyOptimizeResponse;
}

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

function Stat({
  label, value, unit, extra,
}: { label: string; value: string; unit?: string; extra?: string }) {
  return (
    <div className="px-4 py-3 bg-background">
      <div className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-medium tabular-nums leading-tight">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>}
      </div>
      {extra && (
        <div className="text-[11px] text-muted-foreground tabular-nums mt-0.5">{extra}</div>
      )}
    </div>
  );
}

export default function KeyOptimizeResults({ response }: Props) {
  const { found, l_total_optimal_mm, result, target_safety_factor,
          l_min_mm, l_max_mm, step_mm, candidates_evaluated } = response;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-end justify-between">
          <CardTitle>Longueur optimale</CardTitle>
          <span className="text-[11px] text-muted-foreground">
            {candidates_evaluated} longueurs essayées · plage {fmt(l_min_mm, 3)}–{fmt(l_max_mm, 3)} mm · pas {step_mm} mm
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {found && l_total_optimal_mm !== null && result ? (
          <>
            <div className="flex items-center gap-4 rounded-md border border-success/30 bg-success/5 px-4 py-3.5">
              <CheckCircle2 className="h-7 w-7 text-success shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[22px] font-semibold text-success tracking-tight tabular-nums">
                  l_total = {fmt(l_total_optimal_mm, 4)} mm
                </div>
                <div className="text-[12.5px] text-muted-foreground tabular-nums">
                  Section ISO 773 : <b className="text-foreground">b = {result.section.b_mm} mm</b>,
                  h = {result.section.h_mm} mm · l_active = {fmt(result.section.l_active_mm, 4)} mm
                </div>
              </div>
              <Badge variant="success">Validé</Badge>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
              <Stat
                label="Cs obtenu"
                value={fmt(result.Cs, 3)}
                extra={`≥ ${fmt(target_safety_factor, 3)} requis (limitant : ${result.limiting_criterion})`}
              />
              <Stat label="τ cisaillement" value={fmt(result.tau_MPa, 4)} unit="MPa" />
              <Stat label="σ_m matage" value={fmt(result.sigma_m_MPa, 4)} unit="MPa" />
              <Stat label="Cs cisaillement" value={fmt(result.Cs_shear, 3)} />
              <Stat label="Cs matage" value={fmt(result.Cs_bearing, 3)} />
              <Stat label="Couple Mt" value={fmt(result.Mt_Nm, 4)} unit="N·m" />
            </div>
          </>
        ) : (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Aucune longueur entre {fmt(l_min_mm, 3)} et {fmt(l_max_mm, 3)} mm ne satisfait Cs ≥ {fmt(target_safety_factor, 3)}.
            <br />
            Suggestion : augmenter l_max, passer à un moyeu plus dur, ou choisir un assemblage cannelé.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
