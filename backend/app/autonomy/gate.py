"""AutonomyGate: decides the level of every proposal. It never executes anything.

Pure and deterministic, so the decision can be tested exhaustively and
replayed from the event log. It is also the only issuer of `ExecutionPermit`,
the one value the actuator accepts (D037).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.autonomy.policy import AutonomyPolicy
from app.domain.enums import ActionType, AutonomyLevel, GateOutcome, strictest
from app.domain.proposals import ProposedAction
from app.domain.verdicts import OUTCOME_FOR_LEVEL, GateVerdict
from app.domain.violations import RuleCode, RuleViolation
from app.safety.rules import SafetyContext, SafetyLimits, evaluate_rules


@dataclass(frozen=True)
class GateContext:
    safety: SafetyContext
    stage_level: AutonomyLevel | None  # StageSpec.level_for(action_type)


@dataclass(frozen=True, init=False)
class ExecutionPermit:
    """Authority to execute one action, issued only by `AutonomyGate.authorize`.

    The constructor always refuses, and so does `dataclasses.replace`, which
    calls it. Only `_issue_permit` below builds one (D037).
    """

    proposal_key: str
    action_type: ActionType
    zone_id: int | None
    params: Mapping[str, float | str]
    level: AutonomyLevel  # AUTONOMOUS or NOTIFY; APPROVAL only when approved_by is set
    approved_by: str | None  # the farmer whose approval it carries (D062)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise PermissionError("an ExecutionPermit can only be issued by AutonomyGate")


@dataclass(frozen=True)
class FarmerApproval:
    """What the farmer approved: the rule codes of the verdict they saw (D062)."""

    actor: str
    approved_codes: frozenset[RuleCode]


@dataclass(frozen=True)
class Authorization:
    verdict: GateVerdict
    permit: ExecutionPermit | None  # None unless EXECUTE or EXECUTE_AND_NOTIFY


_EXECUTABLE_OUTCOMES = frozenset({GateOutcome.EXECUTE, GateOutcome.EXECUTE_AND_NOTIFY})


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

    def authorize(self, action: ProposedAction, context: GateContext) -> Authorization:
        """Evaluate, and attach a permit only when the outcome lets the action run."""
        verdict = self.evaluate(action, context)
        if verdict.outcome not in _EXECUTABLE_OUTCOMES:
            return Authorization(verdict, permit=None)
        return Authorization(verdict, _issue_permit(action, verdict.effective_level))

    def authorize_approved(
        self, action: ProposedAction, context: GateContext, approval: FarmerApproval
    ) -> Authorization:
        """A permit for what the farmer approved, and nothing more (D062).

        Never while the emergency stop is active (D022), and never when the
        fresh verdict has a violation the farmer did not see: that is a new
        situation, and only a new decision can cover it.
        """
        verdict = self.evaluate(action, context)
        if verdict.outcome in _EXECUTABLE_OUTCOMES:
            return Authorization(verdict, _issue_permit(action, verdict.effective_level))
        if unapproved(verdict, approval):
            return Authorization(verdict, permit=None)
        permit = _issue_permit(action, AutonomyLevel.APPROVAL, approved_by=approval.actor)
        return Authorization(verdict, permit)

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


def unapproved(verdict: GateVerdict, approval: FarmerApproval) -> tuple[RuleViolation, ...]:
    """Violations the approval does not cover. The emergency stop is never covered."""
    return tuple(
        v
        for v in verdict.violations
        if v.code is RuleCode.EMERGENCY_STOP_ACTIVE or v.code not in approval.approved_codes
    )


def _issue_permit(
    action: ProposedAction, level: AutonomyLevel, approved_by: str | None = None
) -> ExecutionPermit:
    permit = object.__new__(ExecutionPermit)
    values = {
        "proposal_key": action.proposal_key,
        "action_type": action.action_type,
        "zone_id": action.zone_id,
        "params": dict(action.params),
        "level": level,
        "approved_by": approved_by,
    }
    for name, value in values.items():
        object.__setattr__(permit, name, value)
    return permit
