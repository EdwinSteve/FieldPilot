import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setSession } from "../api/client";
import { session } from "./api/session";
import { FarmerApp } from "./FarmerApp";
import "./farmer.css";

// Every call to the farm carries the farmer's login (D082).
setSession(session);

const root = document.getElementById("farmer-root");
if (!root) {
  throw new Error("Root element #farmer-root not found");
}

// A saved login renews before the first screen asks for anything, so no call goes out without it:
// with AUTH_REQUIRED=0 the backend never answers 401, and a call without a token runs as the
// anonymous demo user. Offline or with no saved login, this resolves at once.
void session.ensureAccess().finally(() =>
  createRoot(root).render(
    <StrictMode>
      <FarmerApp />
    </StrictMode>,
  ),
);
