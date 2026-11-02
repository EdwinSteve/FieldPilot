import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FarmerApp } from "./FarmerApp";
import "./farmer.css";

const root = document.getElementById("farmer-root");
if (!root) {
  throw new Error("Root element #farmer-root not found");
}

createRoot(root).render(
  <StrictMode>
    <FarmerApp />
  </StrictMode>,
);
