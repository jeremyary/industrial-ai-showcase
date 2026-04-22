# This project was developed with assistance from AI tools.
"""Demo scenario definitions sourced from warehouse-topology.yaml."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ButtonDef:
    """A presenter-facing button rendered by the Showcase Console."""

    label: str
    action: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    buttons: tuple[ButtonDef, ...]


AISLE_3_OBSTRUCTION = Scenario(
    name="aisle-3-obstruction",
    description=(
        "Presenter-triggered obstruction scenario: forklift drives to aisle-3 "
        "approach-point, pauses for clearance narration, Drop Pallet fires, "
        "Cosmos Reason detects, Fleet Manager replans via aisle-4."
    ),
    buttons=(
        ButtonDef(
            label="Dispatch Mission",
            action="dispatch",
        ),
        ButtonDef(
            label="Drop Pallet",
            action="drop-pallet",
            params={"to_state": "obstructed"},
        ),
        ButtonDef(
            label="Clear Pallet",
            action="clear-pallet",
            params={"to_state": "empty"},
        ),
    ),
)


_CATALOG: dict[str, Scenario] = {AISLE_3_OBSTRUCTION.name: AISLE_3_OBSTRUCTION}


def get_scenario(name: str) -> Scenario:
    if name not in _CATALOG:
        raise KeyError(f"Unknown scenario: {name}. Known: {list(_CATALOG)}")
    return _CATALOG[name]


def list_scenarios() -> list[str]:
    return list(_CATALOG)
