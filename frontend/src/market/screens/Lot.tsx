import { useCallback } from "react";
import { useResource } from "../../hooks/useResource";
import { CropArt } from "../../farmer/components/CropArt";
import { Icon, type IconName } from "../../farmer/components/Icon";
import { formatCalendarDate } from "../../farmer/lib/farmTime";
import { kgText } from "../../farmer/lib/harvest";
import { cropLabel } from "../../farmer/lib/names";
import { store, type Passport } from "../api/store";
import { Empty, Journey, Verified } from "../components";
import { en } from "../i18n/en";

function Fact({ icon, label, value }: { icon: IconName; label: string; value: string }) {
  return (
    <div className="flex gap-3 rounded-control bg-ground px-4 py-3">
      <Icon name={icon} size={22} className="mt-0.5 shrink-0 text-primary" />
      <div className="flex flex-col">
        <span className="text-small font-bold text-ink-3">{label}</span>
        <span className="text-body font-bold">{value}</span>
      </div>
    </div>
  );
}

function growing(passport: Passport): string {
  const c = passport.cultivation;
  if (c.data_source === "declared") return en.passport.declared;
  if (c.irrigation_mm_total === null || c.irrigation_events === null) return en.passport.measuredNone;
  return en.passport.measured(Math.round(c.irrigation_mm_total), c.irrigation_events);
}

function plan(passport: Passport): string {
  const p = passport.plan;
  if (!p.known) return en.passport.planUnknown;
  if (p.own_risk || p.rank === null || p.predicted_p_success === null) return en.passport.ownRisk;
  return en.passport.planKnown(p.rank, Math.round(p.predicted_p_success * 10));
}

/** The public passport a product's QR opens (§7): where the food came from, never who or what it cost. */
export function LotPage({ code }: { code: string }) {
  const passport = useResource(
    useCallback(() => store.passport(code), [code]),
    0,
  );
  if (passport.data === null) {
    return passport.error === null ? <p className="text-body text-ink-2">{en.state.loading}</p> : <Empty icon="document" title={en.passport.notFound} />;
  }
  const p = passport.data;
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-[1fr_1.1fr]">
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-5 rounded-[32px] bg-tint p-6">
          <CropArt crop={p.crop} size={96} />
          <div className="flex flex-col gap-1">
            <span className="text-small font-extrabold tracking-[0.14em] text-primary">{en.passport.title.toUpperCase()}</span>
            <h1 className="text-title font-extrabold tracking-title">{cropLabel(p.crop)}</h1>
            <span className="font-mono text-small text-ink-2">{p.lot_code}</span>
          </div>
        </div>
        <Verified verified={p.integrity.verified} />
        <div className="grid gap-2 sm:grid-cols-2">
          <Fact icon="home" label={en.passport.farm} value={`${p.municipality}, ${p.department} · ${en.passport.area(String(p.area_ha))}`} />
          <Fact icon="calendar" label={en.passport.sown} value={formatCalendarDate(p.sowing_date)} />
          <Fact icon="check" label={en.passport.harvested} value={formatCalendarDate(p.harvested_on)} />
          <Fact icon="bag" label={en.passport.quantity} value={`${kgText(p.quantity_kg)} kg · ${en.passport.grade[p.grade]}`} />
        </div>
        <section className="flex flex-col gap-2 rounded-card bg-surface p-5">
          <h2 className="text-lead font-extrabold">{en.passport.growing}</h2>
          <p className="flex items-start gap-2 text-body">
            <Icon name="drop" size={20} className="mt-0.5 shrink-0 text-undo" />
            {growing(p)}
          </p>
          <p className="text-small text-ink-2">{en.passport.inputs(p.cultivation.inputs_applied.length)}</p>
          <h2 className="mt-2 text-lead font-extrabold">{en.passport.planTitle}</h2>
          <p className="flex items-start gap-2 text-body">
            <Icon name="shield" size={20} className="mt-0.5 shrink-0 text-primary" />
            {plan(p)}
          </p>
        </section>
      </div>
      <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
        <h2 className="text-lead font-extrabold">{en.passport.journey}</h2>
        <Journey passport={p} />
        <p className="text-small text-ink-3">{en.passport.privacy}</p>
      </section>
    </div>
  );
}
