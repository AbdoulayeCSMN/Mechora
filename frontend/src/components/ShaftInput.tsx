import type { MaterialName, ShaftRequest, ShaftType } from "../types";
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
  state: ShaftRequest;
  setState: (s: ShaftRequest) => void;
}

const MATERIALS: { value: MaterialName; label: string }[] = [
  { value: "S235", label: "Acier S235 — Re 235 MPa" },
  { value: "S355", label: "Acier S355 — Re 355 MPa" },
  { value: "AL6060", label: "Aluminium 6060 — Re 160 MPa" },
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

export default function ShaftInput({ state, setState }: Props) {
  const update = (patch: Partial<ShaftRequest>) => setState({ ...state, ...patch });

  const setType = (t: ShaftType) => {
    if (t === "solid") {
      update({ type: t, d_int_mm: 0 });
    } else {
      // Default d_int = 0.6 × d_ext if previously 0
      const next_d_int =
        state.d_int_mm > 0 && state.d_int_mm < state.d_ext_mm
          ? state.d_int_mm
          : Math.max(1, state.d_ext_mm * 0.6);
      update({ type: t, d_int_mm: next_d_int });
    }
  };

  return (
    <div className="space-y-5">
      <FormSection title="Section">
        <div className="space-y-1.5">
          <Label>Type d'arbre</Label>
          <Select value={state.type} onValueChange={(v) => setType(v as ShaftType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="solid">Arbre plein</SelectItem>
              <SelectItem value="hollow">Arbre creux</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {state.type === "solid" ? (
          <NumberField
            label="Diamètre d (mm)"
            value={state.d_ext_mm}
            onChange={(n) => update({ d_ext_mm: n })}
            min={0.1}
          />
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <NumberField
              label="D extérieur (mm)"
              value={state.d_ext_mm}
              onChange={(n) => update({ d_ext_mm: n })}
              min={0.1}
            />
            <NumberField
              label="d intérieur (mm)"
              value={state.d_int_mm}
              onChange={(n) => update({ d_int_mm: n })}
              min={0.1}
            />
          </div>
        )}
      </FormSection>

      <FormSection title="Matériau">
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
        <p className="text-[11px] text-muted-foreground italic">
          Au moins l'un des deux doit être &gt; 0. σ_eq = √(σ_f² + 3·τ²).
        </p>
      </FormSection>
    </div>
  );
}
