import type { HubMaterial, KeyRequest, MaterialName } from "../types";
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
  state: KeyRequest;
  setState: (s: KeyRequest) => void;
}

const MATERIALS: { value: MaterialName; label: string }[] = [
  { value: "S235", label: "Acier S235 — Re 235 MPa" },
  { value: "S355", label: "Acier S355 — Re 355 MPa" },
];

const HUBS: { value: HubMaterial; label: string }[] = [
  { value: "steel",     label: "Acier — σ_m_adm 150 MPa" },
  { value: "cast_iron", label: "Fonte — σ_m_adm 80 MPa" },
  { value: "aluminum",  label: "Aluminium — σ_m_adm 60 MPa" },
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

export default function KeyInput({ state, setState }: Props) {
  const update = (patch: Partial<KeyRequest>) => setState({ ...state, ...patch });
  return (
    <div className="space-y-5">
      <FormSection title="Géométrie">
        <NumberField
          label="Diamètre d'arbre d (mm)"
          value={state.shaft_diameter_mm}
          onChange={(n) => update({ shaft_diameter_mm: n })}
          min={6}
        />
        <NumberField
          label="Longueur totale clavette l (mm)"
          value={state.l_total_mm}
          onChange={(n) => update({ l_total_mm: n })}
          min={0.1}
        />
        <p className="text-[11px] text-muted-foreground italic">
          ISO 773 : b et h sont sélectionnés automatiquement selon d (6 → 75 mm).
        </p>
      </FormSection>

      <FormSection title="Matériaux">
        <div className="space-y-1.5">
          <Label>Matériau arbre / clavette</Label>
          <Select value={state.material_shaft} onValueChange={(v) => update({ material_shaft: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {MATERIALS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Matériau moyeu</Label>
          <Select value={state.hub_material} onValueChange={(v) => update({ hub_material: v as HubMaterial })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {HUBS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </FormSection>

      <FormSection title="Sollicitation">
        <NumberField
          label="Couple Mt (N·m)"
          value={state.Mt_Nm}
          onChange={(n) => update({ Mt_Nm: n })}
          min={0.01}
        />
      </FormSection>
    </div>
  );
}
