import { useState } from "react";
import { BackLink } from "../components/BackHeader";
import { BigButton, BigLink } from "../components/BigButton";
import { Chip } from "../components/Chip";
import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { LEVEL_TEXT } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { RainLevelIcon } from "../components/RainLevelIcon";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { soilStatus } from "../lib/soilStatus";
import { soilLevel } from "../lib/statusLevel";
import type { DecisionView } from "../view-models/types";

type Step =
  | { name: "ask" }
  | { name: "reason" }
  | { name: "other" }
  | { name: "done"; answer: "yes" | "no"; withReason: boolean };

function FactRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3.5 border-b border-divider py-3.5 last:border-b-0">
      {icon}
      <span className="flex-1 text-lead font-semibold">{label}</span>
      {value}
    </div>
  );
}

function Ask({
  view,
  onYes,
  onNo,
}: {
  view: DecisionView;
  onYes: () => void;
  onNo: () => void;
}) {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto px-4.5 pt-2 pb-5">
      <div className="flex flex-col items-center gap-3.5 pt-2">
        <IconCircle tone="undo" size="hero">
          <Icon name="dropRipple" size={66} strokeWidth={1.6} />
        </IconCircle>
        <h1 className="text-center text-title font-extrabold tracking-title">{view.question}</h1>
        <span className="text-center text-lead leading-snug text-ink-2">{view.why}</span>
      </div>
      <div className="rounded-card bg-surface px-5 py-1.5">
        <FactRow
          icon={<MoistureDrop {...view.soil} size={34} />}
          label={en.decide.soilNow}
          value={
            <span
              className={`text-row font-extrabold ${
                LEVEL_TEXT[soilLevel(soilStatus(view.soil.value, view.soil.fieldCapacity))]
              }`}
            >
              {view.soil.value}%{" "}
              <span className="text-caption font-semibold text-ink-3">
                {en.soil.of(view.soil.fieldCapacity)}
              </span>
            </span>
          }
        />
        <FactRow
          icon={<RainLevelIcon mm={view.rainMm} size={34} cloudFill="tint" />}
          label={en.decide.rainNext24h}
          value={<span className="text-row font-extrabold text-undo-text">{view.rainMm} mm</span>}
        />
        <FactRow
          icon={<Icon name="waterAdd" size={28} strokeWidth={2} className="text-ink-2" />}
          label={en.decide.waterToAdd}
          value={
            <span className="text-row font-extrabold">
              {view.waterMm === null ? "" : en.rain.amount(view.waterMm)}
            </span>
          }
        />
      </div>
      {view.stopped ? (
        <p className="mt-auto text-center text-body font-bold text-stop">{en.decide.stoppedNote}</p>
      ) : null}
      <div className={`grid grid-cols-2 gap-3 ${view.stopped ? "" : "mt-auto"}`}>
        <BigButton variant="outline" size="large" onClick={onNo}>
          <Icon name="close" strokeWidth={2.8} />
          {en.decide.no}
        </BigButton>
        <BigButton variant="primary" size="large" disabled={view.stopped} onClick={onYes}>
          <Icon name="check" strokeWidth={2.8} />
          {en.decide.yes}
        </BigButton>
      </div>
    </main>
  );
}

const REASON_BUTTON =
  "press flex min-h-17 items-center gap-3.5 rounded-control border-2 border-border bg-surface px-4.5 text-left text-row font-bold text-ink";
const REASON_NUMBER =
  "flex size-10 shrink-0 items-center justify-center rounded-full bg-ground text-lead font-extrabold text-primary";
const MAX_REASON_CHARS = 500;

function Reason({
  onPick,
  onOther,
}: {
  onPick: (reason?: string) => void;
  onOther: () => void;
}) {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto px-4.5 pt-2 pb-5">
      <h1 className="mx-0.5 text-title-md font-extrabold tracking-title">{en.decide.whyNot}</h1>
      <span className="px-0.5 text-body text-ink-2">{en.decide.pickOne}</span>
      <div className="flex flex-col gap-2.5">
        {en.decide.reasons.map((reason, index) => (
          <button
            key={reason}
            type="button"
            onClick={() => onPick(reason)}
            className={REASON_BUTTON}
          >
            <span className={REASON_NUMBER}>{index + 1}</span>
            {reason}
          </button>
        ))}
        <button type="button" onClick={onOther} className={REASON_BUTTON}>
          <span className={REASON_NUMBER}>{en.decide.reasons.length + 1}</span>
          {en.decide.anotherReason}
        </button>
      </div>
      <button
        type="button"
        onClick={() => onPick()}
        className="mt-auto min-h-15 border-0 bg-transparent text-lead font-bold text-ink-2 underline"
      >
        {en.decide.skip}
      </button>
    </main>
  );
}

