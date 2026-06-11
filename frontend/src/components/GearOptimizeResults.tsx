import { CheckCircle2 } from "lucide-react";
import type { GearOptimizeResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  response: GearOptimizeResponse;
}

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

const LIMITING_LABEL: Record<string, string> = {
  flexion_pignon: "flexion (pignon)",
  flexion_roue: "flexion (roue)",
  pression_superficielle: "pression de contact",
};

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

export default function GearOptimizeResults({ response }: Props) {
  const { found, m_optimal_mm, result, target_safety_factor, psi_m, evaluations } = response;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-end justify-between">
          <CardTitle>Module optimal</CardTitle>
          <span className="text-[11px] text-muted-foreground">
            {evaluations.length} modules essayés · ψ_m = b/m = {fmt(psi_m, 3)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {found && m_optimal_mm !== null && result ? (
          <>
            <div className="flex items-center gap-4 rounded-md border border-success/30 bg-success/5 px-4 py-3.5">
              <CheckCircle2 className="h-7 w-7 text-success shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[22px] font-semibold text-success tracking-tight tabular-nums">
                  m = {fmt(m_optimal_mm, 4)} mm
                </div>
                <div className="text-[12.5px] text-muted-foreground tabular-nums">
                  Largeur de denture <b className="text-foreground">b = {fmt(result.geometry.b_mm, 4)} mm</b> ·
                  d1 = {fmt(result.geometry.d1_mm, 4)} mm · d2 = {fmt(result.geometry.d2_mm, 4)} mm
                </div>
              </div>
              <Badge variant="success">Validé</Badge>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
              <Stat
                label="Cs obtenu"
                value={fmt(result.Cs, 3)}
                extra={`≥ ${fmt(target_safety_factor, 3)} requis (limitant : ${LIMITING_LABEL[result.limiting_criterion] ?? result.limiting_criterion})`}
              />
              <Stat label="Cs flexion pignon" value={fmt(result.Cs_F1, 3)} />
              <Stat label="Cs flexion roue" value={fmt(result.Cs_F2, 3)} />
              <Stat label="Cs pression contact" value={fmt(result.Cs_H, 3)} />
              <Stat label="Effort tangentiel Ft" value={fmt(result.Ft_N, 4)} unit="N" />
              <Stat label="Entraxe a" value={fmt(result.geometry.a_mm, 4)} unit="mm" />
            </div>
          </>
        ) : (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Aucun module de la série normalisée ne satisfait Cs ≥ {fmt(target_safety_factor, 3)}.
            <br />
            Suggestion : augmenter z1/z2, choisir des matériaux plus résistants, ou augmenter ψ_m.
          </div>
        )}

        {evaluations.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-[12.5px] tabular-nums">
              <thead>
                <tr className="border-b bg-muted/40 text-[10.5px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2 text-left font-semibold">Module m (mm)</th>
                  <th className="px-3 py-2 text-left font-semibold">Largeur b (mm)</th>
                  <th className="px-3 py-2 text-left font-semibold">Cs</th>
                  <th className="px-3 py-2 text-left font-semibold">Statut</th>
                  <th className="px-3 py-2 text-left font-semibold">Critère limitant</th>
                </tr>
              </thead>
              <tbody>
                {evaluations.map((e, i) => (
                  <tr key={i} className="border-b last:border-b-0">
                    <td className="px-3 py-1.5">{fmt(e.m_mm, 3)}</td>
                    <td className="px-3 py-1.5">{fmt(e.b_mm, 4)}</td>
                    <td className="px-3 py-1.5">{fmt(e.Cs, 3)}</td>
                    <td className="px-3 py-1.5">
                      <Badge variant={e.status === "OK" ? "success" : "destructive"}>{e.status}</Badge>
                    </td>
                    <td className="px-3 py-1.5">{LIMITING_LABEL[e.limiting_criterion] ?? e.limiting_criterion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
