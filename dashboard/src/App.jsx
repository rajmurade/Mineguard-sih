import { useEffect, useState } from "react";
import { getDashboardSummary } from "./api.js";
import EnvironmentTab from "./components/EnvironmentTab.jsx";
import IncidentHistoryTable from "./components/IncidentHistoryTable.jsx";
import KpiBar from "./components/KpiBar.jsx";
import OverviewTab from "./components/OverviewTab.jsx";
import ReportsTab from "./components/ReportsTab.jsx";
import Sidebar from "./components/Sidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import TrendsPanel from "./components/TrendsPanel.jsx";
import { useAlerts } from "./hooks/useAlerts.js";

export default function App() {
  const [section, setSection] = useState("overview");
  const [lastAlert, setLastAlert] = useState(null);
  const [summary, setSummary] = useState(null);
  const [backendOk, setBackendOk] = useState(true);

  // Single WS connection; TopBar + feed both consume it.
  const wsStatus = useAlerts((message) => setLastAlert(message));

  useEffect(() => {
    const load = async () => {
      try {
        setSummary(await getDashboardSummary());
        setBackendOk(true);
      } catch {
        setBackendOk(false);
      }
    };
    load();
    const timer = window.setInterval(load, 20000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen md:pl-48">
      <Sidebar section={section} onSelect={setSection} />

      <div className="flex min-h-screen flex-col">
        <TopBar wsStatus={wsStatus} summary={summary} backendOk={backendOk} />
        <KpiBar />

        <main className="mx-auto w-full max-w-screen-2xl flex-1 p-4">
          {section === "overview" && <OverviewTab lastAlert={lastAlert} />}
          {section === "incidents" && (
            <div className="space-y-4">
              <IncidentHistoryTable />
              <TrendsPanel />
            </div>
          )}
          {section === "environment" && <EnvironmentTab />}
          {section === "reports" && <ReportsTab />}
        </main>

        <footer className="border-t border-ops-border py-4 text-center text-[10px] uppercase tracking-widest text-slate-600">
          MineGuard · safety operations center · ws /ws/alerts
        </footer>
      </div>
    </div>
  );
}