import { AlertTriangle, CheckCircle2, Info, Lightbulb, Wand2, Zap } from "lucide-react";
import type { Advice } from "../types";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { cn } from "@/lib/utils";

interface Props {
  advice: Advice;
  verdict?: string;
  onOptimize?: () => void;
}

type Tone = "ok" | "warn" | "danger" | "info";

function toneFor(verdict?: string, facteur?: string): Tone {
  if (verdict === "OK") return "ok";
  if (verdict === "Surdimensionné") return "info";
  if (verdict === "Limite") return "warn";
  if (verdict === "Sous-dimensionné") return "danger";
  if (facteur === "aucun") return "ok";
  return "danger";
}

function IconFor({ tone }: { tone: Tone }) {
  const common = "h-6 w-6 shrink-0";
  if (tone === "ok") return <CheckCircle2 className={cn(common, "text-success")} />;
  if (tone === "info") return <Lightbulb className={cn(common, "text-info")} />;
  if (tone === "warn") return <Zap className={cn(common, "text-warning")} />;
  if (tone === "danger") return <AlertTriangle className={cn(common, "text-destructive")} />;
  return <Info className={common} />;
}

const TONE_STYLES: Record<Tone, { card: string; conseil: string }> = {
  ok: {
    card: "border-l-4 border-l-success bg-success/5",
    conseil: "text-success",
  },
  warn: {
    card: "border-l-4 border-l-warning bg-warning/5",
    conseil: "text-warning italic",
  },
  danger: {
    card: "border-l-4 border-l-destructive bg-destructive/5",
    conseil: "text-primary italic",
  },
  info: {
    card: "border-l-4 border-l-info bg-info/5",
    conseil: "text-info italic",
  },
};

export default function AdviceCard({ advice, verdict, onOptimize }: Props) {
  const tone = toneFor(verdict, advice.facteur_limitant);
  const styles = TONE_STYLES[tone];

  return (
    <Card className={cn(styles.card)}>
      <CardContent className="pt-5 pb-5 space-y-4">
        <div className="flex items-start gap-3">
          <IconFor tone={tone} />
          <div className="flex-1 min-w-0">
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Diagnostic
            </div>
            <div className="mt-0.5 text-[15px] font-semibold leading-snug">
              {advice.diagnostic}
            </div>
          </div>
        </div>

        <div className="space-y-2.5 pl-9">
          <div>
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Cause
            </div>
            <p className="mt-0.5 text-[13px] text-foreground tabular-nums leading-relaxed">
              {advice.cause}
            </p>
          </div>
          <div>
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Conseil
            </div>
            <p
              className={cn(
                "mt-0.5 text-[13.5px] font-medium leading-relaxed",
                styles.conseil,
              )}
            >
              {advice.conseil}
            </p>
          </div>
        </div>

        {onOptimize && (
          <div className="pl-9">
            <Button onClick={onOptimize}>
              <Wand2 className="h-4 w-4" />
              Lancer l'optimisation
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
