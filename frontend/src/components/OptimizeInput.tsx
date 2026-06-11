import { Plus, Trash2 } from "lucide-react";
import type {
  LoadInput,
  MaterialName,
  OptimizeRequest,
  ProfileFamily,
  SupportType,
} from "../types";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group";

interface Props {
  state: OptimizeRequest;
  setState: (s: OptimizeRequest) => void;
}

const MATERIALS: { value: MaterialName; label: string }[] = [
  { value: "S235", label: "Acier S235" },
  { value: "S355", label: "Acier S355" },
  { value: "AL6060", label: "Aluminium 6060" },
];

const SUPPORTS: { value: SupportType; label: string }[] = [
  { value: "simply_supported", label: "Appui simple (2 appuis)" },
  { value: "cantilever", label: "Encastrement (console)" },
];

function NumberField({
  label,
  value,
  onChange,
  step = "any",
  min,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  step?: string;
  min?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        step={step}
        min={min}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function OptimizeInput({ state, setState }: Props) {
  const update = (patch: Partial<OptimizeRequest>) => setState({ ...state, ...patch });

  const updateLoad = (i: number, ld: LoadInput) => {
    const next = state.loads.slice();
    next[i] = ld;
    update({ loads: next });
  };

  const removeLoad = (i: number) =>
    update({ loads: state.loads.filter((_, j) => j !== i) });

  const addPointLoad = () =>
    update({
      loads: [
        ...state.loads,
        { type: "point", magnitude_kN: 5, position_m: state.length_m / 2 },
      ],
    });

  const addDistributedLoad = () =>
    update({
      loads: [
        ...state.loads,
        {
          type: "distributed",
          magnitude_kN_per_m: 2,
          start_m: 0,
          end_m: state.length_m,
        },
      ],
    });

  const admissibleMm =
    Number.isFinite(state.length_m / state.deflection_ratio)
      ? ((state.length_m / state.deflection_ratio) * 1000).toFixed(1)
      : "–";

  return (
    <div className="space-y-5">
      {/* Geometry + supports */}
      <FormSection title="Géométrie & appuis">
        <NumberField
          label="Longueur L (m)"
          value={state.length_m}
          onChange={(n) => update({ length_m: n })}
          min={0.01}
        />
        <div className="space-y-1.5">
          <Label>Type d'appui</Label>
          <Select
            value={state.support}
            onValueChange={(v) => update({ support: v as SupportType })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SUPPORTS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Matériau</Label>
          <Select
            value={state.material}
            onValueChange={(v) => update({ material: v })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MATERIALS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </FormSection>

      {/* Optimization criteria */}
      <FormSection title="Critères d'optimisation">
        <NumberField
          label="Coefficient de sécurité cible Cs"
          value={state.target_safety_factor}
          onChange={(n) => update({ target_safety_factor: n })}
          step="0.1"
          min={0.1}
        />
        <NumberField
          label="Limite de flèche  L / n  (n =)"
          value={state.deflection_ratio}
          onChange={(n) => update({ deflection_ratio: n })}
          step="10"
          min={1}
        />
        <p className="text-[11px] text-muted-foreground tabular-nums">
          Flèche admissible ≈ <b className="text-foreground">{admissibleMm} mm</b>
        </p>
        <div className="space-y-1.5">
          <Label>Catalogues à considérer</Label>
          <ToggleGroup
            type="multiple"
            value={state.catalogs as string[]}
            onValueChange={(v) => {
              // Prevent unselecting the last one (need ≥ 1)
              if (v.length === 0) return;
              update({ catalogs: v as ProfileFamily[] });
            }}
            className="grid grid-cols-3 gap-1.5 w-full p-0 bg-transparent border-0"
          >
            {(["IPE", "HEA", "HEB", "UPN", "SHS", "CHS"] as const).map((fam) => (
              <ToggleGroupItem
                key={fam}
                value={fam}
                className="border border-border h-9 text-xs font-semibold"
              >
                {fam}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <p className="text-[11px] text-muted-foreground italic">
            La recherche fusionne les catalogues cochés et choisit le profilé le plus
            léger qui passe.
          </p>
        </div>
      </FormSection>

      {/* Loads */}
      <FormSection title="Charges">
        {state.loads.length === 0 && (
          <p className="text-[12px] text-muted-foreground italic">
            Aucune charge. Ajoute une charge ci-dessous.
          </p>
        )}
        {state.loads.map((ld, i) => (
          <div
            key={i}
            className="rounded-md border border-border bg-background/60 p-2.5 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
                {ld.type === "point"
                  ? `Charge ponctuelle F${i + 1}`
                  : `Charge répartie q${i + 1}`}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => removeLoad(i)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
            {ld.type === "point" ? (
              <div className="grid grid-cols-2 gap-2">
                <NumberField
                  label="Magnitude (kN)"
                  value={ld.magnitude_kN}
                  onChange={(n) => updateLoad(i, { ...ld, magnitude_kN: n })}
                  min={0.001}
                />
                <NumberField
                  label="Position (m)"
                  value={ld.position_m}
                  onChange={(n) => updateLoad(i, { ...ld, position_m: n })}
                  min={0}
                />
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                <NumberField
                  label="q (kN/m)"
                  value={ld.magnitude_kN_per_m}
                  onChange={(n) =>
                    updateLoad(i, { ...ld, magnitude_kN_per_m: n })
                  }
                  min={0.001}
                />
                <NumberField
                  label="Début (m)"
                  value={ld.start_m}
                  onChange={(n) => updateLoad(i, { ...ld, start_m: n })}
                  min={0}
                />
                <NumberField
                  label="Fin (m)"
                  value={ld.end_m}
                  onChange={(n) => updateLoad(i, { ...ld, end_m: n })}
                  min={0}
                />
              </div>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={addPointLoad}>
            <Plus className="h-3.5 w-3.5" /> Ponctuelle
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={addDistributedLoad}
          >
            <Plus className="h-3.5 w-3.5" /> Répartie
          </Button>
        </div>
      </FormSection>
    </div>
  );
}
