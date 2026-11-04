// The marketplace's building blocks: the product card, the price split, the kilo stepper and the journey.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { BigButton } from "../farmer/components/BigButton";
import { TextField } from "../farmer/components/TextField";
import { CropArt } from "../farmer/components/CropArt";
import { Icon, type IconName } from "../farmer/components/Icon";
import { formatCalendarDate } from "../farmer/lib/farmTime";
import { kgText } from "../farmer/lib/harvest";
import { cop } from "../farmer/lib/listing";
import { cropLabel } from "../farmer/lib/names";
import type { JourneyStep, Passport, Price, Product, Reason } from "./api/store";
import { en } from "./i18n/en";
import { hrefOf } from "./lib/route";
import { addressProblem, isClearance, kgFromText, kgProblem, priceSplit } from "./lib/shop";
import { dismissToast, useToast } from "./state";

export function ReasonTag({ reason }: { reason: Reason }) {
  const offer = reason === "ON_OFFER" || reason === "DEAL_FOR_YOU";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-pill px-2.5 py-1 text-caption font-bold ${
        offer ? "bg-needs-tint text-needs-text" : "bg-tint text-primary-hover"
      }`}
    >
      <Icon name={offer ? "bag" : reason === "FRESH_HARVEST" ? "check" : "plus"} size={14} strokeWidth={2.6} />
      {en.reasons[reason]}
    </span>
  );
}

/** The share bar under every price: the green part is what the farmer keeps. */
export function ShareBar({ price }: { price: Price }) {
  const split = priceSplit(price);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex h-2 w-full overflow-hidden rounded-pill bg-divider" aria-hidden="true">
        <span className="bg-primary" style={{ width: `${split.farmer * 100}%` }} />
        <span className="bg-earth" style={{ width: `${split.logistics * 100}%` }} />
        <span className="bg-undo" style={{ width: `${split.platform * 100}%` }} />
      </div>
      <span className="text-caption font-bold text-primary-hover">{en.product.farmerKeeps(String(price.farmer_share_pct))}</span>
    </div>
  );
}

/** The longest wait before a card of a grid comes in, so a long list never feels slow. */
const MAX_STAGGER_MS = 320;

/** `index` is the card's place in its grid: the cards come in one after another. */
export function ProductCard({ product, reasons, index = 0 }: { product: Product; reasons?: Reason[]; index?: number }) {
  return (
    <a
      href={hrefOf({ screen: "product", id: product.id })}
      style={{ animationDelay: `${Math.min(index * 40, MAX_STAGGER_MS)}ms` }}
      className="press group flex animate-screen-in flex-col gap-3 rounded-card bg-surface p-4 text-ink no-underline shadow-[0_1px_0_var(--color-border)] transition-[box-shadow,translate] duration-200 hover:-translate-y-1 hover:shadow-[0_12px_30px_rgba(21,39,40,0.12)]"
    >
      <div className="relative flex h-36 items-center justify-center rounded-tile bg-tint">
        <span className="transition-transform duration-300 group-hover:scale-110">
          <CropArt crop={product.crop} size={92} />
        </span>
        {product.offer === null ? null : (
          <span className="absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-pill bg-needs px-2.5 py-1 text-caption font-extrabold text-surface">
            {isClearance(product) ? (
              <>
                <Icon name="clock" size={14} strokeWidth={2.6} />
                {en.product.clearanceBadge(product.offer.discount_pct, product.days_left ?? null)}
              </>
            ) : (
              `−${product.offer.discount_pct}%`
            )}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-0.5">
        <h3 className="text-row font-extrabold">{cropLabel(product.crop)}</h3>
        <span className="text-small text-ink-2">{product.producer}</span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-head font-extrabold tracking-key">{cop(product.price.total_cop)}</span>
        <span className="text-small text-ink-3">{en.product.perKg}</span>
      </div>
      <ShareBar price={product.price} />
      <div className="flex flex-wrap gap-1.5">
        {(reasons ?? []).map((reason) => (
          <ReasonTag key={reason} reason={reason} />
        ))}
        <span className="inline-flex items-center rounded-pill bg-ground px-2.5 py-1 text-caption font-semibold text-ink-2">
          {en.product.harvested(formatCalendarDate(product.harvested_on))}
        </span>
      </div>
    </a>
  );
}

/** Where a shopper's money goes, in three labelled parts. */
export function PriceSplit({ price, bare = false }: { price: Price; bare?: boolean }) {
  const split = priceSplit(price);
  const rows: [string, number, number, string][] = [
    [en.product.toFarmer, price.farmer_cop, split.farmer, "bg-primary"],
    [en.product.toTransport, price.logistics_cop, split.logistics, "bg-earth"],
    [en.product.toPlatform, price.platform_cop, split.platform, "bg-undo"],
  ];
  const bars = rows.map(([label, amount, part, color]) => (
    <div key={label} className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-body font-bold">{label}</span>
        <span className="text-body font-extrabold">
          {cop(amount)} <span className="text-small font-semibold text-ink-3">· {Math.round(part * 100)}%</span>
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-pill bg-divider">
        <div className={`h-full rounded-pill ${color}`} style={{ width: `${part * 100}%` }} />
      </div>
    </div>
  ));
  if (bare) return <div className="flex flex-col gap-3">{bars}</div>;
  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
      <h2 className="text-lead font-extrabold">{en.product.split}</h2>
      {bars}
    </section>
  );
}

/** Whole kilos, at most `max`. The box may be empty (null) while the shopper types; the screen asks for a number. */
export function KgStepper({
  kg,
  max,
  onChange,
  of,
}: {
  kg: number | null;
  max: number;
  onChange: (kg: number | null) => void;
  /** The stock, said beside the kilos: "of 125 kg". */
  of?: number;
}) {
  const button =
    "press flex size-12 items-center justify-center rounded-control border-2 border-border bg-surface text-ink disabled:opacity-40";
  const missing = kgProblem(kg) !== null;
  return (
    <div className="flex items-center gap-2">
      <button type="button" aria-label={en.product.less} disabled={kg === null || kg <= 1} onClick={() => onChange((kg ?? 2) - 1)} className={button}>
        <span className="text-head font-extrabold leading-none">−</span>
      </button>
      <label className="flex flex-col items-center">
        <span className="sr-only">{en.product.kg}</span>
        <input
          inputMode="numeric"
          value={kg ?? ""}
          placeholder="0"
          aria-invalid={missing}
          onChange={(event) => onChange(kgFromText(event.target.value, max))}
          className={`h-12 w-20 rounded-control border-2 bg-surface text-center text-row font-extrabold text-ink placeholder:text-ink-3 ${
            missing ? "border-bad" : "border-border"
          }`}
        />
      </label>
      <button type="button" aria-label={en.product.more} disabled={kg !== null && kg >= max} onClick={() => onChange(Math.min(max, (kg ?? 0) + 1))} className={button}>
        <Icon name="plus" size={22} strokeWidth={2.8} />
      </button>
      <span className="flex flex-col leading-tight">
        <span className="text-body font-bold text-ink-2">kg</span>
        {of === undefined ? null : (
          <span className="text-caption font-semibold whitespace-nowrap text-ink-3">{en.product.ofKg(kgText(of))}</span>
        )}
      </span>
    </div>
  );
}

const STEP_ICON: Record<JourneyStep, IconName> = {
  commissioning: "check",
  shipping: "arrowRight",
  receiving: "home",
  retail_selling: "bag",
};

/** The lot's journey as a timeline, newest step last. */
export function Journey({ passport }: { passport: Passport }) {
  const steps = passport.journey;
  return (
    <ol className="flex flex-col">
      {steps.map((step, i) => (
        <li key={i} className="flex gap-3.5">
          <div className="flex flex-col items-center">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-tint text-primary">
              <Icon name={STEP_ICON[step.step]} size={20} strokeWidth={2.4} />
            </span>
            {i < steps.length - 1 ? <span className="w-0.5 flex-1 bg-border" /> : null}
          </div>
          <div className="flex flex-col pb-4">
            <span className="text-body font-extrabold">{en.passport.steps[step.step]}</span>
            <span className="text-small text-ink-2">
              {formatCalendarDate(step.on)} · {en.passport.kg(kgText(step.quantity_kg))}
              {step.place === null ? "" : ` · ${step.place}`}
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Verified({ verified }: { verified: boolean }) {
  return (
    <p
      className={`flex items-center gap-2 rounded-control px-4 py-3 text-body font-bold ${
        verified ? "bg-tint text-primary-hover" : "bg-bad-tint text-bad-text"
      }`}
    >
      <Icon name={verified ? "shield" : "warning"} size={22} className="shrink-0" />
      {verified ? en.passport.verified : en.passport.broken}
    </p>
  );
}

/**
 * A section that opens in place: the button says what is inside and the chevron turns.
 * Closed, the content is `inert`, so neither a tap nor a screen reader reaches it.
 */
export function Disclosure({
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  title: string;
  /** One line shown under the title while closed, so the shopper knows what is inside. */
  summary?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <section className="flex flex-col rounded-card bg-surface">
      <h2 className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((current) => !current)}
          className="press flex min-h-16 w-full items-center gap-3 rounded-card border-0 bg-transparent px-5 py-3 text-left text-ink"
        >
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="text-lead font-extrabold">{title}</span>
            {summary === undefined ? null : (
              <span className={`text-small text-ink-2 transition-opacity duration-200 ${open ? "opacity-0" : "opacity-100"}`}>{summary}</span>
            )}
          </span>
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-tint text-primary">
            <Icon
              name="chevronDown"
              size={22}
              strokeWidth={2.6}
              className={`transition-transform duration-300 ease-(--ease-calm) ${open ? "rotate-180" : ""}`}
            />
          </span>
        </button>
      </h2>
      <div
        id={id}
        inert={!open}
        className={`grid transition-[grid-template-rows,opacity,visibility] duration-300 ease-(--ease-calm) ${
          open ? "grid-rows-[1fr] opacity-100" : "invisible grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="flex flex-col gap-3 px-5 pb-5">{children}</div>
        </div>
      </div>
    </section>
  );
}

