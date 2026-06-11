import type { ShaftResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";

interface Props {
  result: ShaftResponse;
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

export default function ShaftResultPanel({ result }: Props) {
  const s = result.section;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Résultats Von Mises</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Verdict
          </span>
          <Badge variant={verdictVariant(result.verdict)}>
            {result.verdict} · Cs = {fmt(result.Cs, 3)}
          </Badge>
        </div>

        <Separator />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
          <Stat label="Contrainte équivalente σ_eq" value={fmt(result.sigma_eq_MPa, 4)} unit="MPa" />
          <Stat label="Contrainte de flexion σ_f"   value={fmt(result.sigma_f_MPa, 4)} unit="MPa" />
          <Stat label="Contrainte de torsion τ"     value={fmt(result.tau_MPa, 4)} unit="MPa" />
          <Stat label="Module flexion W_f"          value={fmt(s.W_f_mm3, 4)} unit="mm³" />
          <Stat label="Module torsion W_t"          value={fmt(s.W_t_mm3, 4)} unit="mm³" />
          <Stat label="Aire de section A"           value={fmt(s.area_mm2, 4)} unit="mm²" />
        </div>
      </CardContent>
    </Card>
  );
}
