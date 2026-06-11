import { useEffect, useState } from "react";
import { Activity, ChevronRight, Download, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

type ApiStatus = "checking" | "online" | "offline";

interface Props {
  module: "beams" | "shafts" | "keys" | "bearings" | "gears";
  mode: "verify" | "optimize";
  lastComputed?: Date | null;
  onReset: () => void;
  onExport: () => void;
  canExport: boolean;
}

export default function TopBar({
  module,
  mode,
  lastComputed,
  onReset,
  onExport,
  canExport,
}: Props) {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const r = await fetch(
          (import.meta.env.VITE_API_BASE ?? "http://localhost:8000") + "/health",
          { cache: "no-store" },
        );
        if (!cancelled) setStatus(r.ok ? "online" : "offline");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const moduleLabel =
    module === "beams" ? "Poutres en flexion"
    : module === "shafts" ? "Arbres en torsion + flexion"
    : module === "keys" ? "Clavetage parallèle"
    : module === "bearings" ? "Roulements (durée de vie L10)"
    : "Engrenages droits (Lewis + Hertz)";
  const modeLabel = mode === "verify" ? "Vérification" : "Optimisation";

  return (
    <header className="h-14 shrink-0 border-b bg-background flex items-center px-5 gap-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm min-w-0">
        <span className="text-muted-foreground">Mechora</span>
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="text-muted-foreground">{moduleLabel}</span>
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="font-semibold text-foreground truncate">{modeLabel}</span>
      </div>

      <div className="flex-1" />

      {/* Last computed */}
      {lastComputed && (
        <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground tabular-nums">
          <Activity className="h-3.5 w-3.5" />
          Dernier calcul : {formatTime(lastComputed)}
        </div>
      )}

      <Separator orientation="vertical" className="h-6 hidden md:block" />

      {/* API status */}
      <ApiStatusPill status={status} />

      <Separator orientation="vertical" className="h-6" />

      {/* Actions */}
      <Button variant="ghost" size="sm" onClick={onReset}>
        <RotateCcw className="h-3.5 w-3.5" />
        Réinitialiser
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={onExport}
        disabled={!canExport}
      >
        <Download className="h-3.5 w-3.5" />
        Exporter
      </Button>
    </header>
  );
}

function ApiStatusPill({ status }: { status: ApiStatus }) {
  const config = {
    checking: {
      dot: "bg-muted-foreground animate-pulse",
      label: "Vérification…",
      color: "text-muted-foreground",
    },
    online: {
      dot: "bg-success",
      label: "API en ligne",
      color: "text-success",
    },
    offline: {
      dot: "bg-destructive",
      label: "API hors-ligne",
      color: "text-destructive",
    },
  }[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", config.color)}>
      <span className={cn("inline-block h-2 w-2 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}

function formatTime(d: Date): string {
  const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
