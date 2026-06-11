import { CheckCircle2 } from "lucide-react";
import type { BearingOptimizeResponse } from "../types";
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
  response: BearingOptimizeResponse;
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

export default function BearingOptimizeResults({ response }: Props) {
  const {
    found, C_required_N, C0_required_N, optimal, result,
    target_hours, S0_target, evaluations,
  } = response;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Roulement optimal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {found && optimal && result ? (
            <>
              <div className="flex items-center gap-4 rounded-md border border-success/30 bg-success/5 px-4 py-3.5">
                <CheckCircle2 className="h-7 w-7 text-success shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[22px] font-semibold text-success tracking-tight tabular-nums">
                    {optimal.designation}
                  </div>
                  <div className="text-[12.5px] text-muted-foreground tabular-nums">
                    <b className="text-foreground">C = {fmt(optimal.C_N, 4)} N</b>
                    {" / "}
                    <b className="text-foreground">C0 = {fmt(optimal.C0_N, 4)} N</b>
                    {optimal.d_bore_mm !== null && ` · alésage ${optimal.d_bore_mm} mm`}
                    {" · "}
                    {optimal.type === "ball_radial" ? "billes radial" : "rouleaux cyl."}
                  </div>
                </div>
                <Badge variant="success">L10 et S0 OK</Badge>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px rounded-md border bg-border overflow-hidden">
                <Stat
                  label="L10h obtenu"
                  value={fmtHours(result.L10_hours)}
                  unit="h"
                  extra={`cible ${fmtHours(target_hours)} h`}
                />
                <Stat
                  label="C requise vs retenue"
                  value={fmt(C_required_N, 4)}
                  unit="N"
                  extra={`retenu ${fmt(optimal.C_N, 4)} N`}
                />
                <Stat
                  label="S0 obtenu"
                  value={fmt(result.S0, 3)}
                  extra={`cible ≥ ${fmt(S0_target, 3)}`}
                />
                <Stat
                  label="C0 requise vs retenue"
                  value={fmt(C0_required_N, 4)}
                  unit="N"
                  extra={`retenu ${fmt(optimal.C0_N, 4)} N`}
                />
                <Stat
                  label="P / P0"
                  value={`${fmt(result.P_N, 4)} / ${fmt(result.P0_N, 4)}`}
                  unit="N"
                />
                <Stat
                  label="Charges (Fr / Fa)"
                  value={`${fmt(result.Fr_N, 4)} / ${fmt(result.Fa_N, 4)}`}
                  unit="N"
                />
              </div>
            </>
          ) : (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              Aucun roulement du catalogue n'atteint <b>L10h ≥ {fmtHours(target_hours)} h</b>{" "}
              ET <b>S0 ≥ {fmt(S0_target, 3)}</b>.
              <br />
              C requise ≈ <b>{fmt(C_required_N, 4)} N</b>, C0 requise ≈{" "}
              <b>{fmt(C0_required_N, 4)} N</b>.
              <br />
              Suggestion : passer aux rouleaux, réduire la vitesse ou répartir la charge.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-end justify-between">
            <CardTitle>Catalogue évalué</CardTitle>
            <span className="text-[11px] text-muted-foreground">
              {evaluations.length} roulements · triés par C croissant
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Désignation</TableHead>
                  <TableHead className="text-right">C / C0</TableHead>
                  <TableHead className="text-right">Alésage</TableHead>
                  <TableHead className="text-right">L10h</TableHead>
                  <TableHead className="text-right">S0</TableHead>
                  <TableHead>Statut</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evaluations.map((e) => {
                  const isOptimal = optimal !== null && e.designation === optimal.designation;
                  const bothOk = e.status_dyn === "OK" && e.status_stat === "OK";
                  return (
                    <TableRow
                      key={e.designation}
                      className={cn(isOptimal && "bg-success/10")}
                    >
                      <TableCell className="font-medium">
                        {e.designation}
                        {isOptimal && (
                          <span className="ml-2 text-[10.5px] uppercase tracking-wider font-semibold text-success">
                            · optimal
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {fmt(e.C_N, 4)} / {fmt(e.C0_N, 4)}{" "}
                        <span className="text-muted-foreground">N</span>
                      </TableCell>
                      <TableCell className="text-right">
                        {e.d_bore_mm !== null
                          ? <>{e.d_bore_mm} <span className="text-muted-foreground">mm</span></>
                          : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="text-right">
                        {fmtHours(e.L10_hours)} <span className="text-muted-foreground">h</span>
                      </TableCell>
                      <TableCell className="text-right">{fmt(e.S0, 3)}</TableCell>
                      <TableCell>
                        {bothOk ? (
                          <Badge variant="success">Tient</Badge>
                        ) : (
                          <div className="flex flex-col gap-0.5 text-[10px]">
                            <Badge variant={e.status_dyn === "OK" ? "success" : "destructive"}>
                              Dyn : {e.status_dyn === "OK" ? "OK" : "Insuf."}
                            </Badge>
                            <Badge variant={e.status_stat === "OK" ? "success" : "destructive"}>
                              Stat : {e.status_stat === "OK" ? "OK" : "Insuf."}
                            </Badge>
                          </div>
                        )}
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
