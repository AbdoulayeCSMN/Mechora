import type { BearingRequest, BearingType } from "../types";
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
  state: BearingRequest;
  setState: (s: BearingRequest) => void;
}

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

export default function BearingInput({ state, setState }: Props) {
  const update = (patch: Partial<BearingRequest>) => setState({ ...state, ...patch });
  return (
    <div className="space-y-5">
      <FormSection title="Type & charges catalogue">
        <div className="space-y-1.5">
          <Label>Type de roulement</Label>
          <Select value={state.bearing_type} onValueChange={(v) => update({ bearing_type: v as BearingType })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ball_radial">Billes à contact radial (1 rangée, p = 3)</SelectItem>
              <SelectItem value="roller_cylindrical">Rouleaux cylindriques (p = 10/3)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <NumberField
            label="C dynamique (N)"
            value={state.C_N}
            onChange={(n) => update({ C_N: n })}
            min={1}
          />
          <NumberField
            label="C0 statique (N)"
            value={state.C0_N}
            onChange={(n) => update({ C0_N: n })}
            min={0}
          />
        </div>
        <p className="text-[11px] text-muted-foreground italic">
          C et C0 sont des données catalogue (ex. SKF 6204 → C = 13 500 N, C0 = 6 550 N).
          C0 est requise dès que Fa &gt; 0 (table X/Y/e ISO 281).
        </p>
      </FormSection>

      <FormSection title="Charges appliquées">
        <div className="grid grid-cols-2 gap-2">
          <NumberField
            label="Charge radiale Fr (N)"
            value={state.Fr_N}
            onChange={(n) => update({ Fr_N: n })}
            min={0}
          />
          <NumberField
            label="Charge axiale Fa (N)"
            value={state.Fa_N}
            onChange={(n) => update({ Fa_N: n })}
            min={0}
          />
        </div>
        <p className="text-[11px] text-muted-foreground italic">
          Au moins une des deux doit être &gt; 0. Pour rouleaux cylindriques, Fa est ignoré
          (P = Fr).
        </p>
      </FormSection>

      <FormSection title="Régime & durée cible">
        <NumberField
          label="Vitesse de rotation n (tr/min)"
          value={state.n_rpm}
          onChange={(n) => update({ n_rpm: n })}
          min={1}
        />
        <div className="space-y-1.5">
          <Label>Durée de vie L10h cible (h)</Label>
          <Select
            value={String(state.target_hours)}
            onValueChange={(v) => update({ target_hours: parseFloat(v) })}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="1000">1 000 h — usage général</SelectItem>
              <SelectItem value="5000">5 000 h — véhicules</SelectItem>
              <SelectItem value="20000">20 000 h — machines 8 h/j</SelectItem>
              <SelectItem value="30000">30 000 h — machines 8 h/j (haut)</SelectItem>
              <SelectItem value="50000">50 000 h — service continu</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </FormSection>
    </div>
  );
}
