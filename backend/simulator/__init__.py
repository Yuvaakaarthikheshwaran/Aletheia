"""
Aletheia Digital Twin Simulator

A deterministic, physics-based virtual greenhouse that produces
sensor data compatible with the existing /analyze endpoint.

Architecture:
  Weather Engine → Soil Engine → Plant Physiology → Virtual Sensors → /analyze

No random.randint() or random.uniform() — all evolution is continuous
and driven by physical relationships between variables.
"""

from backend.simulator.engine import GreenhouseSimulator
from backend.simulator.scenarios import SCENARIOS

__all__ = ["GreenhouseSimulator", "SCENARIOS"]