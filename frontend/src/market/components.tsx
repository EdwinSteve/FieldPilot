// The marketplace's building blocks: the product card, the price split, the kilo stepper and the journey.
import { CropArt } from "../farmer/components/CropArt";
import { Icon, type IconName } from "../farmer/components/Icon";
import { formatCalendarDate } from "../farmer/lib/farmTime";
import { kgText } from "../farmer/lib/harvest";
import { cop } from "../farmer/lib/listing";
import { cropLabel } from "../farmer/lib/names";
import type { JourneyStep, Passport, Price, Product, Reason } from "./api/store";
import { en } from "./i18n/en";
import { hrefOf } from "./lib/route";
import { priceSplit } from "./lib/shop";

export function ReasonTag({ reason }: { reason: Reason }) {
  const offer = reason === "ON_OFFER";
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

export function ProductCard({ product, reasons }: { product: Product; reasons?: Reason[] }) {
  return (
    <a
      href={hrefOf({ screen: "product", id: product.id })}
      className="press group flex flex-col gap-3 rounded-card bg-surface p-4 text-ink no-underline shadow-[0_1px_0_var(--color-border)] transition-shadow hover:shadow-[0_12px_30px_rgba(21,39,40,0.12)]"
    >
      <div className="relative flex h-36 items-center justify-center rounded-tile bg-tint">
        <span className="transition-transform duration-300 group-hover:scale-110">
          <CropArt crop={product.crop} size={92} />
        </span>
        {product.offer === null ? null : (
          <span className="absolute top-2.5 left-2.5 rounded-pill bg-needs px-2.5 py-1 text-caption font-extrabold text-surface">
            −{product.offer.discount_pct}%
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
export function PriceSplit({ price }: { price: Price }) {
  const split = priceSplit(price);
  const rows: [string, number, number, string][] = [
    [en.product.toFarmer, price.farmer_cop, split.farmer, "bg-primary"],
    [en.product.toTransport, price.logistics_cop, split.logistics, "bg-earth"],
    [en.product.toPlatform, price.platform_cop, split.platform, "bg-undo"],
  ];
  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
      <h2 className="text-lead font-extrabold">{en.product.split}</h2>
      {rows.map(([label, amount, part, color]) => (
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
      ))}
    </section>
  );
}

export function KgStepper({ kg, max, onChange }: { kg: number; max: number; onChange: (kg: number) => void }) {
  const button =
    "press flex size-12 items-center justify-center rounded-control border-2 border-border bg-surface text-ink disabled:opacity-40";
  return (
    <div className="flex items-center gap-2">
      <button type="button" aria-label={en.product.less} disabled={kg <= 1} onClick={() => onChange(kg - 1)} className={button}>
        <span className="text-head font-extrabold leading-none">−</span>
      </button>
      <label className="flex flex-col items-center">
        <span className="sr-only">{en.product.kg}</span>
        <input
          inputMode="numeric"
          value={kg}
          onChange={(event) => onChange(Number(event.target.value.replace(/\D/g, "")) || 0)}
          className="h-12 w-20 rounded-control border-2 border-border bg-surface text-center text-row font-extrabold text-ink"
        />
      </label>
      <button type="button" aria-label={en.product.more} disabled={kg >= max} onClick={() => onChange(kg + 1)} className={button}>
        <Icon name="plus" size={22} strokeWidth={2.8} />
      </button>
      <span className="text-body font-bold text-ink-2">kg</span>
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
