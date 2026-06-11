import { CheckCircle2 } from "lucide-react";
import type { OptimizeResponse } from "../types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { cn } from "@/lib/utils";

interface Props {
  response: OptimizeResponse;
}

const fmt = (n: number, digits = 4) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

function statusBadge(status: string) {
  switch (status) {
    case "OK":
      return { label: "Tient", variant: "success" as const };
    case "Cs_insuffisant":
      return { label: "Cs insuffisant", variant: "destructive" as const };
    case "fleche_excessive":
      return { label: "Flèche excessive", variant: "warning" as const };
    default:
      return { label: status, variant: "outline" as const };
  }
}

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
      <div className="mt-1 text-lg font-medium tabular-nums leading-tight">
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

export default function OptimizeResults({ response }: Props) {
  const {
    found,
    optimal,
    result,
    evaluations,
    deflection_limit_mm,
    target_safety_factor,
  } = response;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Profilé optimal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {found && optimal && result ? (
            <>
              <div className="flex items-center gap-4 rounded-md border border-success/30 bg-success/5 px-4 py-3.5">
                <CheckCircle2 className="h-7 w-7 text-success shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[22px] font-semibold text-success tracking-tight tabular-nums">
                    {optimal.designation}{" "}
                    <span className="text-sm font-normal text-muted-foreground">
                      — famille {optimal.family}
                    </span>
                  </div>
                  <div className="text-[12.5px] text-muted-foreground tabular-nums">
                    <b className="text-foreground">{fmt(optimal.mass_kg_per_m, 3)} kg/m</b>{" "}
                    · h = {optimal.h_mm} mm · b = {optimal.b_mm} mm
                  </div>
                </div>
                <Badge variant="success">Validé</Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-px rounded-md border bg-border overflow-hidden">
                <Stat
                  label="Cs obtenu"
                  value={fmt(result.Cs, 3)}
                  extra={`≥ ${fmt(target_safety_factor, 3)} requis`}
                />
                <Stat
                  label="Flèche f"
                  value={fmt(result.f_max_mm, 4)}
                  unit="mm"
                  extra={`≤ ${fmt(deflection_limit_mm, 4)} mm admis`}
                />
                <Stat
                  label="Contrainte σ"
                  value={fmt(result.sigma_max_MPa, 4)}
                  unit="MPa"
                />
                <Stat label="Moment M" value={fmt(result.M_max_kNm, 4)} unit="kN·m" />
                <Stat label="Inertie Iy" value={fmt(optimal.inertia_mm4, 4)} unit="mm⁴" />
                <Stat
                  label="Module Wy"
                  value={fmt(optimal.section_modulus_mm3, 4)}
                  unit="mm³"
                />
              </div>
            </>
          ) : (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              Aucun profilé du catalogue ne satisfait Cs ≥{" "}
              {fmt(target_safety_factor, 3)} ET flèche ≤{" "}
              {fmt(deflection_limit_mm, 4)} mm.
              <br />
              Suggestion : relâcher la limite de flèche (ex. L/150), réduire le Cs cible,
              ou changer de matériau / catalogue.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-end justify-between">
            <CardTitle>Tableau des profilés évalués</CardTitle>
            <span className="text-[11px] text-muted-foreground">
              {evaluations.length} candidats · triés par masse croissante
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Profilé</TableHead>
                  <TableHead className="text-right">Masse</TableHead>
                  <TableHead className="text-right">Cs</TableHead>
                  <TableHead className="text-right">f_max</TableHead>
                  <TableHead className="text-right">σ_max</TableHead>
                  <TableHead>Statut</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evaluations.map((e) => {
                  const badge = statusBadge(e.status);
                  const key = `${e.family}-${e.designation}`;
                  const isOptimal =
                    optimal !== null &&
                    e.designation === optimal.designation &&
                    e.family === optimal.family;
                  return (
                    <TableRow
                      key={key}
                      className={cn(isOptimal && "bg-success/10")}
                      title={e.reason ?? ""}
                    >
                      <TableCell className="font-medium">
                        {e.designation}
                        <span className="ml-1.5 text-[10px] font-normal text-muted-foreground">
                          [{e.family}]
                        </span>
                        {isOptimal && (
                          <span className="ml-2 text-[10.5px] uppercase tracking-wider font-semibold text-success">
                            · optimal
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {fmt(e.mass_kg_per_m, 3)}{" "}
                        <span className="text-muted-foreground">kg/m</span>
                      </TableCell>
                      <TableCell className="text-right">{fmt(e.Cs, 3)}</TableCell>
                      <TableCell className="text-right">
                        {fmt(e.f_max_mm, 3)}{" "}
                        <span className="text-muted-foreground">mm</span>
                      </TableCell>
                      <TableCell className="text-right">
                        {fmt(e.sigma_max_MPa, 4)}{" "}
                        <span className="text-muted-foreground">MPa</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={badge.variant}>{badge.label}</Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
