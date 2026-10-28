"""The gate's answer to a proposal."""

from dataclasses import dataclass

from app.domain.enums import AutonomyLevel, GateOutcome
from app.domain.violations import RuleCode, RuleViolation

OUTCOME_FOR_LEVEL: dict[AutonomyLevel, GateOutcome] = {
    AutonomyLevel.AUTONOMOUS: GateOutcome.EXECUTE,
    AutonomyLevel.NOTIFY: GateOutcome.EXECUTE_AND_NOTIFY,
    AutonomyLevel.APPROVAL: GateOutcome.AWAIT_APPROVAL,
}


@dataclass(frozen=True)
class GateVerdict:
    outcome: GateOutcome
    requested_level: AutonomyLevel  # default, tightened by the stage (D006)
    effective_level: AutonomyLevel  # after the always-approval check and the rules
    violations: tuple[RuleViolation, ...]

    @property
    def reason_code(self) -> RuleCode | None:
        """The leading cause: emergency stop, then always-approval, then the first rule (D022)."""
        return self.violations[0].code if self.violations else None
