import { useCallback, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { Icon } from "../../farmer/components/Icon";
import { store, type Product } from "../api/store";
import { Empty, ProductCard } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { useUser } from "../state";

const loadOffers = () => store.offersToday();
const loadPicks = () => store.recommendations(6);

function Row({ title, lead, children }: { title: string; lead?: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-title-sm font-extrabold tracking-title">{title}</h2>
        {lead === undefined ? null : <p className="text-body text-ink-2">{lead}</p>}
      </div>
      {children}
    </section>
  );
}

const GRID = "grid grid-cols-1 gap-4 min-[480px]:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

export function Shop() {
  const user = useUser();
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState("");
  const products = useResource(
    useCallback(() => store.products(asked.trim() || undefined), [asked]),
    0,
  );
  const offers = useResource(loadOffers, 0).data ?? [];
  const shopper = user?.role === "customer";
  const picks = useResource(shopper ? loadPicks : noPicks, 0).data ?? [];
  const list: Product[] = products.data ?? [];

  return (
    <div className="flex flex-col gap-10">
      <section className="relative overflow-hidden rounded-[32px] bg-primary px-6 py-10 text-surface md:px-12 md:py-14">
        <div className="relative z-10 flex max-w-2xl flex-col gap-4">
          <h1 className="text-[34px] leading-[1.05] font-extrabold tracking-title md:text-[52px]">{en.shop.hero}</h1>
          <p className="text-lead leading-snug opacity-90">{en.shop.heroLead}</p>
          <form
            className="mt-2 flex max-w-xl flex-col gap-2 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault();
              setAsked(query);
            }}
          >
            <label className="flex min-h-14 flex-1 items-center gap-2 rounded-control bg-surface px-4 text-ink">
              <Icon name="search" size={22} className="shrink-0 text-ink-3" />
              <span className="sr-only">{en.shop.search}</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value.slice(0, 60))}
                placeholder={en.shop.searchHint}
                className="h-full min-w-0 flex-1 bg-transparent text-body outline-none"
              />
            </label>
            <button type="submit" className="press min-h-14 rounded-control bg-[#ffd27a] px-6 text-body font-extrabold text-[#2c2208]">
              {en.shop.search.split(" ")[0]}
            </button>
          </form>
        </div>
        <span aria-hidden="true" className="absolute -right-24 -bottom-24 size-96 rounded-full bg-field opacity-50" />
        <span aria-hidden="true" className="absolute top-8 right-24 size-40 rounded-full bg-leaf opacity-40" />
      </section>

      {offers.length > 0 && asked === "" ? (
        <Row title={en.shop.offers}>
          <div className={GRID}>
            {offers.map((product) => (
              <ProductCard key={product.id} product={product} reasons={["ON_OFFER"]} />
            ))}
          </div>
        </Row>
      ) : null}

      {asked === "" ? (
        shopper ? (
          picks.length > 0 ? (
            <Row title={en.shop.forYou} lead={en.shop.forYouLead}>
              <div className={GRID}>
                {picks.map((pick) => (
                  <ProductCard key={pick.product.id} product={pick.product} reasons={pick.reasons} />
                ))}
              </div>
            </Row>
          ) : null
        ) : null
      ) : null}

      <Row title={asked === "" ? en.shop.all : `“${asked}”`}>
        {products.data === null ? (
          <p className="text-body text-ink-2">{products.error === null ? en.shop.loading : en.shop.failed}</p>
        ) : list.length === 0 ? (
          <Empty icon="bag" title={asked === "" ? en.shop.empty : en.shop.none} />
        ) : (
          <div className={GRID}>
            {list.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </Row>
      {shopper ? null : (
        <p className="text-small text-ink-3">
          <a href={hrefOf({ screen: "account" })} className="font-bold text-primary">
            {en.account.logIn}
          </a>{" "}
          · {en.shop.forYouOff}
        </p>
      )}
    </div>
  );
}

const noPicks = () => Promise.resolve([]);
