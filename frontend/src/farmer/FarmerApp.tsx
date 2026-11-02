import type { ReactNode } from "react";
import { StateView } from "./components/StateView";
import { TabBar } from "./components/TabBar";
import { useFarm } from "./hooks/useFarm";
import { useFarmRoute } from "./hooks/useFarmRoute";
import { en } from "./i18n/en";
import { hrefOf, tabOf, type Route } from "./lib/route";
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
import type { Farm, FarmState } from "./view-models/types";

function screenFor(route: Route, farm: Farm): ReactNode {
  const today = <TodayScreen view={farm.today} />;
  switch (route.screen) {
    case "welcome":
      return <WelcomeScreen />;
    case "today":
      return today;
    case "talk":
      return <TalkScreen view={farm.chat} control={farm.talk} />;
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
      return (
        <DecideScreen
          key={route.taskId}
          view={view}
          onApprove={farm.approve}
          onReject={farm.reject}
        />
      );
    }
    case "field":
      return <FieldScreen view={farm.field} />;
    case "zone": {
      const view = farm.zone(route.zoneId);
      return view === null ? today : <ZoneScreen view={view} />;
    }
    case "report": {
      const view = farm.report(route.reportId);
      return view === null ? (
        <StateView icon="document" title={en.report.emptyTitle} detail={en.report.emptyDetail} />
      ) : (
        <ReportScreen view={view} />
      );
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

function contentFor(route: Route, state: FarmState): ReactNode {
  if (route.screen === "welcome") return <WelcomeScreen />;
  switch (state.status) {
    case "loading":
      return <StateView icon="hourglass" title={en.state.loading} />;
    case "error":
      return (
        <StateView icon="warning" title={en.state.errorTitle} detail={en.state.errorDetail} />
      );
    case "empty":
      return <StateView icon="home" title={en.state.emptyTitle} detail={en.state.emptyDetail} />;
    case "ready":
      return (
        <>
          {state.stale ? <Notice text={en.state.staleData} /> : null}
          {state.farm.actionFailed ? <Notice text={en.state.actionFailed} /> : null}
          {/* `inert` stops every tap while an action runs, without greying the buttons. */}
          <div inert={state.farm.busy} className="contents">
            {/* The key plays the entrance on a change of screen, never on a data refresh. */}
            <div key={hrefOf(route)} className="flex min-h-0 flex-1 animate-screen-in flex-col">
              {screenFor(route, state.farm)}
            </div>
          </div>
        </>
      );
  }
}

function Notice({ text }: { text: string }) {
  return (
    <p
      role="alert"
      className="shrink-0 animate-notice-in bg-needs-tint px-4.5 py-2.5 text-small font-bold text-needs-text"
    >
      {text}
    </p>
  );
}

/** The shell: one phone-sized column with the current screen and the tab bar. */
export function FarmerApp() {
  const route = useFarmRoute();
  const state = useFarm();
  const tab = tabOf(route);
  return (
    <div className="relative mx-auto flex h-dvh w-full max-w-[430px] flex-col overflow-hidden bg-ground">
      {contentFor(route, state)}
      {tab === null ? null : <TabBar active={tab} />}
    </div>
  );
}
