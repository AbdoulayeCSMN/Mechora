import type { BeamResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";

interface Props {
  result: BeamResponse;
}

function verdictVariant(v: string): "success" | "warning" | "destructive" | "info" {
  switch (v) {
    case "Sous-dimensionné":
      return "destructive";
    case "Limite":
      return "warning";
    case "OK":
      return "success";
    case "Surdimensionné":
      return "info";
    default:
      return "info";
  }
}

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

function Stat({
  label,
  value,
  unit,
  extra,
}: {
  label: string;
  value: string;
  unit?: string;
  extra?: string;
}) {
  return (
    <div className="px-4 py-3 bg-background">
      <div className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-medium text-foreground tabular-nums leading-tight">
        {value}
        {unit && (
          <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>
        )}
      </div>
      {extra && (
        <div className="text-[11px] text-muted-foreground tabular-nums mt-0.5">
          {extra}
        </div>
      )}
    </div>
  );
}

export default function ResultPanel({ result }: Props) {
  const sp = result.section_properties;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Résultats du calcul</CardTitle>
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px rounded-md border bg-border overflow-hidden">
          <Stat label="Contrainte max σ" value={fmt(result.sigma_max_MPa, 4)} unit="MPa" />
          <Stat label="Flèche max f" value={fmt(result.f_max_mm, 4)} unit="mm" />
          <Stat label="Moment max M" value={fmt(result.M_max_kNm, 4)} unit="kN·m" />
          <Stat label="Inertie I" value={fmt(sp.inertia_mm4, 4)} unit="mm⁴" />
          <Stat
            label="Module W = I/v"
            value={fmt(sp.section_modulus_mm3, 4)}
            unit="mm³"
          />
          <Stat label="Aire A" value={fmt(sp.area_mm2, 4)} unit="mm²" />
          {Object.entries(result.reactions_kN).map(([k, v]) => (
            <Stat
              key={k}
              label={`Réaction ${k}`}
              value={fmt(v, 4)}
              unit={k === "M_r" ? "kN·m" : "kN"}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
