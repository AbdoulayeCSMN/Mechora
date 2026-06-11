import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export type KPITone = "neutral" | "success" | "warning" | "destructive" | "info";

export interface KPI {
  label: string;
  value: string;
  unit?: string;
  caption?: string;
  tone?: KPITone;
  trend?: "up" | "down" | "flat";
}

const TONE: Record<KPITone, { ring: string; text: string; bg: string }> = {
  neutral:     { ring: "ring-border",         text: "text-foreground",    bg: "" },
  success:     { ring: "ring-success/30",     text: "text-success",       bg: "bg-success/5" },
  warning:     { ring: "ring-warning/30",     text: "text-warning",       bg: "bg-warning/5" },
  destructive: { ring: "ring-destructive/30", text: "text-destructive",   bg: "bg-destructive/5" },
  info:        { ring: "ring-info/30",        text: "text-info",          bg: "bg-info/5" },
};

export default function KPIRow({ items }: { items: KPI[] }) {
  const cols =
    items.length >= 5
      ? "lg:grid-cols-5"
      : items.length === 4
      ? "lg:grid-cols-4"
      : "lg:grid-cols-3";
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-3 gap-3", cols)}>
      {items.map((kpi, i) => {
        const tone = TONE[kpi.tone ?? "neutral"];
        return (
          <div
            key={i}
            className={cn(
              "rounded-lg border bg-card shadow-sm p-4 ring-1 ring-inset",
              tone.ring,
              tone.bg,
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                {kpi.label}
              </span>
              {kpi.trend && <TrendIcon trend={kpi.trend} />}
            </div>
            <div className="mt-1.5 flex items-baseline gap-1.5">
              <span
                className={cn(
                  "text-[22px] font-semibold tracking-tight tabular-nums leading-none",
                  tone.text,
                )}
              >
                {kpi.value}
              </span>
              {kpi.unit && (
                <span className="text-[13px] text-muted-foreground font-medium">
                  {kpi.unit}
                </span>
              )}
            </div>
            {kpi.caption && (
              <div className="mt-1.5 text-[11px] text-muted-foreground tabular-nums">
                {kpi.caption}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function TrendIcon({ trend }: { trend: "up" | "down" | "flat" }) {
  if (trend === "up") return <ArrowUpRight className="h-3.5 w-3.5 text-success" />;
  if (trend === "down") return <ArrowDownRight className="h-3.5 w-3.5 text-success" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}
