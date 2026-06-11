import { useState } from "react";

import NavRail, { type DashboardModule } from "./components/dashboard/NavRail";
import BeamsView from "./components/views/BeamsView";
import BearingsView from "./components/views/BearingsView";
import GearsView from "./components/views/GearsView";
import KeysView from "./components/views/KeysView";
import ShaftsView from "./components/views/ShaftsView";

export default function App() {
  const [activeModule, setActiveModule] = useState<DashboardModule>("beams");

  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <NavRail module={activeModule} onModule={setActiveModule} />
      {activeModule === "beams" && <BeamsView />}
      {activeModule === "shafts" && <ShaftsView />}
      {activeModule === "keys" && <KeysView />}
      {activeModule === "bearings" && <BearingsView />}
      {activeModule === "gears" && <GearsView />}
    </div>
  );
}
