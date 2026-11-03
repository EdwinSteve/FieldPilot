// The marketplace shell: a top bar on wide screens, a bottom bar on phones, and the screen between.
import { useEffect, type ReactNode } from "react";
import { Icon, type IconName } from "../farmer/components/Icon";
import { Wordmark } from "../farmer/components/Wordmark";
import appIcon from "../farmer/assets/icon-180.png";
import { useLook } from "../farmer/hooks/useLook";
import { en } from "./i18n/en";
import { hrefOf, tabOf, type MarketRoute } from "./lib/route";
import { canRunWarehouse, type MarketRole } from "./lib/storedUser";
import { AccountPage } from "./screens/Account";
import { AssistantPage } from "./screens/Assistant";
import { CartPage } from "./screens/Cart";
import { LotPage } from "./screens/Lot";
import { OrderPage, OrdersPage } from "./screens/Orders";
import { ProductPage } from "./screens/Product";
import { Shop } from "./screens/Shop";
import { WarehousePage } from "./screens/Warehouse";
import { useCart, useRoute, useUser } from "./state";

type Tab = ReturnType<typeof tabOf>;

interface NavItem {
  tab: Tab;
  icon: IconName;
  route: MarketRoute;
}

const SHOPPER: NavItem[] = [
  { tab: "shop", icon: "home", route: { screen: "shop" } },
  { tab: "assistant", icon: "chat", route: { screen: "assistant" } },
  { tab: "cart", icon: "bag", route: { screen: "cart" } },
  { tab: "orders", icon: "document", route: { screen: "orders" } },
  { tab: "account", icon: "user", route: { screen: "account" } },
];
const WAREHOUSE: NavItem[] = [
  { tab: "warehouse", icon: "home", route: { screen: "warehouse" } },
  { tab: "shop", icon: "bag", route: { screen: "shop" } },
  { tab: "account", icon: "user", route: { screen: "account" } },
];
const FARMER: NavItem[] = [
  { tab: "shop", icon: "home", route: { screen: "shop" } },
  { tab: "account", icon: "user", route: { screen: "account" } },
];

function navFor(role: MarketRole | null): NavItem[] {
  if (canRunWarehouse(role)) return WAREHOUSE;
  return role === "farmer" ? FARMER : SHOPPER;
}

function screenFor(route: MarketRoute): ReactNode {
  switch (route.screen) {
    case "shop":
      return <Shop />;
    case "product":
      return <ProductPage key={route.id} id={route.id} />;
    case "cart":
      return <CartPage />;
    case "orders":
      return <OrdersPage />;
    case "order":
      return <OrderPage key={route.id} id={route.id} />;
    case "assistant":
      return <AssistantPage />;
    case "account":
      return <AccountPage />;
    case "lot":
      return <LotPage key={route.code} code={route.code} />;
    case "warehouse":
      return <WarehousePage />;
  }
}

function CartBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="absolute -top-1.5 -right-2 flex min-w-6 items-center justify-center rounded-pill border-2 border-surface bg-needs px-1.5 text-caption font-extrabold text-surface">
      {count}
    </span>
  );
}

export function MarketApp() {
  // Light or dark as the farmer app: the same saved look, or the phone's.
  useLook();
  const route = useRoute();
  const user = useUser();
  const cart = useCart();
  const active = tabOf(route);
  const items = navFor(user?.role ?? null);
  const count = cart?.lines.length ?? 0;

  useEffect(() => {
    document.title = route.screen === "shop" ? en.brand : en.titles.page(en.titles[route.screen]);
    window.scrollTo({ top: 0 });
  }, [route.screen, route]);

  return (
    <div className="flex min-h-dvh flex-col bg-ground text-ink">
      <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-18 w-full max-w-[1240px] items-center justify-between gap-4 px-4 md:px-8">
          <a href={hrefOf({ screen: "shop" })} className="flex items-center gap-2.5 no-underline">
            <img src={appIcon} alt="" width={40} height={40} className="size-10 rounded-tile" />
            <Wordmark />
            <span className="rounded-pill bg-tint px-2.5 py-1 text-caption font-extrabold text-primary-hover">Market</span>
          </a>
          <nav aria-label={en.nav.label} className="hidden items-center gap-1 md:flex">
            {items.map((item) => (
              <a
                key={item.tab}
                href={hrefOf(item.route)}
                aria-current={active === item.tab ? "page" : undefined}
                className={`relative flex min-h-12 items-center gap-2 rounded-control px-4 text-body font-bold no-underline ${
                  active === item.tab ? "bg-tint text-primary" : "text-ink-2 hover:bg-ground"
                }`}
              >
                <span className="relative">
                  <Icon name={item.icon} size={22} />
                  {item.tab === "cart" ? <CartBadge count={count} /> : null}
                </span>
                {en.nav[item.tab]}
              </a>
            ))}
          </nav>
          <a href={hrefOf({ screen: "cart" })} aria-label={`${en.nav.cart}, ${en.nav.cartCount(count)}`} className="relative flex size-12 items-center justify-center rounded-full text-ink md:hidden">
            <Icon name="bag" size={26} />
            <CartBadge count={count} />
          </a>
        </div>
      </header>

      <main key={`${route.screen}-${hrefOf(route)}`} className="mx-auto w-full max-w-[1240px] flex-1 animate-screen-in px-4 pt-6 pb-32 md:px-8 md:pb-16">
        {screenFor(route)}
      </main>

      <nav
        aria-label={en.nav.label}
        className="fixed inset-x-0 bottom-0 z-30 grid border-t border-border bg-surface px-2 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] md:hidden"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        {items.map((item) => (
          <a
            key={item.tab}
            href={hrefOf(item.route)}
            aria-current={active === item.tab ? "page" : undefined}
            className={`flex min-h-16 flex-col items-center justify-center gap-1 rounded-tile text-caption no-underline ${
              active === item.tab ? "bg-tint font-extrabold text-primary" : "font-semibold text-ink-3"
            }`}
          >
            <span className="relative">
              <Icon name={item.icon} size={24} />
              {item.tab === "cart" ? <CartBadge count={count} /> : null}
            </span>
            {en.nav[item.tab]}
          </a>
        ))}
      </nav>
    </div>
  );
}
