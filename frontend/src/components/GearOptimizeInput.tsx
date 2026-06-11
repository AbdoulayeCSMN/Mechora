import type { GearOptimizeRequest, MaterialName } from "../types";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

interface Props {
  state: GearOptimizeRequest;
  setState: (s: GearOptimizeRequest) => void;
}

const MATERIALS: { value: MaterialName | string; label: string }[] = [
  { value: "S235", label: "Acier S235" },
  { value: "S355", label: "Acier S355" },
  { value: "C45E", label: "Acier C45E" },
  { value: "42CrMo4", label: "Acier 42CrMo4" },
  { value: "16NiCr6", label: "Acier 16NiCr6" },
];

function NumberField({
  label, value, onChange, step = "any", min,
}: {
  label: string; value: number; onChange: (n: number) => void; step?: string; min?: number;
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

export default function GearOptimizeInput({ state, setState }: Props) {
  const update = (patch: Partial<GearOptimizeRequest>) => setState({ ...state, ...patch });
  return (
    <div className="space-y-5">
      <FormSection title="Géométrie & matériaux">
        <div className="grid grid-cols-2 gap-2">
          <NumberField
            label="Dents pignon z1"
            value={state.z1}
            onChange={(n) => update({ z1: Math.round(n) })}
            step="1"
            min={12}
          />
          <NumberField
            label="Dents roue z2"
            value={state.z2}
            onChange={(n) => update({ z2: Math.round(n) })}
            step="1"
            min={12}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Matériau pignon</Label>
          <Select value={state.material_pinion} onValueChange={(v) => update({ material_pinion: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {MATERIALS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Matériau roue</Label>
          <Select value={state.material_gear} onValueChange={(v) => update({ material_gear: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {MATERIALS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </FormSection>

      <FormSection title="Sollicitation">
        <NumberField
          label="Couple sur le pignon Mt1 (N·m)"
          value={state.Mt1_Nm}
          onChange={(n) => update({ Mt1_Nm: n })}
          min={0.01}
        />
        <NumberField
          label="Vitesse pignon n1 (tr/min)"
          value={state.n1_rpm}
          onChange={(n) => update({ n1_rpm: n })}
          min={1}
        />
        <NumberField
          label="Facteur d'application K_A"
          value={state.K_A}
          onChange={(n) => update({ K_A: n })}
          step="0.1"
          min={0.1}
        />
      </FormSection>

      <FormSection title="Critères de recherche">
        <NumberField
          label="Cs cible"
          value={state.target_cs}
          onChange={(n) => update({ target_cs: n })}
          step="0.1"
          min={0.1}
        />
        <NumberField
          label="Rapport largeur/module ψ_m = b/m"
          value={state.psi_m}
          onChange={(n) => update({ psi_m: n })}
          step="0.5"
          min={1}
        />
      </FormSection>
    </div>
  );
}
