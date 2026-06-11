import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BeamResponse, SupportType } from "../types";
import { E_BY_MATERIAL } from "../types";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface Props {
  result: BeamResponse;
  material: string;
  support: SupportType;
}

function deflectionCurve(
  x: number[],
  M_kNm: number[],
  E_Pa: number,
  I_mm4: number,
  support: SupportType,
): number[] {
  const n = x.length;
  if (n === 0) return [];
  const EI = E_Pa * (I_mm4 * 1e-12);
  const rhs = M_kNm.map((m) => -(m * 1000) / EI);
  const slope = new Array<number>(n).fill(0);
  for (let i = 1; i < n; i++) {
    slope[i] = slope[i - 1] + 0.5 * (rhs[i] + rhs[i - 1]) * (x[i] - x[i - 1]);
  }
  const f = new Array<number>(n).fill(0);
  for (let i = 1; i < n; i++) {
    f[i] = f[i - 1] + 0.5 * (slope[i] + slope[i - 1]) * (x[i] - x[i - 1]);
  }
  if (support === "simply_supported") {
    const c = -f[n - 1] / (x[n - 1] - x[0]);
    for (let i = 0; i < n; i++) f[i] += c * (x[i] - x[0]);
  }
  return f.map((v) => v * 1000);
}

const fmt = (n: number, digits = 3) =>
  Number.isFinite(n) ? n.toPrecision(digits) : "–";

function Chart({
  title,
  subtitle,
  yLabel,
  data,
  dataKey,
  color,
}: {
  title: string;
  subtitle: string;
  yLabel: string;
  data: any[];
  dataKey: string;
  color: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle>{title}</CardTitle>
          <span className="text-[10.5px] uppercase tracking-wider text-muted-foreground font-medium">
            {subtitle}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[230px]">
          <ResponsiveContainer>
            <LineChart
              data={data}
              margin={{ top: 8, right: 18, bottom: 28, left: 12 }}
            >
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="2 3" />
              <XAxis
                dataKey="x"
                type="number"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(v) => v.toFixed(2)}
                label={{
                  value: "x  (m)",
                  position: "insideBottom",
                  offset: -12,
                  fill: "hsl(var(--muted-foreground))",
                  fontSize: 11,
                  fontWeight: 500,
                }}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                stroke="hsl(var(--border))"
              />
              <YAxis
                tickFormatter={(v) => fmt(v, 3)}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                stroke="hsl(var(--border))"
                width={68}
                label={{
                  value: yLabel,
                  angle: -90,
                  position: "insideLeft",
                  fill: "hsl(var(--muted-foreground))",
                  fontSize: 11,
                  fontWeight: 500,
                  offset: 12,
                }}
              />
              <Tooltip
                formatter={(v: number) => [fmt(v, 4), yLabel]}
                labelFormatter={(l) => `x = ${(+l).toFixed(3)} m`}
                contentStyle={{
                  fontSize: 12,
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 6,
                  backgroundColor: "hsl(var(--popover))",
                  color: "hsl(var(--popover-foreground))",
                  boxShadow: "0 2px 6px rgba(15,23,42,.08)",
                  padding: "8px 10px",
                }}
                labelStyle={{ color: "hsl(var(--muted-foreground))", marginBottom: 4 }}
              />
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeWidth={1} />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Charts({ result, material, support }: Props) {
  const E = E_BY_MATERIAL[material] ?? 210e9;
  const f = deflectionCurve(
    result.x_m,
    result.M_kNm,
    E,
    result.section_properties.inertia_mm4,
    support,
  );
  const data = result.x_m.map((xi, i) => ({
    x: xi,
    V: result.V_kN[i],
    M: result.M_kNm[i],
    f: f[i],
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-5">
      <Chart
        title="Effort tranchant"
        subtitle="V(x) · kN"
        yLabel="V (kN)"
        data={data}
        dataKey="V"
        color="hsl(var(--primary))"
      />
      <Chart
        title="Moment fléchissant"
        subtitle="M(x) · kN·m"
        yLabel="M (kN·m)"
        data={data}
        dataKey="M"
        color="hsl(var(--info))"
      />
      <Chart
        title="Flèche (déformée)"
        subtitle="f(x) · mm (vers le bas)"
        yLabel="f (mm)"
        data={data}
        dataKey="f"
        color="hsl(var(--success))"
      />
    </div>
  );
}
