import { useState, type ReactNode } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type FarmPlot } from "../api/lifecycle";
import { BackLink } from "../components/BackHeader";
import { BigButton } from "../components/BigButton";
import { Choices } from "../components/Choices";
import { Icon, type IconName } from "../components/Icon";
import { Sheet } from "../components/Sheet";
import { useLook } from "../hooks/useLook";
import { en } from "../i18n/en";
import type { Farmer } from "../lib/account";
import { hectaresText } from "../lib/farmOutline";
import { TEXT_SIZES, THEMES, type ThemeChoice } from "../lib/look";
import { farmLabel } from "../lib/names";
import { mobileDisplay } from "../lib/typing";

const loadPolicy = () => lifecycle.privacyPolicy();

const THEME_ICONS: Record<ThemeChoice, IconName> = { phone: "phone", light: "sun", dark: "moon" };

/** The sign-out buttons: tinted, each in its own colour. */
const SIGN_OUT =
  "press flex min-h-16 items-center justify-center gap-2.5 rounded-control border-2 px-4 text-row font-extrabold disabled:cursor-not-allowed disabled:opacity-60";

/** Static class names, so Tailwind finds them. */
const STAGGER = [
  "",
  "[animation-delay:50ms]",
  "[animation-delay:100ms]",
  "[animation-delay:150ms]",
  "[animation-delay:200ms]",
];

function Section({
  title,
  icon,
  order,
  children,
}: {
  title: string;
  /** Each card's own picture, so the cards are told apart before the words are read. */
  icon: IconName;
  /** Its place on the page: each card rises in a moment after the one above. */
  order: number;
  children: ReactNode;
}) {
  return (
    <section
      className={`flex shrink-0 animate-screen-in flex-col gap-3 rounded-card bg-surface p-4.5 ${STAGGER[order] ?? ""}`}
    >
      <h2 className="flex items-center gap-2.5 text-lead font-extrabold">
        <Icon name={icon} size={24} className="shrink-0" />
        {title}
      </h2>
      {children}
    </section>
  );
}

function Question({ label, children }: { label: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-2 border-0 p-0">
      <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{label}</legend>
      {children}
    </fieldset>
  );
}

function YouSection({ farmer, plot }: { farmer: Farmer; plot: FarmPlot | null }) {
  const place =
    plot?.municipality && plot.department ? en.settings.farmPlace(plot.municipality, plot.department) : null;
  return (
    <Section title={en.settings.you} icon="user" order={0}>
      <div className="flex items-center gap-3.5">
        <span
          aria-hidden="true"
          className="flex size-14 shrink-0 items-center justify-center rounded-full bg-tint text-head font-extrabold text-primary-hover"
        >
          {farmer.name.trim().charAt(0).toUpperCase()}
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="text-row font-extrabold break-words">{farmer.name}</span>
          <span className="flex items-center gap-1.5 text-body text-ink-2">
            <Icon name="call" size={18} className="shrink-0 text-ink-3" />
            {en.settings.phone(mobileDisplay(farmer.phone.replace(/^\+57/, "")))}
          </span>
        </div>
      </div>
      {plot === null ? null : (
        <div className="flex gap-3 rounded-control bg-ground px-4 py-3">
          <Icon name="home" size={24} className="mt-0.5 shrink-0 text-primary" />
          <div className="flex min-w-0 flex-col">
            <span className="text-body font-bold">{farmLabel(plot.name)}</span>
            {place === null ? null : (
              <span className="flex items-center gap-1.5 text-small text-ink-2">
                <Icon name="pin" size={16} className="shrink-0 text-ink-3" />
                {place}
              </span>
            )}
            <span className="flex items-center gap-1.5 text-small text-ink-2">
              <Icon name="field" size={16} className="shrink-0 text-ink-3" />
              {en.settings.farmSize(hectaresText(plot.area_ha))}
            </span>
          </div>
        </div>
      )}
      <p className="flex items-start gap-1.5 px-0.5 text-small text-ink-3">
        <Icon name="info" size={18} className="mt-0.5 shrink-0" />
        {en.settings.readOnly}
      </p>
    </Section>
  );
}

