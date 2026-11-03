import { CYCLE_STEPS, stepStates, stepTurns, type CycleStep, type StepState } from "../lib/cycle";
import { SUBAGENT_LABELS } from "../lib/timeline";
import type { DailyCycleResult } from "../types/api";

interface HeroDiagramProps {
  lastCycle: DailyCycleResult | null;
}

/** How FieldPilot works, as a collapsible flow. Steps glow where the last cycle got. */
export function HeroDiagram({ lastCycle }: HeroDiagramProps) {
  const states = stepStates(lastCycle);
  const turns = stepTurns(lastCycle);
  return (
    <details className="hero" open>
      <summary>How FieldPilot works</summary>
      <svg className="hero-diagram" viewBox="0 0 480 470">
        <title>
          The agent reads sensors and satellite and proposes; the autonomy gate decides; the valve
          or the farmer acts. Everything is recorded.
        </title>
        <defs>
          <marker
            id="hero-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M0 0L10 5L0 10z" className="hero-arrowhead" />
          </marker>
        </defs>

        <g>
          <rect x="40" y="8" width="400" height="54" rx="12" className="hero-node" />
          <text x="240" y="30" textAnchor="middle" className="hero-title">
            Sensors and satellite
          </text>
          <text x="240" y="50" textAnchor="middle" className="hero-sub">
            moisture · rain forecast · NDVI · imagery
          </text>
        </g>
        <line x1="240" y1="62" x2="240" y2="76" className="hero-wire" markerEnd="url(#hero-arrow)" />

        <g>
          <rect x="40" y="78" width="400" height="180" rx="12" className="hero-node hero-node--agent" />
          <text x="240" y="100" textAnchor="middle" className="hero-title">
            Agent: daily cycle
          </text>
          {CYCLE_STEPS.map((step, i) => (
            <StepRow key={step} step={step} y={110 + i * 36} state={states[step]} turns={turns[step]} />
          ))}
        </g>
        <line
          x1="240"
          y1="258"
          x2="240"
          y2="272"
          className="hero-wire"
          markerEnd="url(#hero-arrow)"
        />

        <g>
          <rect x="40" y="274" width="400" height="92" rx="12" className="hero-node hero-node--gate" />
          <text x="240" y="296" textAnchor="middle" className="hero-title">
            Autonomy gate
          </text>
          <text x="240" y="318" textAnchor="middle" className="hero-sub">
            autonomous · with notice · with approval
          </text>
          <text x="240" y="340" textAnchor="middle" className="hero-sub">
            and always the safety rules
          </text>
        </g>
        <line
          x1="240"
          y1="366"
          x2="240"
          y2="380"
          className="hero-wire"
          markerEnd="url(#hero-arrow)"
        />

        <g>
          <rect x="40" y="382" width="192" height="52" rx="12" className="hero-node" />
          <text x="136" y="404" textAnchor="middle" className="hero-title">
            Valve
          </text>
          <text x="136" y="424" textAnchor="middle" className="hero-sub">
            irrigates what was approved
          </text>
          <rect x="248" y="382" width="192" height="52" rx="12" className="hero-node" />
          <text x="344" y="404" textAnchor="middle" className="hero-title">
            Farmer
          </text>
          <text x="344" y="424" textAnchor="middle" className="hero-sub">
            approves and reverts
          </text>
        </g>

        <text x="240" y="458" textAnchor="middle" className="hero-foot">
          Everything is recorded in the event log.
        </text>
      </svg>
    </details>
  );
}

interface StepRowProps {
  step: CycleStep;
  y: number;
  state: StepState;
  turns: number | null;
}

function StepRow({ step, y, state, turns }: StepRowProps) {
  const caption =
    turns === null ? "" : state === "stopped" ? `${turns} turns · stopped` : `${turns} turns`;
  return (
    <g>
      <rect x="56" y={y} width="368" height="30" rx="9" className={`hero-step hero-step--${state}`} />
      <circle cx="78" cy={y + 15} r="6" className={`hero-dot hero-dot--${state}`} />
      <text x="92" y={y + 20} className="hero-step-label">
        {SUBAGENT_LABELS[step] ?? step}
      </text>
      <text x="412" y={y + 20} textAnchor="end" className="hero-sub">
        {caption}
      </text>
    </g>
  );
}
