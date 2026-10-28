"""AutonomyGate: decides the level of every proposal. It never executes anything.

Pure and deterministic, so the decision can be tested exhaustively and
replayed from the event log.
"""

from dataclasses import dataclass

from app.autonomy.policy import AutonomyPolicy
from app.domain.enums import AutonomyLevel, strictest
from app.domain.proposals import ProposedAction
from app.domain.verdicts import OUTCOME_FOR_LEVEL, GateVerdict
from app.domain.violations import RuleCode, RuleViolation
from app.safety.rules import SafetyContext, SafetyLimits, evaluate_rules


@dataclass(frozen=True)
class GateContext:
    safety: SafetyContext
    stage_level: AutonomyLevel | None  # StageSpec.level_for(action_type)


class AutonomyGate:
    def __init__(self, policy: AutonomyPolicy, limits: SafetyLimits) -> None:
        self._policy = policy
        self._limits = limits

    def evaluate(self, action: ProposedAction, context: GateContext) -> GateVerdict:
        """Autonomy level first, safety rules second (non-negotiable rule 1).

        1. default level from the policy;
        2. tightened by the stage override, never relaxed (D006);
        3. always-approval types go to APPROVAL;
        4. any rule violation goes to APPROVAL, listing every violation;
        5. otherwise the requested level stands.
        Nothing is dropped: the worst outcome is AWAIT_APPROVAL (D004).
        """
        requested = self._requested_level(action, context)
        violations = self._violations(action, context)
        effective = AutonomyLevel.APPROVAL if violations else requested
        return GateVerdict(
            outcome=OUTCOME_FOR_LEVEL[effective],
            requested_level=requested,
            effective_level=effective,
            violations=violations,
        )

    def _requested_level(self, action: ProposedAction, context: GateContext) -> AutonomyLevel:
        default = self._policy.default_level(action.action_type)
        if context.stage_level is None:
            return default
        return strictest(default, context.stage_level)

    def _violations(
        self, action: ProposedAction, context: GateContext
    ) -> tuple[RuleViolation, ...]:
        """Rule violations, with always-approval right after the emergency stop (D022)."""
        rules = evaluate_rules(action, context.safety, self._limits)
        if action.action_type not in self._policy.always_approval:
            return rules
        always = RuleViolation(
            RuleCode.ALWAYS_APPROVAL_TYPE, {"action_type": str(action.action_type)}
        )
        leading = tuple(v for v in rules if v.code is RuleCode.EMERGENCY_STOP_ACTIVE)
        rest = tuple(v for v in rules if v.code is not RuleCode.EMERGENCY_STOP_ACTIVE)
        return (*leading, always, *rest)
