# This project was developed with assistance from AI tools.
"""Rule-based decisioning for Fleet Manager v1.

Single rule for Phase 1 per user guidance 2026-04-19 and the 5-min demo script:
an aisle-obstruction event triggers a reroute mission for the AMR in that aisle.
Additional rules land when a future demo beat earns them — not speculatively.

LangGraph-based agentic decisioning arrives in Phase 3 (ADR-005, ADR-019).
"""

from common_lib.events import EventClass, FleetEvent, FleetMission, MissionKind


class DecisionRule:
    """A decisioning rule maps a FleetEvent to zero or one FleetMission."""

    name: str

    def applies(self, event: FleetEvent) -> bool:
        raise NotImplementedError

    def decide(self, event: FleetEvent, policy_version: str) -> FleetMission:
        raise NotImplementedError


class AisleObstructionReroute(DecisionRule):
    """Phase 1 demo rule: aisle-obstruction event → reroute AMR on alternate path."""

    name = "aisle-obstruction-reroute"
    CONFIDENCE_THRESHOLD = 0.8

    def applies(self, event: FleetEvent) -> bool:
        return (
            event.event_class == EventClass.AISLE_OBSTRUCTION
            and event.confidence >= self.CONFIDENCE_THRESHOLD
        )

    def decide(self, event: FleetEvent, policy_version: str) -> FleetMission:
        robot_id = str(event.payload.get("affected_robot_id", "amr-07"))
        return FleetMission(
            trace_id=event.trace_id,
            kind=MissionKind.REROUTE,
            robot_id=robot_id,
            triggered_by_event_id=event.event_id,
            policy_version=policy_version,
            params={"reason": "aisle-obstruction", "origin_location": event.location},
        )


class RuleEngine:
    """Evaluates rules in order; first match wins."""

    def __init__(self, rules: list[DecisionRule], policy_version: str) -> None:
        self._rules = rules
        self._policy_version = policy_version

    def evaluate(self, event: FleetEvent) -> FleetMission | None:
        for rule in self._rules:
            if rule.applies(event):
                return rule.decide(event, self._policy_version)
        return None


def default_engine(policy_version: str = "vla-warehouse-v1.3") -> RuleEngine:
    return RuleEngine(rules=[AisleObstructionReroute()], policy_version=policy_version)
