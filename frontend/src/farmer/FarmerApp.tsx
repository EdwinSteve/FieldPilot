import { useEffect, useRef, useState, type ReactNode } from "react";
import { BackTarget } from "./components/backTarget";
import { BigButton } from "./components/BigButton";
import { StateView } from "./components/StateView";
import { TabBar } from "./components/TabBar";
import type { FarmPlot, StartedCycle } from "./api/lifecycle";
import type { HarvestNote } from "./components/HarvestSheet";
import { phoneClock, useFarm } from "./hooks/useFarm";
import { useFarmProgress, type FarmProgress } from "./hooks/useFarmProgress";
import { useFarmRoute } from "./hooks/useFarmRoute";
import { useFocusHeading } from "./hooks/useFocusHeading";
import { useOnline } from "./hooks/useOnline";
import { useSession, type SessionControl } from "./hooks/useSession";
import { en } from "./i18n/en";
import { gatedRoute, startRoute } from "./lib/accountGate";
import { cropLabel } from "./lib/names";
import { hrefOf, tabOf, type Route } from "./lib/route";
import { LogInScreen, SignUpScreen } from "./screens/AccountScreens";
import { AdviceScreen } from "./screens/AdviceScreen";
import { DecideScreen } from "./screens/DecideScreen";
import { FieldScreen } from "./screens/FieldScreen";
import { PlanScreen } from "./screens/PlanScreen";
import { ReportScreen } from "./screens/ReportScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { SetupScreen } from "./screens/SetupScreen";
import { StopScreen } from "./screens/StopScreen";
import { TalkScreen } from "./screens/TalkScreen";
import { TodayScreen } from "./screens/TodayScreen";
import { UpdatesScreen } from "./screens/UpdatesScreen";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import { ZoneScreen } from "./screens/ZoneScreen";
import type { Farm, FarmState, PlantedNote } from "./view-models/types";

/** What the farm screens can ask of the shell: the harvest that ends the crop, and the note after sowing. */
interface ShellActions {
  onHarvested: (note: HarvestNote) => void;
  planted: PlantedNote | null;
  onPlantedSeen: () => void;
}

function screenFor(route: Route, farm: Farm, age: string | null, shell: ShellActions): ReactNode {
  const today = (
    <TodayScreen
      view={farm.today}
      age={age}
      planted={shell.planted}
      onPlantedSeen={shell.onPlantedSeen}
      savedAnswers={farm.savedAnswers}
      onHarvested={shell.onHarvested}
    />
  );
  switch (route.screen) {
    // Entry and setup screens never wait for the farm: `FarmerApp` shows them first.
    case "welcome":
    case "login":
    case "signup":
    case "setup":
    case "advice":
    case "settings":
      return null;
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
          saved={farm.savedAnswers.includes(route.taskId)}
        />
      );
    }
    case "field":
      return <FieldScreen view={farm.field} onAsk={farm.talk.setDraft} />;
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
      return <PlanScreen view={farm.plan} onUndo={farm.undo} onHarvested={shell.onHarvested} />;
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
  if (!online) return en.state.offlineBrowsing;
  if (!stale) return null;
  return en.state.stale(age ?? en.freshness.justNow);
}

function entryFor(shown: Route, session: SessionControl, online: boolean): ReactNode {
  switch (shown.screen) {
    case "welcome":
      return (
        <WelcomeScreen
          startHref={hrefOf(startRoute(session.farmer !== null, session.known !== null))}
        />
      );
    case "login":
      return <LogInScreen session={session} />;
    case "signup":
      return <SignUpScreen session={session} online={online} />;
    default:
      return null;
  }
}

/** Before a crop grows: set up the farm, then choose what to sow. */
function setupFor(
  shown: Route,
  session: SessionControl,
  farm: FarmProgress,
  harvested: HarvestNote | null,
  onPlanted: (cycle: StartedCycle) => void,
): ReactNode {
  const stage = farm.stage;
  const farmer = session.farmer;
  if (farmer === null || stage === null) return null;
  if (shown.screen === "setup" && stage.stage === "no_plot") {
    return <SetupScreen farmer={farmer} home={session.known?.home ?? null} onSaved={farm.reload} />;
  }
  if (shown.screen === "advice" && stage.stage === "no_cycle") {
    return (
      <AdviceScreen key={stage.plot.id} plot={stage.plot} harvested={harvested} onPlanted={onPlanted} />
    );
  }
  return null;
}

interface FarmAreaProps {
  plot: FarmPlot;
  route: Route;
  shown: Route;
  online: boolean;
  shell: ShellActions;
}

