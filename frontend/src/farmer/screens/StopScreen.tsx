import { BackLink } from "../components/BackHeader";
import { BigButton, BigLink } from "../components/BigButton";
import { Icon, StopSign } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { InfoRow } from "../components/InfoRow";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { StopView } from "../view-models/types";

function Confirm({ view, onStop }: { view: StopView; onStop: () => void }) {
  const running = view.runningUntil;
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-4.5 pt-5 pb-6">
      <BackLink href={hrefOf({ screen: "today" })} label={en.back.today} />
      <div className="flex flex-col items-center gap-4.5 pt-3">
        <IconCircle tone="stop" size="stop">
          <StopSign size={76} />
        </IconCircle>
        <h1 className="text-center text-title font-extrabold tracking-title">
          {running === null ? en.stop.title : en.stop.titleWhileRunning}
        </h1>
        <span className="text-center text-lead leading-snug text-ink-2">
          {running === null ? en.stop.explain : en.stop.explainWhileRunning(running)}
        </span>
      </div>
      <div className="rounded-card bg-surface px-5 py-1.5">
        <InfoRow icon={<Icon name="check" size={28} strokeWidth={2.6} className="text-primary" />}>
          {en.stop.keepsAlerts}
        </InfoRow>
        <InfoRow icon={<Icon name="check" size={28} strokeWidth={2.6} className="text-primary" />}>
          {en.stop.keepsValves}
        </InfoRow>
      </div>
      <div className="mt-auto flex flex-col gap-3">
        <BigButton variant="stop" size="extraLarge" onClick={onStop}>
          {en.stop.confirm}
        </BigButton>
        <BigLink variant="outline" href={hrefOf({ screen: "today" })}>
          <span className="text-lead font-bold">{en.stop.cancel}</span>
        </BigLink>
      </div>
    </main>
  );
}

const STOPPED_ROWS: { label: string; allowed: boolean }[] = [
  { label: en.stop.noWatering, allowed: false },
  { label: en.stop.noPlanChanges, allowed: false },
  { label: en.stop.valvesCanClose, allowed: true },
  { label: en.stop.alertsStillOn, allowed: true },
];

function Stopped({ view, onResume }: { view: StopView; onResume: () => void }) {
  const running = view.runningUntil;
  return (
    <>
      <output className="flex items-center gap-3.5 bg-stop px-5 pt-7 pb-5.5 text-surface">
        <StopSign size={44} inverted />
        <div className="flex flex-col gap-0.5">
          <span className="text-head font-extrabold">
            {running === null ? en.stop.stopped : en.stop.stoppedWhileRunning}
          </span>
          <span className="text-small">{view.since}</span>
          {running === null ? null : (
            <span className="text-small font-bold">{en.stop.runningUntil(running)}</span>
          )}
        </div>
      </output>
      <main className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4.5 pt-4.5 pb-5">
        <div className="rounded-card bg-surface px-5 py-1.5">
          {STOPPED_ROWS.map(({ label, allowed }) => (
            <InfoRow
              key={label}
              icon={
                <IconCircle tone={allowed ? "good" : "stop"} size="row">
                  <Icon name={allowed ? "check" : "close"} size={22} strokeWidth={2.8} />
                </IconCircle>
              }
            >
              <span className="text-lead font-bold">{label}</span>
            </InfoRow>
          ))}
        </div>
        <div className="mt-auto flex flex-col">
          <BigButton variant="primary" size="extraLarge" onClick={onResume}>
            <Icon name="play" size={26} />
            {en.stop.startAgain}
          </BigButton>
        </div>
      </main>
    </>
  );
}

interface StopScreenProps {
  view: StopView;
  onStop: () => void;
  onResume: () => void;
}

export function StopScreen({ view, onStop, onResume }: StopScreenProps) {
  return view.stopped ? (
    <Stopped view={view} onResume={onResume} />
  ) : (
    <Confirm view={view} onStop={onStop} />
  );
}
