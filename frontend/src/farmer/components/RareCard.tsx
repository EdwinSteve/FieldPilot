import type { ReactNode } from "react";
import { en } from "../i18n/en";
import type { RareCase } from "../view-models/types";
import { BigLink } from "./BigButton";
import { Icon } from "./Icon";
import { IconCircle, type CircleTone } from "./IconCircle";

interface FrameProps {
  border: string;
  tone: CircleTone;
  icon: ReactNode;
  title: string;
  detail: string;
  children: ReactNode;
}

function Frame({ border, tone, icon, title, detail, children }: FrameProps) {
  return (
    <section className={`flex flex-col gap-3.5 rounded-card bg-surface p-4.5 ${border}`}>
      <div className="flex items-center gap-3.5">
        <IconCircle tone={tone} size="large">
          {icon}
        </IconCircle>
        <div className="flex flex-1 flex-col gap-0.5">
          <span className="text-row font-extrabold">{title}</span>
          <span className="text-small text-ink-2">{detail}</span>
        </div>
      </div>
      {children}
    </section>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <span className="text-caption leading-snug text-ink-3">{children}</span>;
}

/** The things that go wrong rarely, each with what the farmer needs to know. */
export function RareCard({ item }: { item: RareCase }) {
  switch (item.kind) {
    case "recheck":
      return (
        <Frame
          border="border-[2.5px] border-needs"
          tone="needs"
          icon={<Icon name="cloudRain" size={28} strokeWidth={2} />}
          title={item.title}
          detail={item.detail}
        >
          <Note>{item.note}</Note>
        </Frame>
      );
    case "cut_off":
      return (
        <Frame
          border="border-[2.5px] border-stop"
          tone="stop"
          icon={<Icon name="warning" size={28} />}
          title={item.title}
          detail={item.detail}
        >
          <Note>{item.note}</Note>
          <div className="flex items-center gap-2.5 rounded-chip bg-ground px-3.5 py-3">
            <Icon name="check" size={22} strokeWidth={2.6} className="text-primary" />
            <span className="text-small font-bold">{en.updates.rare.valveClosed}</span>
          </div>
          <BigLink variant="outline" size="compact" href={item.zoneHref}>
            {item.action}
          </BigLink>
        </Frame>
      );
    case "too_late":
      return (
        <Frame
          border=""
          tone="neutral"
          icon={<Icon name="hourglass" size={28} strokeWidth={2} />}
          title={item.title}
          detail={item.detail}
        >
          <button
            type="button"
            disabled
            className="flex min-h-16 cursor-not-allowed items-center justify-center gap-2.5 rounded-control bg-divider text-row font-extrabold text-ink-3"
          >
            <Icon name="lock" size={22} strokeWidth={2.4} />
            {en.updates.rare.undoClosed}
          </button>
        </Frame>
      );
  }
}
