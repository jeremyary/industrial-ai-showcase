# This project was developed with assistance from AI tools.
"""Pre-built order templates for demo scenarios."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderTemplate:
    material: str
    quantity: int
    source_location: str
    destination_location: str


TEMPLATES: list[OrderTemplate] = [
    OrderTemplate("BEARING-ASSY-7200", 48, "dock-a", "dock-b"),
    OrderTemplate("MOTOR-CTRL-X10", 12, "dock-a", "dock-b"),
    OrderTemplate("WIDGET-A-42", 200, "dock-a", "dock-b"),
    OrderTemplate("GEARBOX-G3-LH", 24, "dock-b", "dock-a"),
    OrderTemplate("SENSOR-PKG-IR-05", 96, "dock-a", "dock-b"),
]
