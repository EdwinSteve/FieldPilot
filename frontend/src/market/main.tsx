import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setSession } from "../api/client";
import { session } from "./api/session";
import { MarketApp } from "./MarketApp";
import "./market.css";

// Every call carries the shopper's or the operator's login (D082); the catalogue works without one.
setSession(session);

const root = document.getElementById("market-root");
if (!root) {
  throw new Error("Root element #market-root not found");
}

// A saved login renews before the first screen asks for anything, so no call goes out without it:
// with AUTH_REQUIRED=0 the backend never answers 401, and a call without a token runs as the
// anonymous demo user. Offline or with no saved login, this resolves at once.
void session.ensureAccess().finally(() =>
  createRoot(root).render(
    <StrictMode>
      <MarketApp />
    </StrictMode>,
  ),
);
