import type { BearingOptimizeRequest, BearingType } from "../types";
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
  state: BearingOptimizeRequest;
  setState: (s: BearingOptimizeRequest) => void;
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

export default function BearingOptimizeInput({ state, setState }: Props) {
  const update = (patch: Partial<BearingOptimizeRequest>) => setState({ ...state, ...patch });
  return (
    <div className="space-y-5">
      <FormSection title="Type">
        <div className="space-y-1.5">
          <Label>Type de roulement</Label>
          <Select value={state.bearing_type} onValueChange={(v) => update({ bearing_type: v as BearingType })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ball_radial">Billes radial — catalogue 6200…6212</SelectItem>
              <SelectItem value="roller_cylindrical">Rouleaux cylindriques — NU 204…NU 212</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </FormSection>

      <FormSection title="Charges">
        <div className="grid grid-cols-2 gap-2">
          <NumberField label="Fr (N)" value={state.Fr_N} onChange={(n) => update({ Fr_N: n })} min={0} />
          <NumberField label="Fa (N)" value={state.Fa_N} onChange={(n) => update({ Fa_N: n })} min={0} />
        </div>
      </FormSection>

      <FormSection title="Régime & critères cible">
        <NumberField
          label="Vitesse n (tr/min)"
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
              <SelectItem value="20000">20 000 h — machines industrielles</SelectItem>
              <SelectItem value="30000">30 000 h — machines (haut)</SelectItem>
              <SelectItem value="50000">50 000 h — service continu</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <NumberField
          label="Facteur statique cible S0"
          value={state.S0_target}
          onChange={(n) => update({ S0_target: n })}
          step="0.1"
          min={0.1}
        />
        <p className="text-[11px] text-muted-foreground italic">
          S0 ≥ 1.0 : fonctionnement normal. S0 ≥ 1.2 : résistance aux chocs.
        </p>
      </FormSection>
    </div>
  );
}
