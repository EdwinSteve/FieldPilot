# FieldPilot demo script

A three-minute walk through two simulated days on the demo farm (D076). The
model's answers are recorded, so the demo runs offline with `MOCK_LLM=1` and
looks the same every time. Part B, the chat and voice, needs the real model.

The dashboard is in Spanish, so the button names below are quoted exactly as
they appear on screen.

## Before you record

```bash
make seed      # fresh demo farm; the clock is paused on 2 Nov, 06:00 in Neiva
make dev       # backend :8000 and dashboard :5173 (MOCK_LLM=1 from .env)
               # if :8000 is taken: make dev BACKEND_PORT=8001
```

Open <http://localhost:5173>, full screen, and check that the clock reads
**2 nov, 06:00 · en pausa**.

**The one rule of the recorded demo.** The replay reproduces the recorded
run only on the same clicks: the tools read the database, so a different
action makes a different farm. Until the day-2 cycle has run:
- **reject** the held irrigation (do not approve it);
- do not press "Reanudar", the speeds, "+1 h" or "Actualizar simulación".

After the day-2 cycle, anything goes.

## Part A — two days in three minutes (`MOCK_LLM=1`)

| Time | Click | What to say |
|---|---|---|
| 0:00 | Open **Cómo funciona FieldPilot**, then point at **Autonomía: quién decide** | "FieldPilot is an agent that runs a maize field. Four subagents read the sensors, the forecast and the satellite, and propose actions. The model never touches a valve: an autonomy gate decides every action, by level and by safety rule." |
| 0:20 | **Ejecutar ciclo diario** | "Day one. The agent monitors the field, reads the satellite image, decides on irrigation and writes a report." (the **Ciclo diario** stepper runs through Monitoreo → Imágenes → Riego → Informe) |
| 0:35 | Point at **Zonas** and **Vista satelital** | "Zona 2 is dry: 20 % moisture against 32 % field capacity. The satellite shows low vigour and about a quarter of bare soil; SAM 3.1 found the patches." |
| 0:45 | Point at the card in **Pendientes de aprobación** | "The agent proposed 20 mm, but 12 mm of rain is coming. The gate held it for the farmer, and says why in plain Spanish." |
| 0:55 | Type *Esperaré la lluvia* in **Motivo (opcional)**, then **Rechazar** | "The farmer decides to wait for the rain. That 'no' is logged as clearly as a 'yes'." |
| 1:05 | **Inyectar sequía (48 h)**, then **+1 día** | "The rain does not come: we inject a drought and move to the next morning." (the clock reads 3 nov, 06:00) |
| 1:15 | **Ejecutar ciclo diario** | "Day two. The soil dropped to 16,7 % and no rain is forecast." |
| 1:30 | Point at **Calendario** | "This time the gate let the 20 mm run on its own: it is within every limit. The agent also scheduled the rest of the deficit for tomorrow, with notice, because the safety rules allow at most 20 mm a day." |
| 1:45 | Point at the card **Ventana en reloj simulado** | "A notified action can be reverted for six hours of simulated time. The backend decides the window; the screen only shows it." |
| 1:55 | **×360**, then **Reanudar** | "At ×360 the six hours pass in about a minute; the dashboard updates the simulation every five seconds." (the card shows "≈ … reales a ×360 (estimación)") |
| 2:10 | **Revertir** on the extra irrigation, then **Pausar** | "The farmer reverts it before it runs. Nothing was applied." |
| 2:20 | Open **Informes del día** | "Every day ends with a report. Every number in it is checked against what the agent actually read; a report with an invented number is refused." |
| 2:35 | Open **Libro de eventos** | "Every proposal, verdict, execution, rejection and revert is in an append-only log, with the rule that applied." |
| 2:45 | **Parada de emergencia**, then **Desactivar parada de emergencia** | "And one button stops any action that adds water. Closing a valve always works." |
| 2:55 | — | "FieldPilot: the agent decides, the gate checks, the farmer has the last word." |

## Part B — chat and voice (real model, optional)

Stop `make dev` and start it with the real model on the same farm:

```bash
MOCK_LLM=0 make dev
```

- In **Pregúntale al agente**, type *¿Cómo está la humedad de la zona 2?* and
  click **Preguntar**. The answer cites the readings, rounded, and every number
  is checked before it is shown.
- Click **Hablar**, ask *¿Necesita agua el maíz de la zona dos?*, then
  **Detener y enviar**. The dashboard shows what it understood ("Entendí: «…»")
  and the answer. The chat never acts: it says the daily cycle decides (D057).

With `MOCK_LLM=0` the daily cycle also runs on the real model, so its
proposals can differ from the recording; the gate still decides each one.

## Reset and troubleshooting

| What you see | What to do |
|---|---|
| "El ciclo grabado de hoy ya se ejecutó" | That day already ran. Press "+1 día" (day 1), or reset. |
| A 503 that says the recorded answer does not fit this farm | An action differed from the script. Reset. |
| The dashboard says the backend is offline | Check `make dev`; with `BACKEND_PORT`, use the same value for both. |

**Reset:** stop `make dev`, then `make seed` and `make dev` again.

**Re-record** after changing a prompt, the seed or these steps:
`make record-demo` (real model, about 30 calls). It saves nothing unless day 1
holds an irrigation for approval and day 2 leaves one to revert.
