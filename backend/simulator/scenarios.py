"""
Aletheia Digital Twin — Scenario Engine

Each scenario modifies the Weather/Soil/Plant engines to simulate
specific environmental conditions. All scenarios are deterministic
— they apply continuous offsets, not random perturbations.

Scenarios:
  - normal_day:      Baseline greenhouse conditions
  - heat_wave:       Progressive temperature increase
  - cold_wave:       Progressive temperature decrease
  - cloudy_day:      Reduced sunlight, higher humidity
  - drought:         No irrigation, no rain, progressive soil drying
  - overwatering:    Continuous irrigation, saturated soil
  - nutrient_lockout: Simulated via high soil temp + low pH indicators
                      (labeled clearly as environmental assumption, not measurement)
  - transplant_shock: High stress initial state, recovery trajectory
  - sensor_failure:   Virtual sensors return None for some fields
  - power_failure:    All systems off — temperature drifts to ambient
"""

from typing import Dict


SCENARIOS = {
    "normal_day": {
        "label": "Normal Day",
        "description": "Baseline greenhouse conditions with natural diurnal cycle.",
        "temp_offset": 0.0,
        "humidity_offset": 0.0,
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 0.0,
        "sensor_failure_fields": [],
    },
    "heat_wave": {
        "label": "Heat Wave",
        "description": "Progressive temperature increase peaking at +12°C above normal.",
        "temp_offset": 0.15,       # °C per minute increase
        "humidity_offset": -0.3,   # humidity drops as temp rises
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 10.0,
        "sensor_failure_fields": [],
    },
    "cold_wave": {
        "label": "Cold Wave",
        "description": "Progressive temperature decrease to near-freezing greenhouse.",
        "temp_offset": -0.12,      # °C per minute decrease
        "humidity_offset": 0.1,    # humidity rises slightly
        "cloud_boost": 0.3,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 5.0,
        "sensor_failure_fields": [],
    },
    "cloudy_day": {
        "label": "Cloudy Day",
        "description": "Heavy cloud cover reducing sunlight by 70%, higher humidity.",
        "temp_offset": 0.0,
        "humidity_offset": 0.1,
        "cloud_boost": 0.7,        # 70% cloud cover
        "rain_boost": 0.1,         # light drizzle
        "irrigation": False,
        "initial_stress": 0.0,
        "sensor_failure_fields": [],
    },
    "drought": {
        "label": "Drought",
        "description": "No irrigation, no rain — progressive soil moisture depletion.",
        "temp_offset": 0.05,       # slight warming from dry conditions
        "humidity_offset": -0.2,   # drier air
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 5.0,
        "sensor_failure_fields": [],
    },
    "overwatering": {
        "label": "Overwatering",
        "description": "Continuous irrigation saturating soil beyond field capacity.",
        "temp_offset": 0.0,
        "humidity_offset": 0.2,    # high humidity from wet soil
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": True,        # irrigation ON continuously
        "initial_stress": 0.0,
        "sensor_failure_fields": [],
    },
    "nutrient_lockout": {
        "label": "Nutrient Lockout (Simulated)",
        "description": (
            "SIMULATED SCENARIO based on environmental assumptions, "
            "NOT direct nutrient measurement. High soil temperature + "
            "low moisture create conditions associated with nutrient lockout."
        ),
        "temp_offset": 0.08,       # warming
        "humidity_offset": -0.1,
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 15.0,
        "sensor_failure_fields": [],
    },
    "transplant_shock": {
        "label": "Transplant Shock",
        "description": "Plant starts with high stress, gradually recovers if conditions stay optimal.",
        "temp_offset": 0.0,
        "humidity_offset": 0.0,
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 60.0,    # start very stressed
        "sensor_failure_fields": [],
    },
    "sensor_failure": {
        "label": "Sensor Failure",
        "description": "Simulated sensor malfunction — some readings drop to None/null.",
        "temp_offset": 0.0,
        "humidity_offset": 0.0,
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 0.0,
        "sensor_failure_fields": ["leaf_temp", "soil_temp", "light"],
    },
    "power_failure": {
        "label": "Power Failure",
        "description": "All climate control off — temperature drifts toward ambient, no irrigation.",
        "temp_offset": -0.1,       # cooling toward ambient
        "humidity_offset": 0.0,
        "cloud_boost": 0.0,
        "rain_boost": 0.0,
        "irrigation": False,
        "initial_stress": 0.0,
        "sensor_failure_fields": [],
    },
}


def apply_scenario(sim, scenario_name: str):
    """
    Apply a scenario to a GreenhouseSimulator instance.
    Modifies weather offsets, soil irrigation, and plant initial stress.
    Does NOT use random — all offsets are deterministic constants.
    """
    config = SCENARIOS.get(scenario_name)
    if config is None:
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(SCENARIOS.keys())}")

    # Weather offsets
    sim.weather.scenario_temp_offset = config["temp_offset"]
    sim.weather.scenario_humidity_offset = config["humidity_offset"]
    sim.weather.scenario_cloud_boost = config["cloud_boost"]
    sim.weather.scenario_rain_boost = config["rain_boost"]

    # Soil
    sim.soil.irrigation_active = config["irrigation"]

    # Plant
    sim.plant.stress = config["initial_stress"]
    sim.plant.stress_recovery = 0.0

    # Sensor failure simulation
    sim._sensor_failure_fields = config["sensor_failure_fields"]

    # Reset scenario timer
    sim.scenario_elapsed = 0.0
    sim.current_scenario = scenario_name

    # For cold_wave, start from a cooler baseline
    if scenario_name == "cold_wave":
        sim.weather.air_temp = 18.0
    # For heat_wave, start from a warmer baseline
    if scenario_name == "heat_wave":
        sim.weather.air_temp = 30.0
    # For drought, start with drier soil
    if scenario_name == "drought":
        sim.soil.soil_moisture = 35.0
    # For overwatering, start saturated
    if scenario_name == "overwatering":
        sim.soil.soil_moisture = 85.0
    # For nutrient_lockout, start with warm soil
    if scenario_name == "nutrient_lockout":
        sim.soil.soil_temp = 30.0
        sim.soil.soil_moisture = 30.0
    # For power_failure, start normal but systems go off
    if scenario_name == "power_failure":
        sim.soil.irrigation_active = False


def get_scenario_list() -> Dict:
    """Return scenario catalog for frontend display."""
    return {
        name: {
            "label": cfg["label"],
            "description": cfg["description"],
        }
        for name, cfg in SCENARIOS.items()
    }