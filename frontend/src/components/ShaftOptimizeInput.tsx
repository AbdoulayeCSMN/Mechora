import type { MaterialName, ShaftOptimizeRequest, ShaftType } from "../types";
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
  state: ShaftOptimizeRequest;
  setState: (s: ShaftOptimizeRequest) => void;
}

const MATERIALS: { value: MaterialName; label: string }[] = [
  { value: "S235", label: "Acier S235" },
  { value: "S355", label: "Acier S355" },
  { value: "AL6060", label: "Aluminium 6060" },
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

export default function ShaftOptimizeInput({ state, setState }: Props) {
  const update = (patch: Partial<ShaftOptimizeRequest>) =>
    setState({ ...state, ...patch });

  return (
    <div className="space-y-5">
      <FormSection title="Type & matériau">
        <div className="space-y-1.5">
          <Label>Type d'arbre</Label>
          <Select
            value={state.type}
            onValueChange={(v) => update({ type: v as ShaftType })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="solid">Arbre plein</SelectItem>
              <SelectItem value="hollow">Arbre creux</SelectItem>
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
        {state.type === "hollow" && (
          <NumberField
            label="Ratio d_int / d_ext"
            value={state.d_int_ratio}
            onChange={(n) => update({ d_int_ratio: n })}
            step="0.05"
            min={0.05}
          />
        )}
      </FormSection>

      <FormSection title="Sollicitations">
        <NumberField
          label="Moment fléchissant Mf (N·m)"
          value={state.Mf_Nm}
          onChange={(n) => update({ Mf_Nm: n })}
          min={0}
        />
        <NumberField
          label="Moment de torsion Mt (N·m)"
          value={state.Mt_Nm}
          onChange={(n) => update({ Mt_Nm: n })}
          min={0}
        />
      </FormSection>

      <FormSection title="Critères d'optimisation">
        <NumberField
          label="Coefficient de sécurité cible Cs"
          value={state.target_cs}
          onChange={(n) => update({ target_cs: n })}
          step="0.1"
          min={0.1}
        />
        <div className="grid grid-cols-2 gap-2">
          <NumberField
            label="d_min (mm)"
            value={state.d_min_mm}
            onChange={(n) => update({ d_min_mm: n })}
            min={0.1}
          />
          <NumberField
            label="d_max (mm)"
            value={state.d_max_mm}
            onChange={(n) => update({ d_max_mm: n })}
            min={0.1}
          />
        </div>
        <NumberField
          label="Pas Δd (mm)"
          value={state.step_mm}
          onChange={(n) => update({ step_mm: n })}
          step="0.5"
          min={0.1}
        />
      </FormSection>
    </div>
  );
}
