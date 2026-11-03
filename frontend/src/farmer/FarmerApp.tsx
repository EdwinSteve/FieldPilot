import { useEffect, useRef, type ReactNode } from "react";
import { BackTarget } from "./components/backTarget";
import { BigButton } from "./components/BigButton";
import { StateView } from "./components/StateView";
import { TabBar } from "./components/TabBar";
import { useFarm } from "./hooks/useFarm";
import { useFarmRoute } from "./hooks/useFarmRoute";
import { useFocusHeading } from "./hooks/useFocusHeading";
import { useOnline } from "./hooks/useOnline";
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

function screenFor(route: Route, farm: Farm, age: string | null): ReactNode {
  const today = <TodayScreen view={farm.today} age={age} />;
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

/** The one line under the screen's top that says the farm may not be current. */
function connectionNotice(online: boolean, stale: boolean, age: string | null): string | null {
  if (!online) return en.state.offline;
  if (!stale) return null;
  return en.state.stale(age ?? en.freshness.justNow);
}

function contentFor(route: Route, state: FarmState, online: boolean): ReactNode {
  if (route.screen === "welcome") return <WelcomeScreen />;
  switch (state.status) {
    case "loading":
      return <StateView icon="hourglass" title={en.state.loading} />;
    case "error":
      return (
        <StateView
          icon={online ? "warning" : "cloudOff"}
          title={online ? en.state.errorTitle : en.state.offline}
          detail={`${en.state.errorDetail} ${en.state.lastTried(state.lastTried)}`}
        >
          <div className="flex w-full max-w-80 flex-col pt-2">
            <BigButton variant="primary" disabled={state.retrying} onClick={state.retry}>
              {state.retrying ? en.state.retrying : en.state.retry}
            </BigButton>
          </div>
        </StateView>
      );
    case "empty":
      return <StateView icon="home" title={en.state.emptyTitle} detail={en.state.emptyDetail} />;
    case "ready": {
      const failure = state.farm.actionFailure;
      // A failed tap offline already says "No signal": one notice is enough.
      const notice =
        failure === "offline" ? null : connectionNotice(online, state.stale, state.age);
      return (
        <>
          {notice === null ? null : <Notice text={notice} />}
          {failure === null ? null : <Notice text={en.state.failures[failure]} />}
          {state.farm.busy ? <Saving /> : null}
          {/* `inert` stops every tap while an action runs, without greying the buttons. */}
          <div inert={state.farm.busy} className="contents">
            {/* The key plays the entrance on a change of screen, never on a data refresh. */}
            <div key={hrefOf(route)} className="flex min-h-0 flex-1 animate-screen-in flex-col">
              {screenFor(route, state.farm, state.age)}
            </div>
          </div>
        </>
      );
    }
  }
}

/** Floats over the screen so nothing jumps. A fast action never shows it. */
function Saving() {
  return (
    <output className="absolute top-3 left-1/2 z-20 -translate-x-1/2 animate-fade-in rounded-pill bg-ink px-4 py-2 text-small font-bold text-surface shadow-bubble [animation-delay:250ms]">
      {en.state.working}
    </output>
  );
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
  const { route, back } = useFarmRoute();
  const state = useFarm();
  const online = useOnline();
  const tab = tabOf(route);
  const shell = useRef<HTMLDivElement>(null);
  const farm = state.status === "ready" ? state.farm : null;

  useEffect(() => {
    const name = en.titles.screens[route.screen];
    document.title = route.screen === "welcome" ? en.titles.app : en.titles.page(name);
  }, [route.screen]);

  useFocusHeading(hrefOf(route), shell);

  return (
    <div
      ref={shell}
      className="relative mx-auto flex h-dvh w-full max-w-[430px] flex-col overflow-hidden bg-ground pt-[env(safe-area-inset-top)]"
    >
      <BackTarget value={back}>{contentFor(route, state, online)}</BackTarget>
      {tab === null ? null : (
        <TabBar
          active={tab}
          unread={farm?.updates.unreadCount ?? 0}
          decisionWaiting={(farm?.today.decision ?? null) !== null}
        />
      )}
    </div>
  );
}