/** The farm with a crop growing: its screens, kept fresh, and the tab bar. */
function FarmArea({ plot, route, shown, online, shell }: FarmAreaProps) {
  const state = useFarm(plot.id);
  const tab = tabOf(shown);
  const farm = state.status === "ready" ? state.farm : null;
  return (
    <>
      {farmContent(route, shown, state, online, shell)}
      {tab === null ? null : (
        <TabBar
          active={tab}
          unread={farm?.updates.unreadCount ?? 0}
          decisionWaiting={(farm?.today.decision ?? null) !== null}
        />
      )}
    </>
  );
}

function farmContent(
  route: Route,
  shown: Route,
  state: FarmState,
  online: boolean,
  shell: ShellActions,
): ReactNode {
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
          {state.farm.outboxNotice === null ? null : <Notice text={state.farm.outboxNotice} />}
          {state.farm.busy ? <Saving /> : null}
          {/* `inert` stops every tap while an action runs, without greying the buttons. */}
          <div inert={state.farm.busy} className="contents">
            {/* The key plays the entrance on a change of screen, never on a data refresh. */}
            <div key={hrefOf(route)} className="flex min-h-0 flex-1 animate-screen-in flex-col">
              {screenFor(shown, state.farm, state.age, shell)}
            </div>
          </div>
        </>
      );
    }
  }
}

function signedInContent(
  route: Route,
  shown: Route,
  session: SessionControl,
  farm: FarmProgress,
  online: boolean,
  shell: ShellActions & { harvested: HarvestNote | null; onPlanted: (cycle: StartedCycle) => void },
): ReactNode {
  if (farm.failed) {
    return (
      <StateView
        icon={online ? "warning" : "cloudOff"}
        title={online ? en.state.errorTitle : en.state.offline}
        detail={`${en.state.errorDetail} ${en.state.lastTried(phoneClock(farm.triedAt))}`}
      >
        <div className="flex w-full max-w-80 flex-col pt-2">
          <BigButton variant="primary" onClick={farm.reload}>
            {en.state.retry}
          </BigButton>
        </div>
      </StateView>
    );
  }
  const stage = farm.stage;
  if (stage === null) return <StateView icon="hourglass" title={en.state.loading} />;
  const farmer = session.farmer;
  if (shown.screen === "settings" && farmer !== null) {
    return (
      <SettingsScreen
        farmer={farmer}
        plot={stage.stage === "no_plot" ? null : stage.plot}
        onSignOut={() => void session.logOut()}
        onSignOutEverywhere={session.logOutEverywhere}
      />
    );
  }
  if (stage.stage !== "farming") return setupFor(shown, session, farm, shell.harvested, shell.onPlanted);
  return (
    <FarmArea
      key={stage.plot.id}
      plot={stage.plot}
      route={route}
      shown={shown}
      online={online}
      shell={shell}
    />
  );
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
  const online = useOnline();
  const session = useSession();
  const signedIn = session.farmer !== null;
  const farm = useFarmProgress(session.farmer?.id ?? null);
  // Signed out, the log-in stands in front of the screen the URL asks for.
  const shown = gatedRoute(route, signedIn, session.known !== null, farm.progress);
  const shell = useRef<HTMLDivElement>(null);
  // Said once on What to plant after the harvest; gone after the next sowing or sign-out.
  const [harvested, setHarvested] = useState<HarvestNote | null>(null);
  const onHarvested = (note: HarvestNote) => {
    setHarvested(note);
    farm.reload();
  };
  // Said once on Today after sowing, until the farmer taps OK.
  const [planted, setPlanted] = useState<PlantedNote | null>(null);
  const onPlanted = (cycle: StartedCycle) => {
    setPlanted({ crop: cropLabel(cycle.crop), automated: cycle.automated });
    setHarvested(null);
    farm.reload();
  };
  const shellActions = {
    onHarvested,
    planted,
    onPlantedSeen: () => setPlanted(null),
    harvested,
    onPlanted,
  };

  useEffect(() => {
    const name = en.titles.screens[shown.screen];
    document.title = shown.screen === "welcome" ? en.titles.app : en.titles.page(name);
  }, [shown.screen]);

  // Signed in, a screen the gate replaced shows in the URL too, so Back and a reload agree.
  const replaced = signedIn && hrefOf(shown) !== hrefOf(route) ? hrefOf(shown) : null;
  useEffect(() => {
    if (replaced !== null) window.location.replace(replaced);
  }, [replaced]);

  useFocusHeading(hrefOf(shown), shell);

  return (
    <div
      ref={shell}
      className="relative mx-auto flex h-dvh w-full max-w-[430px] flex-col overflow-hidden bg-ground pt-[env(safe-area-inset-top)]"
    >
      <BackTarget value={back}>
        {!signedIn || shown.screen === "welcome"
          ? entryFor(shown, session, online)
          : signedInContent(route, shown, session, farm, online, shellActions)}
      </BackTarget>
    </div>
  );
}
