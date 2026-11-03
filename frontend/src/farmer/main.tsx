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

createRoot(root).render(
  <StrictMode>
    <FarmerApp />
  </StrictMode>,
);
