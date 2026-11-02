import type { ReactNode } from "react";
import { TabBar } from "./components/TabBar";
import { useMockFarm } from "./fixtures/mockFarm";
import { useFarmRoute } from "./hooks/useFarmRoute";
import { tabOf, type Route } from "./lib/route";
import { DecideScreen } from "./screens/DecideScreen";
import { FieldScreen } from "./screens/FieldScreen";
import { PlanScreen } from "./screens/PlanScreen";
import { ReportScreen } from "./screens/ReportScreen";
import { StopScreen } from "./screens/StopScreen";
import { TalkScreen } from "./screens/TalkScreen";
import { TodayScreen } from "./screens/TodayScreen";
import { UpdatesScreen } from "./screens/UpdatesScreen";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import { ZoneScreen } from "./screens/ZoneScreen";
import type { Farm } from "./view-models/types";

function screenFor(route: Route, farm: Farm): ReactNode {
  const today = <TodayScreen view={farm.today} />;
  switch (route.screen) {
    case "welcome":
      return <WelcomeScreen />;
    case "today":
      return today;
    case "talk":
      return <TalkScreen view={farm.talk} />;
    case "updates":
      return (
        <UpdatesScreen
          view={farm.updates}
          onUndo={(taskId) => void farm.undo(taskId)}
          onMarkAllRead={() => void farm.markAllRead()}
        />
      );
    case "decide": {
      const view = farm.decision(route.taskId);
      if (view === null) return today;
      return <DecideScreen view={view} onApprove={farm.approve} onReject={farm.reject} />;
    }
    case "field":
      return <FieldScreen view={farm.field} />;
    case "zone": {
      const view = farm.zone(route.zoneId);
      return view === null ? today : <ZoneScreen view={view} />;
    }
    case "report": {
      const view = farm.report(route.reportId);
      return view === null ? today : <ReportScreen view={view} />;
    }
    case "plan":
      return <PlanScreen view={farm.plan} onUndo={farm.undo} />;
    case "stop":
      return (
        <StopScreen
          view={farm.stop}
          onStop={() => void farm.setStopped(true)}
          onResume={() => void farm.setStopped(false)}
        />
      );
  }
}

/** The shell: one phone-sized column with the current screen and the tab bar. */
export function FarmerApp() {
  const route = useFarmRoute();
  const farm = useMockFarm();
  const tab = tabOf(route);
  return (
    <div className="relative mx-auto flex h-dvh w-full max-w-[430px] flex-col overflow-hidden bg-ground">
      {screenFor(route, farm)}
      {tab === null ? null : <TabBar active={tab} />}
    </div>
  );
}
