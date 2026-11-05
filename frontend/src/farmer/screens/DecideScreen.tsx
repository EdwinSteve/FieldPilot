import { useRef, useState } from "react";
import { BackLink } from "../components/BackHeader";
import { BigButton, BigLink } from "../components/BigButton";
import { Chip } from "../components/Chip";
import { Icon, PlantIcon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { LEVEL_TEXT } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { RainLevelIcon } from "../components/RainLevelIcon";
import { useFocusHeading } from "../hooks/useFocusHeading";
import { en } from "../i18n/en";
import type { ApprovalOutcome } from "../lib/approvalOutcome";
import { hrefOf } from "../lib/route";
import { soilStatus } from "../lib/soilStatus";
import { soilLevel } from "../lib/statusLevel";
import type { Approval, DecisionView, FieldWorkFacts } from "../view-models/types";

type Step =
  | { name: "ask" }
  | { name: "reason" }
  | { name: "other" }
  | { name: "done"; answer: "yes"; outcome: ApprovalOutcome; undoUntil: string | null }
  | { name: "done"; answer: "no"; withReason: boolean }
  /** No signal: the answer waits on the phone. */
  | { name: "done"; answer: "saved" };

function doneCopy(step: Extract<Step, { name: "done" }>, view: DecisionView) {
  if (step.answer === "saved") {
    return {
      title: en.outbox.savedTitle,
      detail: en.outbox.savedDetail,
      icon: "cloudOff" as const,
      tone: "undo" as const,
    };
  }
  if (step.answer === "no") {
    return {
      title: view.work === null ? en.decide.noWater : en.fieldWork.noTitle,
      detail: step.withReason ? en.decide.noWaterSaved : en.decide.noWaterSkipped,
      icon: "check" as const,
      tone: "neutral" as const,
    };
  }
  if (view.work !== null) {
    return {
      title: en.fieldWork.yesTitle,
      detail: en.fieldWork.yesDetail,
      icon: "check" as const,
      tone: "good" as const,
    };
  }
  switch (step.outcome) {
    case "running":
      return {
        title: en.decide.wateringNow,
        detail: en.decide.wateringDetail(view.zoneName, view.waterMm),
        icon: "check" as const,
        tone: "good" as const,
      };
    case "planned":
      return {
        title: en.decide.plannedTitle,
        detail: en.decide.plannedDetail(view.zoneName),
        icon: "clock" as const,
        tone: "undo" as const,
      };
    case "not_run":
      return {
        title: en.decide.notRunTitle,
        detail: en.decide.notRunDetail,
        icon: "warning" as const,
        tone: "stop" as const,
      };
  }
}

function FactRow({
  icon,
  label,
  note,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  note?: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3.5 border-b border-divider py-3.5 last:border-b-0">
      {icon}
      <span className="flex flex-1 flex-col">
        <span className="text-lead font-semibold">{label}</span>
        {note === undefined ? null : <span className="text-caption text-ink-2">{note}</span>}
      </span>
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
          {view.work === null ? (
            <Icon name="dropRipple" size={66} strokeWidth={1.6} />
          ) : (
            <PlantIcon size={66} />
          )}
        </IconCircle>
        <h1 className="text-center text-title font-extrabold tracking-title">{view.question}</h1>
        <span className="text-center text-lead leading-snug text-ink-2">{view.why}</span>
      </div>
      {view.work !== null ? (
        <FieldWorkFactsCard work={view.work} />
      ) : (
      <div className="rounded-card bg-surface px-5 py-1.5">
        <FactRow
          icon={<MoistureDrop {...view.soil} size={34} />}
          label={en.decide.soilNow}
          note={view.percentFull}
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
      )}
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

/** The agronomist's task: what, when and why, in its own words (D093). */
function FieldWorkFactsCard({ work }: { work: FieldWorkFacts }) {
  return (
    <div className="flex flex-col gap-3 rounded-card bg-surface px-5 py-4">
      {work.dose === null ? null : (
        <div className="flex flex-col gap-0.5">
          <span className="text-caption font-semibold text-ink-2">{en.fieldWork.what}</span>
          <span className="text-row font-extrabold">{work.dose}</span>
        </div>
      )}
      <div className="flex flex-col gap-0.5">
        <span className="text-caption font-semibold text-ink-2">{en.fieldWork.when}</span>
        <span className="text-lead font-bold">{work.when}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-caption font-semibold text-ink-2">{en.fieldWork.why}</span>
        <p className="text-body leading-snug">{work.rationale}</p>
      </div>
    </div>
  );
}

function Reason({
  reasons,
  onPick,
  onOther,
}: {
  reasons: readonly string[];
  onPick: (reason?: string) => void;
  onOther: () => void;
}) {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto px-4.5 pt-2 pb-5">
      <h1 className="mx-0.5 text-title-md font-extrabold tracking-title">{en.decide.whyNot}</h1>
      <span className="px-0.5 text-body text-ink-2">{en.decide.pickOne}</span>
      <div className="flex flex-col gap-2.5">
        {reasons.map((reason, index) => (
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
          <span className={REASON_NUMBER}>{reasons.length + 1}</span>
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
  const { title, detail, icon, tone } = doneCopy(step, view);
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4.5 px-4.5 pt-3 pb-5 text-center">
      <span className="animate-pop-in">
        <IconCircle tone={tone} size="hero">
          <Icon name={icon} size={66} strokeWidth={2.4} />
        </IconCircle>
      </span>
      <h1 className="text-title font-extrabold">{title}</h1>
      <span className="text-lead leading-normal text-ink-2">{detail}</span>
      {step.answer === "yes" && step.undoUntil !== null ? (
        <span className="flex items-start gap-2 rounded-control bg-undo-tint px-4 py-3 text-left text-body font-bold text-undo-text">
          <Icon name="undo" size={22} className="mt-0.5 shrink-0" />
          {en.decide.undoUntil(step.undoUntil)}
        </span>
      ) : null}
      <BigLink variant="outline" href={hrefOf({ screen: "today" })}>
        <span className="px-5 text-body font-bold">{en.decide.backToToday}</span>
      </BigLink>
    </main>
  );
}

interface DecideScreenProps {
  view: DecisionView;
  onApprove: (taskId: number) => Promise<Approval | null>;
  onReject: (taskId: number, reason?: string) => Promise<"sent" | "saved" | null>;
  /** Answered without signal: the answer waits on the phone. */
  saved: boolean;
}

export function DecideScreen({ view, onApprove, onReject, saved }: DecideScreenProps) {
  const [step, setStep] = useState<Step>(saved ? { name: "done", answer: "saved" } : { name: "ask" });
  const steps = useRef<HTMLDivElement>(null);
  // Each step is a new question or answer: a screen reader hears its heading.
  useFocusHeading(step.name, steps);

  const approve = () => {
    void onApprove(view.taskId).then((approval) => {
      if (approval === null) return;
      if (approval.outcome === "saved") setStep({ name: "done", answer: "saved" });
      else setStep({ name: "done", answer: "yes", outcome: approval.outcome, undoUntil: approval.undoUntil });
    });
  };
  const reject = (reason?: string) => {
    void onReject(view.taskId, reason).then((result) => {
      if (result === "saved") setStep({ name: "done", answer: "saved" });
      else if (result === "sent") setStep({ name: "done", answer: "no", withReason: reason !== undefined });
    });
  };

  return (
    <>
      <header className="flex items-center gap-3 px-4.5 pt-5 pb-2">
        <BackLink />
        <Chip tone="needs">
          <span className="text-small">{en.autonomy.needsYou}</span>
        </Chip>
      </header>
      <div ref={steps} className="contents">
        {step.name === "ask" && view.open ? (
          <Ask view={view} onYes={approve} onNo={() => setStep({ name: "reason" })} />
        ) : null}
        {step.name === "ask" && !view.open ? <Closed /> : null}
        {step.name === "reason" ? (
          <Reason
            reasons={view.work === null ? en.decide.reasons : en.fieldWork.noReasons}
            onPick={reject}
            onOther={() => setStep({ name: "other" })}
          />
        ) : null}
        {step.name === "other" ? (
          <OtherReason onSave={reject} onBack={() => setStep({ name: "reason" })} />
        ) : null}
        {step.name === "done" ? <Done step={step} view={view} /> : null}
      </div>
    </>
  );
}
