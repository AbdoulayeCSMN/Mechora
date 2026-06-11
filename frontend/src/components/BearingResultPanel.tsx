import type { BearingResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";

interface Props {
  result: BearingResponse;
}

function dynamicVerdictVariant(v: string): "success" | "warning" | "destructive" | "info" {
  switch (v) {
    case "Insuffisant":    return "destructive";
    case "Limite":         return "warning";
    case "OK":             return "success";
    case "Surdimensionné": return "info";
    default:               return "info";
  }
}

function staticVerdictVariant(v: string): "success" | "warning" | "destructive" | "info" {
  if (v.startsWith("Insuffisant")) return "destructive";
  if (v.includes("limite")) return "warning";
  if (v.includes("chocs OK")) return "info";
  return "success";
}

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";
const fmtHours = (n: number) =>
  Number.isFinite(n)
    ? n >= 1e6 ? (n / 1e6).toFixed(1) + " M" : Math.round(n).toLocaleString("fr-FR")
    : "–";

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

export default function BearingResultPanel({ result }: Props) {
  const ratio = result.target_hours > 0 ? result.L10_hours / result.target_hours : 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vérification roulement (ISO 281 + ISO 76)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-md border border-border p-3 bg-background">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
                Verdict dynamique
              </span>
              <Badge variant={dynamicVerdictVariant(result.verdict_dynamic)}>
                {result.verdict_dynamic}
              </Badge>
            </div>
            <div className="text-[11px] text-muted-foreground tabular-nums">
              L10h / cible = {fmt(ratio, 3)}
            </div>
          </div>
          <div className="rounded-md border border-border p-3 bg-background">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
                Verdict statique
              </span>
              <Badge variant={staticVerdictVariant(result.verdict_static)}>
                {result.verdict_static}
              </Badge>
            </div>
            <div className="text-[11px] text-muted-foreground tabular-nums">
              S0 = {fmt(result.S0, 3)} = C0 / P0
            </div>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
          <Stat
            label="Durée L10h"
            value={fmtHours(result.L10_hours)}
            unit="h"
            extra={`L10 = ${fmt(result.L10_millions, 4)} × 10⁶ tours`}
          />
          <Stat
            label="Charge équivalente P"
            value={fmt(result.P_N, 4)}
            unit="N"
            extra={`X = ${fmt(result.X_used, 3)}, Y = ${fmt(result.Y_used, 3)}` +
              (result.e_used !== null ? `, e = ${fmt(result.e_used, 3)}` : "")}
          />
          <Stat label="Charge stat. P0" value={fmt(result.P0_N, 4)} unit="N" />
          <Stat label="C catalogue" value={fmt(result.C_N, 4)} unit="N" />
          <Stat label="C0 catalogue" value={fmt(result.C0_N, 4)} unit="N" />
          <Stat
            label="Régime"
            value={fmt(result.n_rpm, 4)}
            unit="tr/min"
            extra={`Type ${result.bearing_type === "ball_radial" ? "billes radial" : "rouleaux cyl."}`}
          />
        </div>
      </CardContent>
    </Card>
  );
}