function OtherReason({
  onSave,
  onBack,
}: {
  onSave: (reason: string) => void;
  onBack: () => void;
}) {
  const [text, setText] = useState("");
  const reason = text.trim();
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto px-4.5 pt-2 pb-5">
      <h1 className="mx-0.5 text-title-md font-extrabold tracking-title">{en.decide.whyNot}</h1>
      <label className="flex flex-col gap-2 px-0.5 text-body font-bold text-ink-2">
        {en.decide.yourReason}
        <textarea
          rows={4}
          value={text}
          maxLength={MAX_REASON_CHARS}
          onChange={(event) => setText(event.target.value)}
          className="resize-none rounded-control border-2 border-border bg-surface p-4 text-body font-normal text-ink"
        />
      </label>
      <div className="mt-auto flex flex-col gap-2">
        <BigButton
          variant="primary"
          size="large"
          disabled={reason === ""}
          onClick={() => onSave(reason)}
        >
          {en.decide.saveReason}
        </BigButton>
        <button
          type="button"
          onClick={onBack}
          className="min-h-15 border-0 bg-transparent text-lead font-bold text-ink-2 underline"
        >
          {en.decide.backToReasons}
        </button>
      </div>
    </main>
  );
}

function Closed() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4.5 px-4.5 pt-3 pb-5 text-center">
      <IconCircle tone="neutral" size="hero">
        <Icon name="check" size={66} strokeWidth={2.4} />
      </IconCircle>
      <h1 className="text-title font-extrabold">{en.decide.closedTitle}</h1>
      <span className="text-lead leading-normal text-ink-2">{en.decide.closedDetail}</span>
    </main>
  );
}

function Done({ step, view }: { step: Extract<Step, { name: "done" }>; view: DecisionView }) {
  const yes = step.answer === "yes";
  const noDetail = step.withReason ? en.decide.noWaterSaved : en.decide.noWaterSkipped;
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4.5 px-4.5 pt-3 pb-5 text-center">
      <span className="animate-pop-in">
        <IconCircle tone={yes ? "good" : "neutral"} size="hero">
          <Icon name="check" size={66} strokeWidth={2.4} />
        </IconCircle>
      </span>
      <h1 className="text-title font-extrabold">
        {yes ? en.decide.wateringNow : en.decide.noWater}
      </h1>
      <span className="text-lead leading-normal text-ink-2">
        {yes ? en.decide.wateringDetail(view.zoneName, view.waterMm) : noDetail}
      </span>
      <BigLink variant="outline" href={hrefOf({ screen: "today" })}>
        <span className="px-5 text-body font-bold">{en.decide.backToToday}</span>
      </BigLink>
    </main>
  );
}

interface DecideScreenProps {
  view: DecisionView;
  onApprove: (taskId: number) => Promise<boolean>;
  onReject: (taskId: number, reason?: string) => Promise<boolean>;
}

export function DecideScreen({ view, onApprove, onReject }: DecideScreenProps) {
  const [step, setStep] = useState<Step>({ name: "ask" });

  const approve = () => {
    void onApprove(view.taskId).then((done) => {
      if (done) setStep({ name: "done", answer: "yes", withReason: false });
    });
  };
  const reject = (reason?: string) => {
    void onReject(view.taskId, reason).then((done) => {
      if (done) setStep({ name: "done", answer: "no", withReason: reason !== undefined });
    });
  };

  return (
    <>
      <header className="flex items-center gap-3 px-4.5 pt-5 pb-2">
        <BackLink href={hrefOf({ screen: "today" })} label={en.back.today} />
        <Chip tone="needs">
          <span className="text-small">{en.autonomy.needsYou}</span>
        </Chip>
      </header>
      {step.name === "ask" && view.open ? (
        <Ask view={view} onYes={approve} onNo={() => setStep({ name: "reason" })} />
      ) : null}
      {step.name === "ask" && !view.open ? <Closed /> : null}
      {step.name === "reason" ? (
        <Reason onPick={reject} onOther={() => setStep({ name: "other" })} />
      ) : null}
      {step.name === "other" ? (
        <OtherReason onSave={reject} onBack={() => setStep({ name: "reason" })} />
      ) : null}
      {step.name === "done" ? <Done step={step} view={view} /> : null}
    </>
  );
}