function LookSection() {
  const [look, setLook] = useLook();
  return (
    <Section title={en.settings.look} icon="eye" order={1}>
      <Question label={en.settings.theme}>
        <Choices
          options={THEMES}
          chosen={look.theme}
          label={(theme) => en.settings.themes[theme]}
          icon={(theme) => THEME_ICONS[theme]}
          onChoose={(theme) => setLook({ ...look, theme })}
        />
      </Question>
      <Question label={en.settings.textSize}>
        <Choices
          options={TEXT_SIZES}
          chosen={look.text}
          label={(size) => en.settings.textSizes[size]}
          labelClass={(size) => (size === "large" ? "text-key" : "")}
          onChoose={(text) => setLook({ ...look, text })}
        />
        <p className="mt-1 rounded-control bg-ground px-4 py-3 text-body text-ink-2">{en.settings.textSample}</p>
      </Question>
    </Section>
  );
}

function PrivacySection() {
  const policy = useResource(loadPolicy, 0).data;
  return (
    <Section title={en.settings.privacy} icon="shield" order={2}>
      <p className="px-0.5 text-body text-ink-2">{en.settings.agreed}</p>
      <blockquote className="m-0 flex gap-3 rounded-control bg-ground px-4 py-3 text-body">
        <Icon name="shield" size={24} className="mt-0.5 shrink-0 text-primary" />
        {en.auth.consent}
      </blockquote>
      {policy === null ? null : (
        <p className="flex animate-fade-in items-center gap-1.5 px-0.5 text-small text-ink-3">
          <Icon name="document" size={18} className="shrink-0" />
          {en.settings.policyVersion(policy.version)}
        </p>
      )}
    </Section>
  );
}

function EverywhereSheet({ onConfirm, onClose }: { onConfirm: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const confirm = async () => {
    setBusy(true);
    setFailed(false);
    try {
      await onConfirm();
    } catch {
      setFailed(true);
      setBusy(false);
    }
  };
  return (
    <Sheet label={en.settings.everywhereTitle} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{en.settings.everywhereTitle}</h2>
      <p className="text-body text-ink-2">{en.settings.everywhereDetail}</p>
      {failed ? (
        <p role="alert" className="animate-card-in rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {en.settings.everywhereFailed}
        </p>
      ) : null}
      <button
        type="button"
        disabled={busy}
        onClick={() => void confirm()}
        className={`${SIGN_OUT} border-bad bg-bad-tint text-bad-text`}
      >
        <Icon name="phone" size={24} />
        {busy ? en.settings.everywhereBusy : en.settings.everywhereConfirm}
      </button>
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.settings.cancel}
      </BigButton>
    </Sheet>
  );
}

interface SettingsScreenProps {
  farmer: Farmer;
  /** The farm, once it is set up. */
  plot: FarmPlot | null;
  onSignOut: () => void;
  onSignOutEverywhere: () => Promise<void>;
}

/** Who is signed in, how the app looks on this phone, how the farmer counts a harvest, and signing out. */
export function SettingsScreen({ farmer, plot, onSignOut, onSignOutEverywhere }: SettingsScreenProps) {
  const [everywhere, setEverywhere] = useState(false);
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-5 pb-6">
      <header className="flex animate-screen-in items-center gap-3">
        <BackLink />
        <h1 className="text-title font-extrabold tracking-title">{en.settings.title}</h1>
      </header>
      <YouSection farmer={farmer} plot={plot} />
      <LookSection />
      <PrivacySection />
      <Section title={en.settings.account} icon="lock" order={3}>
        <p className="-mt-1 px-0.5 text-small text-ink-2">{en.settings.signOutHint}</p>
        {/* Blue: you can log in again any time. Red: it reaches every phone. Solid red stays Stop's. */}
        <button type="button" onClick={onSignOut} className={`${SIGN_OUT} border-undo bg-undo-tint text-undo-text`}>
          <Icon name="logOut" size={24} />
          {en.auth.signOut}
        </button>
        <button
          type="button"
          onClick={() => setEverywhere(true)}
          className={`${SIGN_OUT} border-bad bg-bad-tint text-bad-text`}
        >
          <Icon name="phone" size={24} />
          {en.settings.signOutEverywhere}
        </button>
      </Section>
      {everywhere ? (
        <EverywhereSheet onConfirm={onSignOutEverywhere} onClose={() => setEverywhere(false)} />
      ) : null}
    </main>
  );
}