interface AddressFieldProps {
  label: string;
  hint: string;
  /** The address in use: shown as text with a Change button; empty opens the box at once. */
  saved: string;
  confirmLabel: string;
  changeLabel: string;
  /** Takes the typed address; false keeps the box open, as when a save failed. */
  onConfirm: (address: string) => boolean | Promise<boolean>;
  /** The text being typed, or null while the address shows as text. */
  onDraft?: (draft: string | null) => void;
  /** Say what is missing even before the shopper presses the button, as after Pay. */
  showProblem?: boolean;
  busy?: boolean;
}

/**
 * An address that is kept unless the shopper asks to change it. Enter in the box confirms it,
 * checks included; Cancel puts the saved one back. Nothing here pays or orders.
 */
export function AddressField({
  label,
  hint,
  saved,
  confirmLabel,
  changeLabel,
  onConfirm,
  onDraft,
  showProblem = false,
  busy = false,
}: AddressFieldProps) {
  const [draft, setDraft] = useState<string | null>(() => (saved.trim() === "" ? saved : null));
  const [tried, setTried] = useState(false);
  const box = useRef<HTMLInputElement>(null);
  /** Set by Change, so the box takes focus only when the shopper opened it. */
  const opened = useRef(false);
  useEffect(() => {
    if (draft !== null && opened.current) {
      opened.current = false;
      box.current?.focus();
    }
  }, [draft]);
  const set = (next: string | null) => {
    setDraft(next);
    onDraft?.(next);
  };

  if (draft === null) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-body font-bold">{label}</span>
        <div className="flex animate-fade-in items-center gap-3 rounded-control bg-ground py-1.5 pr-1.5 pl-4">
          <Icon name="pin" size={20} className="shrink-0 text-primary" />
          <span className="flex-1 text-body leading-snug">{saved}</span>
          <button
            type="button"
            onClick={() => {
              opened.current = true;
              setTried(false);
              set(saved);
            }}
            className="press flex min-h-12 shrink-0 items-center rounded-control border-2 border-border bg-surface px-4 text-small font-extrabold text-ink"
          >
            {changeLabel}
          </button>
        </div>
      </div>
    );
  }

  const problem = addressProblem(draft);
  const confirm = async () => {
    setTried(true);
    if (problem !== null) return;
    if (await onConfirm(draft.trim())) set(null);
  };
  return (
    <form
      noValidate
      className="flex animate-fade-in flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void confirm();
      }}
    >
      <TextField
        ref={box}
        label={label}
        hint={hint}
        value={draft}
        onChange={set}
        problem={(tried || showProblem) && problem !== null ? en.cart.addressProblem : null}
        autoComplete="street-address"
      />
      <div className="flex gap-2">
        <BigButton type="submit" variant="outline" size="compact" disabled={busy}>
          <span className="px-3">{confirmLabel}</span>
        </BigButton>
        {saved.trim() === "" ? null : (
          <BigButton variant="outline" size="compact" onClick={() => set(null)}>
            <span className="px-3">{en.account.cancelChange}</span>
          </BigButton>
        )}
      </div>
    </form>
  );
}

