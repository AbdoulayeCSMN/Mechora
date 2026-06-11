import type { LoadInput, SupportType } from "../types";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  length_m: number;
  support: SupportType;
  loads: LoadInput[];
}

const W = 880;
const H = 240;
const BEAM_Y = 138;
const BEAM_X0 = 90;
const BEAM_X1 = 790;
const BEAM_LEN_PX = BEAM_X1 - BEAM_X0;

const C_BEAM = "#0f172a";     // slate-900
const C_SUPPORT = "#475569";  // slate-600
const C_DIM = "#94a3b8";      // slate-400
// Use primary CSS variable so colors stay in sync with the theme
const C_POINT = "hsl(var(--primary))";
const C_DIST = "hsl(var(--info))";

function xPx(pos_m: number, length_m: number) {
  if (length_m <= 0) return BEAM_X0;
  return BEAM_X0 + (Math.max(0, Math.min(pos_m, length_m)) / length_m) * BEAM_LEN_PX;
}

function SupportTriangle({ cx }: { cx: number }) {
  return (
    <g stroke={C_SUPPORT} strokeWidth={1.3}>
      <polygon
        points={`${cx - 13},${BEAM_Y + 22} ${cx + 13},${BEAM_Y + 22} ${cx},${BEAM_Y + 2}`}
        fill="#e2e8f0"
      />
      <line x1={cx - 18} y1={BEAM_Y + 22} x2={cx + 18} y2={BEAM_Y + 22} />
      {[-14, -7, 0, 7, 14].map((dx) => (
        <line key={dx} x1={cx + dx} y1={BEAM_Y + 22} x2={cx + dx - 4} y2={BEAM_Y + 28} />
      ))}
    </g>
  );
}

function FixedWall({ x }: { x: number }) {
  const top = BEAM_Y - 30;
  const bot = BEAM_Y + 30;
  return (
    <g stroke={C_SUPPORT} strokeWidth={1.3}>
      <line x1={x} y1={top} x2={x} y2={bot} strokeWidth={2.5} />
      {Array.from({ length: 10 }).map((_, i) => {
        const y = top + ((bot - top) / 9) * i;
        return <line key={i} x1={x} y1={y} x2={x - 11} y2={y + 7} />;
      })}
    </g>
  );
}

function PointArrow({ cx, label }: { cx: number; label: string }) {
  const tip = BEAM_Y - 3;
  const tail = BEAM_Y - 60;
  return (
    <g stroke={C_POINT} fill={C_POINT} strokeWidth={1.6}>
      <line x1={cx} y1={tail} x2={cx} y2={tip} />
      <polygon points={`${cx - 5},${tip - 9} ${cx + 5},${tip - 9} ${cx},${tip}`} />
      <text
        x={cx}
        y={tail - 5}
        textAnchor="middle"
        fontSize={11.5}
        fontWeight={600}
        stroke="none"
        fill={C_POINT}
      >
        {label}
      </text>
    </g>
  );
}

function DistributedArrows({ x1, x2, label }: { x1: number; x2: number; label: string }) {
  const tip = BEAM_Y - 3;
  const top = BEAM_Y - 46;
  const width = x2 - x1;
  const n = Math.max(2, Math.min(14, Math.round(width / 30)));
  return (
    <g stroke={C_DIST} fill={C_DIST} strokeWidth={1.3}>
      <line x1={x1} y1={top} x2={x2} y2={top} strokeWidth={2} />
      {Array.from({ length: n + 1 }).map((_, i) => {
        const xa = x1 + (width * i) / n;
        return (
          <g key={i}>
            <line x1={xa} y1={top} x2={xa} y2={tip} />
            <polygon points={`${xa - 4},${tip - 8} ${xa + 4},${tip - 8} ${xa},${tip}`} />
          </g>
        );
      })}
      <text
        x={(x1 + x2) / 2}
        y={top - 6}
        textAnchor="middle"
        fontSize={11.5}
        fontWeight={600}
        stroke="none"
        fill={C_DIST}
      >
        {label}
      </text>
    </g>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span
        className="h-3 w-3 rounded-sm border border-black/10"
        style={{ background: color }}
      />
      {label}
    </span>
  );
}

export default function BeamDiagram({ length_m, support, loads }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Schéma de la poutre</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          className="w-full h-auto block rounded-md bg-muted/30 py-1.5"
        >
          <rect
            x={BEAM_X0}
            y={BEAM_Y - 7}
            width={BEAM_LEN_PX}
            height={14}
            fill={C_BEAM}
            rx={1}
          />
          {support === "simply_supported" && (
            <>
              <SupportTriangle cx={BEAM_X0} />
              <SupportTriangle cx={BEAM_X1} />
            </>
          )}
          {support === "cantilever" && <FixedWall x={BEAM_X0} />}

          <g fontSize={11.5} fill={C_DIM} stroke={C_DIM}>
            <line x1={BEAM_X0} y1={BEAM_Y + 64} x2={BEAM_X1} y2={BEAM_Y + 64} strokeWidth={1} />
            <line x1={BEAM_X0} y1={BEAM_Y + 60} x2={BEAM_X0} y2={BEAM_Y + 68} />
            <line x1={BEAM_X1} y1={BEAM_Y + 60} x2={BEAM_X1} y2={BEAM_Y + 68} />
            <text
              x={(BEAM_X0 + BEAM_X1) / 2}
              y={BEAM_Y + 82}
              textAnchor="middle"
              stroke="none"
              fontWeight={500}
            >
              L = {length_m} m
            </text>
          </g>

          {loads.map((ld, i) => {
            if (ld.type === "point") {
              return (
                <PointArrow
                  key={i}
                  cx={xPx(ld.position_m, length_m)}
                  label={`${ld.magnitude_kN} kN`}
                />
              );
            }
            return (
              <DistributedArrows
                key={i}
                x1={xPx(ld.start_m, length_m)}
                x2={xPx(ld.end_m, length_m)}
                label={`${ld.magnitude_kN_per_m} kN/m`}
              />
            );
          })}
        </svg>

        <div className="mt-4 flex flex-wrap gap-4">
          <LegendSwatch color={C_BEAM} label="Poutre" />
          <LegendSwatch
            color="#e2e8f0"
            label={
              support === "simply_supported" ? "Appuis simples" : "Encastrement"
            }
          />
          <LegendSwatch color={C_POINT} label="Charge ponctuelle" />
          <LegendSwatch color={C_DIST} label="Charge répartie" />
        </div>
      </CardContent>
    </Card>
  );
}
