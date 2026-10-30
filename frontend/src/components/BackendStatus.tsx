import { useEffect, useState } from "react";
import { fetchHealth } from "../api/health";

type Status = "checking" | "online" | "offline";

const LABELS: Record<Status, string> = {
  checking: "Conectando…",
  online: "Backend en línea",
  offline: "Backend sin conexión",
};

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    fetchHealth()
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));
  }, []);

  return <p className={`backend-status backend-status--${status}`}>{LABELS[status]}</p>;
}
