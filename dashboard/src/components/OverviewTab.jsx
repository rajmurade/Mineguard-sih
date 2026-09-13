import AIDetectionsPanel from "./AIDetectionsPanel.jsx";
import EnvironmentalPanel from "./EnvironmentalPanel.jsx";
import IncidentFeed from "./IncidentFeed.jsx";
import IncidentsByTypePie from "./IncidentsByTypePie.jsx";
import IncidentHistoryTable from "./IncidentHistoryTable.jsx";
import LiveFeedPanel from "./LiveFeedPanel.jsx";
import SimulateEventPanel from "./SimulateEventPanel.jsx";
import WorkerStatusPanel from "./WorkerStatusPanel.jsx";

export default function OverviewTab({ lastAlert }) {
  return (
    <div className="space-y-4">
      {/* above the fold: live feed + AI detections, sticky controls sidebar.
          Both the live feed and the controls sidebar pin with the same bounded-sticky
          pattern (single scroll layer); the feed travels the whole above-the-fold grid,
          then both unpin before the below-the-fold content to avoid any overlap. */}
      <div data-overview="above-fold" className="grid grid-cols-12 items-start gap-4">
        {/* left column row 1: pinned live CCTV feed (self-start keeps it top-aligned) */}
        <div data-overview="feed" className="col-span-12 space-y-4 xl:sticky xl:top-20 xl:self-start xl:z-10 xl:col-span-8 xl:col-start-1 xl:row-start-1">
          <LiveFeedPanel />
        </div>

        {/* right sidebar row 1: pins below the TopBar while this grid is in view */}
        <div data-overview="sticky" className="col-span-12 space-y-4 xl:sticky xl:top-20 xl:self-start xl:z-20 xl:col-span-4 xl:col-start-9 xl:row-start-1">
          <EnvironmentalPanel />
          <IncidentFeed alert={lastAlert} maxItems={12} compact />
          <SimulateEventPanel />
        </div>

        {/* left column row 2: AI detections scrolls naturally under the pinned feed */}
        <div className="col-span-12 space-y-4 xl:col-span-8 xl:col-start-1 xl:row-start-2">
          <AIDetectionsPanel />
        </div>
      </div>

      {/* below the fold: scrolls naturally with the page, never under the sticky column */}
      <div data-overview="below-fold" className="grid grid-cols-12 items-start gap-4">
        <div className="col-span-12 xl:col-span-8">
          <IncidentHistoryTable />
        </div>
        <div className="col-span-12 xl:col-span-4">
          <div data-overview="pie">
            <IncidentsByTypePie />
          </div>
        </div>
      </div>

      {/* workers on site */}
      <WorkerStatusPanel />
    </div>
  );
}