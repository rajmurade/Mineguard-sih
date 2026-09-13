import EnvironmentalPanel from "./EnvironmentalPanel.jsx";
import MetricTrendsPanel from "./MetricTrendsPanel.jsx";

export default function EnvironmentTab() {
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 space-y-4">
        <EnvironmentalPanel />
        <MetricTrendsPanel />
      </div>
    </div>
  );
}