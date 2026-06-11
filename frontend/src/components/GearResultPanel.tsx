import type { GearResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";

interface Props {
  result: GearResponse;
}

function verdictVariant(v: string): "success" | "warning" | "destructive" | "info" {
  switch (v) {
    case "Sous-dimensionné": return "destructive";
    case "Limite":           return "warning";
    case "OK":               return "success";
    case "Surdimensionné":   return "info";
    default:                 return "info";
  }
}

const LIMITING_LABEL: Record<string, string> = {
  flexion_pignon: "flexion (pignon)",
  flexion_roue: "flexion (roue)",
  pression_superficielle: "pression de contact",
};

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
      <div className="mt-1 text-lg font-medium text-foreground tabular-nums leading-tight">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>}
      </div>
      {extra && (
        <div className="text-[11px] text-muted-foreground tabular-nums mt-0.5">{extra}</div>
      )}
    </div>
  );
}

export default function GearResultPanel({ result }: Props) {
  const g = result.geometry;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vérification engrenage droit</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Verdict · Critère limitant :{" "}
            <b className="text-foreground">
              {LIMITING_LABEL[result.limiting_criterion] ?? result.limiting_criterion}
            </b>
          </span>
          <Badge variant={verdictVariant(result.verdict)}>
            {result.verdict} · Cs = {fmt(result.Cs, 3)}
          </Badge>
        </div>

        <Separator />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px rounded-md border bg-border overflow-hidden">
          <Stat label="Module m" value={fmt(g.m_mm, 3)} unit="mm" />
          <Stat label="Diamètres primitifs" value={`${fmt(g.d1_mm, 4)} / ${fmt(g.d2_mm, 4)}`} unit="mm" extra="d1 (pignon) / d2 (roue)" />
          <Stat label="Entraxe a" value={fmt(g.a_mm, 4)} unit="mm" />
          <Stat label="Rapport u = z2/z1" value={fmt(g.u, 3)} extra={`z1=${g.z1}, z2=${g.z2}`} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
          <Stat
            label="Flexion pignon σ_F1"
            value={fmt(result.sigma_F1_MPa, 4)}
            unit="MPa"
            extra={`adm ${fmt(result.sigma_F1_adm_MPa, 4)} MPa · Cs = ${fmt(result.Cs_F1, 3)}`}
          />
          <Stat
            label="Flexion roue σ_F2"
            value={fmt(result.sigma_F2_MPa, 4)}
            unit="MPa"
            extra={`adm ${fmt(result.sigma_F2_adm_MPa, 4)} MPa · Cs = ${fmt(result.Cs_F2, 3)}`}
          />
          <Stat
            label="Pression de contact σ_H"
            value={fmt(result.sigma_H_MPa, 4)}
            unit="MPa"
            extra={`adm ${fmt(result.sigma_H_adm_MPa, 4)} MPa · Cs = ${fmt(result.Cs_H, 3)}`}
          />
          <Stat label="Effort tangentiel Ft" value={fmt(result.Ft_N, 4)} unit="N" />
          <Stat label="Effort radial Fr" value={fmt(result.Fr_N, 4)} unit="N" />
          <Stat label="Vitesse tangentielle v" value={fmt(result.v_m_s, 3)} unit="m/s" extra={`K_V = ${fmt(result.K_V, 3)} · K_A = ${fmt(result.K_A, 3)}`} />
        </div>
      </CardContent>
    </Card>
  );
}
