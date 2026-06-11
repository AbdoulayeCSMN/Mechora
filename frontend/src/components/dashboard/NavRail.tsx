import {
  CircleDot,
  Cog,
  Cpu,
  HelpCircle,
  Key,
  RectangleHorizontal,
  Settings,
  Settings2,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type DashboardModule = "beams" | "shafts" | "keys" | "bearings" | "gears";

interface Props {
  module: DashboardModule;
  onModule: (m: DashboardModule) => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}

export default function NavRail({ module, onModule }: Props) {
  const items: NavItem[] = [
    {
      id: "beams",
      label: "Poutres",
      icon: RectangleHorizontal,
      active: module === "beams",
      onClick: () => onModule("beams"),
    },
    {
      id: "shafts",
      label: "Arbres",
      icon: Cog,
      active: module === "shafts",
      onClick: () => onModule("shafts"),
    },
    {
      id: "keys",
      label: "Clavetage",
      icon: Key,
      active: module === "keys",
      onClick: () => onModule("keys"),
    },
    {
      id: "bearings",
      label: "Roulements",
      icon: CircleDot,
      active: module === "bearings",
      onClick: () => onModule("bearings"),
    },
    {
      id: "gears",
      label: "Engrenages",
      icon: Settings2,
      active: module === "gears",
      onClick: () => onModule("gears"),
    },
  ];

  const bottom: NavItem[] = [
    { id: "settings", label: "Réglages", icon: Settings, disabled: true },
    { id: "help", label: "Aide", icon: HelpCircle, disabled: true },
  ];

  return (
    <aside className="hidden md:flex w-[76px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex items-center justify-center h-14 border-b border-sidebar-border">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Cpu className="h-5 w-5" strokeWidth={2.25} />
        </div>
      </div>

      <nav className="flex-1 flex flex-col items-center gap-1 py-3">
        {items.map((it) => (
          <NavButton key={it.id} item={it} />
        ))}
      </nav>

      <nav className="flex flex-col items-center gap-1 py-3 border-t border-sidebar-border">
        {bottom.map((it) => (
          <NavButton key={it.id} item={it} />
        ))}
      </nav>
    </aside>
  );
}

function NavButton({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      onClick={item.onClick}
      disabled={item.disabled}
      title={item.label}
      className={cn(
        "relative w-[60px] py-2 rounded-md flex flex-col items-center gap-1 transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        item.active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
        item.disabled &&
          "opacity-40 cursor-not-allowed hover:bg-transparent hover:text-muted-foreground",
      )}
    >
      {item.active && (
        <span className="absolute -left-2 top-1/2 -translate-y-1/2 w-[3px] h-7 rounded-r-full bg-primary" />
      )}
      <Icon
        className={cn(
          "h-5 w-5 transition-transform",
          item.active && "scale-110",
        )}
      />
      <span className="text-[10px] font-medium tracking-wide">{item.label}</span>
    </button>
  );
}
