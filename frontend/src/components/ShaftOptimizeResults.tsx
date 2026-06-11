import { CheckCircle2 } from "lucide-react";
import type { ShaftOptimizeResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  response: ShaftOptimizeResponse;
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

export default function ShaftOptimizeResults({ response }: Props) {
  const { found, d_optimal_mm, result, target_safety_factor,
          d_min_mm, d_max_mm, step_mm, candidates_evaluated } = response;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-end justify-between">
          <CardTitle>Diamètre optimal</CardTitle>
          <span className="text-[11px] text-muted-foreground">
            {candidates_evaluated} diamètres essayés · plage {d_min_mm}–{d_max_mm} mm · pas {step_mm} mm
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {found && d_optimal_mm !== null && result ? (
          <>
            <div className="flex items-center gap-4 rounded-md border border-success/30 bg-success/5 px-4 py-3.5">
              <CheckCircle2 className="h-7 w-7 text-success shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[22px] font-semibold text-success tracking-tight tabular-nums">
                  d = {fmt(d_optimal_mm, 4)} mm
                </div>
                <div className="text-[12.5px] text-muted-foreground tabular-nums">
                  Arbre {result.section.type === "hollow" ? "creux" : "plein"}
                  {result.section.type === "hollow" &&
                    ` · d_int = ${fmt(result.section.d_int_mm, 4)} mm`}
                  · A = <b className="text-foreground">{fmt(result.section.area_mm2, 4)} mm²</b>
                </div>
              </div>
              <Badge variant="success">Validé</Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
              <Stat
                label="Cs obtenu"
                value={fmt(result.Cs, 3)}
                extra={`≥ ${fmt(target_safety_factor, 3)} requis`}
              />
              <Stat
                label="σ_eq (Von Mises)"
                value={fmt(result.sigma_eq_MPa, 4)}
                unit="MPa"
              />
              <Stat label="σ_f (flexion)" value={fmt(result.sigma_f_MPa, 4)} unit="MPa" />
              <Stat label="τ (torsion)"   value={fmt(result.tau_MPa, 4)} unit="MPa" />
              <Stat label="W_f"           value={fmt(result.section.W_f_mm3, 4)} unit="mm³" />
              <Stat label="W_t"           value={fmt(result.section.W_t_mm3, 4)} unit="mm³" />
            </div>
          </>
        ) : (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Aucun diamètre dans la plage {d_min_mm}–{d_max_mm} mm ne satisfait Cs ≥{" "}
            {fmt(target_safety_factor, 3)}.
            <br />
            Suggestion : augmenter d_max, réduire le Cs cible, ou passer à un acier
            à limite élastique plus élevée.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