export function Notice({ text, tone = "needs" }: { text: string; tone?: "needs" | "good" }) {
  return (
    <p
      role={tone === "needs" ? "alert" : "status"}
      className={`rounded-control px-4 py-3 text-small font-bold ${
        tone === "needs" ? "bg-needs-tint text-needs-text" : "bg-tint text-primary-hover"
      }`}
    >
      {text}
    </p>
  );
}

/** The one toast of the page, above the phone's bottom bar; read out when it appears. */
export function ToastRegion() {
  const toast = useToast();
  return (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-24 z-40 flex justify-center px-4 md:bottom-6">
      {toast === null ? null : (
        <div
          key={toast.id}
          role={toast.tone === "needs" ? "alert" : "status"}
          className={`pointer-events-auto flex w-full max-w-md animate-sheet-up items-start gap-3 rounded-card py-2 pr-2 pl-4 shadow-[0_12px_40px_rgba(21,39,40,0.22)] ${
            toast.tone === "good" ? "bg-ink text-surface" : "bg-needs-tint text-needs-text"
          }`}
        >
          <Icon name={toast.tone === "good" ? "check" : "warning"} size={22} strokeWidth={2.6} className="mt-3 shrink-0" />
          <div className="flex min-w-0 flex-1 flex-col items-start">
            <span className="py-2.5 text-body font-bold leading-snug">{toast.text}</span>
            {toast.action === undefined ? null : "href" in toast.action ? (
              <a
                href={toast.action.href}
                onClick={dismissToast}
                className="press -mt-1 -ml-1 flex min-h-12 items-center rounded-control px-1 text-body font-extrabold text-inherit underline underline-offset-4"
              >
                {toast.action.label}
              </a>
            ) : (
              <button
                type="button"
                onClick={() => {
                  const run = (toast.action as { run: () => void }).run;
                  dismissToast();
                  run();
                }}
                className="press -mt-1 -ml-1 flex min-h-12 items-center rounded-control border-0 bg-transparent px-1 text-body font-extrabold text-inherit underline underline-offset-4"
              >
                {toast.action.label}
              </button>
            )}
          </div>
          <button
            type="button"
            aria-label={en.toast.close}
            onClick={dismissToast}
            className="press flex size-12 shrink-0 items-center justify-center rounded-control border-0 bg-transparent text-inherit"
          >
            <Icon name="close" size={20} strokeWidth={2.6} />
          </button>
        </div>
      )}
    </div>
  );
}

export function Empty({ icon, title, detail, children }: { icon: IconName; title: string; detail?: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card bg-surface px-6 py-12 text-center">
      <span className="flex size-16 items-center justify-center rounded-full bg-tint text-primary">
        <Icon name={icon} size={32} />
      </span>
      <h2 className="text-head font-extrabold">{title}</h2>
      {detail === undefined ? null : <p className="max-w-md text-body text-ink-2">{detail}</p>}
      {children}
    </div>
  );
}
