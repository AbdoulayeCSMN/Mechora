import type { ShaftType } from "../types";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  type: ShaftType;
  d_ext_mm: number;
  d_int_mm: number;
  Mf_Nm?: number;
  Mt_Nm?: number;
}

const W = 880;
const H = 280;
const CX = 280;
const CY = 140;
const MAX_R = 100;

const C_SHAFT = "#1f2937";        // slate-800
const C_INNER = "#f4f5f7";        // page background
const C_DIM = "#94a3b8";          // slate-400
const C_MF = "hsl(var(--primary))";
const C_MT = "hsl(var(--info))";

export default function ShaftDiagram({
  type, d_ext_mm, d_int_mm, Mf_Nm, Mt_Nm,
}: Props) {
  const r_ext = MAX_R;
  const innerRatio = d_ext_mm > 0 ? d_int_mm / d_ext_mm : 0;
  const r_inner_actual = innerRatio * r_ext;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Section de l'arbre</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          className="w-full h-auto block rounded-md bg-muted/30 py-2"
        >
          {/* Reference axes */}
          <g stroke={C_DIM} strokeWidth={0.75} strokeDasharray="3 3">
            <line x1={CX - r_ext - 30} y1={CY} x2={CX + r_ext + 30} y2={CY} />
            <line x1={CX} y1={CY - r_ext - 30} x2={CX} y2={CY + r_ext + 30} />
          </g>

          {/* Outer circle (shaft body) */}
          <circle
            cx={CX}
            cy={CY}
            r={r_ext}
            fill={C_SHAFT}
            opacity={0.92}
          />

          {/* Inner hole if hollow */}
          {type === "hollow" && r_inner_actual > 0 && (
            <circle
              cx={CX}
              cy={CY}
              r={r_inner_actual}
              fill={C_INNER}
              stroke={C_DIM}
              strokeWidth={0.5}
              strokeDasharray="2 2"
            />
          )}

          {/* Dimension annotations: d_ext */}
          <g fontSize={11.5} fill={C_DIM} stroke={C_DIM}>
            <line x1={CX - r_ext} y1={CY + r_ext + 22} x2={CX + r_ext} y2={CY + r_ext + 22} strokeWidth={1} />
            <line x1={CX - r_ext} y1={CY + r_ext + 18} x2={CX - r_ext} y2={CY + r_ext + 26} />
            <line x1={CX + r_ext} y1={CY + r_ext + 18} x2={CX + r_ext} y2={CY + r_ext + 26} />
            <text
              x={CX}
              y={CY + r_ext + 40}
              textAnchor="middle"
              stroke="none"
              fontWeight={500}
            >
              d_ext = {d_ext_mm} mm
            </text>
          </g>

          {type === "hollow" && (
            <g fontSize={11} fill={C_DIM} stroke={C_DIM}>
              <text
                x={CX}
                y={CY - r_ext - 16}
                textAnchor="middle"
                stroke="none"
              >
                d_int = {d_int_mm} mm
              </text>
            </g>
          )}

          {/* Mf — bending arrow on the right side */}
          <g transform={`translate(${CX + r_ext + 110},${CY})`}>
            <text x={0} y={-78} textAnchor="middle" fontSize={12.5} fontWeight={600} fill={C_MF}>
              Mf
            </text>
            {Mf_Nm !== undefined && (
              <text x={0} y={-60} textAnchor="middle" fontSize={11} fill={C_MF}>
                {Mf_Nm} N·m
              </text>
            )}
            <path
              d="M -22,-40 A 28 28 0 1 1 22,-40"
              fill="none"
              stroke={C_MF}
              strokeWidth={2}
            />
            <polygon points="22,-40 14,-46 14,-32" fill={C_MF} />
            <text x={0} y={28} textAnchor="middle" fontSize={10} fill={C_DIM}>
              flexion
            </text>
          </g>

          {/* Mt — torsion arrow around the shaft (curved) on the left side */}
          <g transform={`translate(${CX - r_ext - 110},${CY})`}>
            <text x={0} y={-78} textAnchor="middle" fontSize={12.5} fontWeight={600} fill={C_MT}>
              Mt
            </text>
            {Mt_Nm !== undefined && (
              <text x={0} y={-60} textAnchor="middle" fontSize={11} fill={C_MT}>
                {Mt_Nm} N·m
              </text>
            )}
            <path
              d="M -28,0 A 28 28 0 1 1 0,28"
              fill="none"
              stroke={C_MT}
              strokeWidth={2}
            />
            <polygon points="0,28 -8,22 6,18" fill={C_MT} />
            <text x={0} y={48} textAnchor="middle" fontSize={10} fill={C_DIM}>
              torsion
            </text>
          </g>
        </svg>

        <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm" style={{ background: C_SHAFT }} />
            Section pleine
          </span>
          {type === "hollow" && (
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm border border-muted-foreground/40 bg-background" />
              Cavité interne
            </span>
          )}
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm" style={{ background: C_MF }} />
            Moment fléchissant Mf
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm" style={{ background: C_MT }} />
            Moment de torsion Mt
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
