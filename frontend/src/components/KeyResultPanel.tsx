import type { KeyResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";

interface Props {
  result: KeyResponse;
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

export default function KeyResultPanel({ result }: Props) {
  const s = result.section;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vérification clavette</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Verdict · Critère limitant : <b className="text-foreground">{result.limiting_criterion}</b>
          </span>
          <Badge variant={verdictVariant(result.verdict)}>
            {result.verdict} · Cs = {fmt(result.Cs, 3)}
          </Badge>
        </div>

        <Separator />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
          <Stat
            label="Cisaillement τ"
            value={fmt(result.tau_MPa, 4)}
            unit="MPa"
            extra={`adm ${fmt(result.Re_shear_MPa, 4)} MPa · Cs = ${fmt(result.Cs_shear, 3)}`}
          />
          <Stat
            label="Matage σ_m"
            value={fmt(result.sigma_m_MPa, 4)}
            unit="MPa"
            extra={`adm ${fmt(result.sigma_m_adm_MPa, 4)} MPa · Cs = ${fmt(result.Cs_bearing, 3)}`}
          />
          <Stat label="Section b × h" value={`${fmt(s.b_mm, 3)} × ${fmt(s.h_mm, 3)}`} unit="mm" />
          <Stat label="Longueur totale" value={fmt(s.l_total_mm, 4)} unit="mm" />
          <Stat
            label="Longueur active"
            value={fmt(s.l_active_mm, 4)}
            unit="mm"
            extra="= l_total − b"
          />
          <Stat label="Couple appliqué Mt" value={fmt(result.Mt_Nm, 4)} unit="N·m" />
        </div>
      </CardContent>
    </Card>
  );
}
