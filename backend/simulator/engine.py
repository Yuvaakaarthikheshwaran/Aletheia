"""
Aletheia Digital Twin — Core Physics Engine

Deterministic, continuous simulation of a virtual greenhouse.
No random.randint() or random.uniform() — every variable evolves
from its previous state through physical relationships.

Architecture:
  Sun → Weather → Soil → Plant Physiology → Virtual Sensors

All time is in simulation minutes. One step = one minute of greenhouse time.
"""

import math
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ============================================================
# Physical Constants & Defaults
# ============================================================

# Sun position model: simulates a sine-wave daylight curve
# Peak at noon (sim_minute 720 = 12:00), sunrise ~360 (06:00), sunset ~1080 (18:00)
SUNRISE_MINUTE = 360   # 06:00
SUNSET_MINUTE = 1080   # 18:00
DAY_LENGTH = SUNSET_MINUTE - SUNRISE_MINUTE  # 720 minutes = 12 hours
SOLAR_NOON = (SUNRISE_MINUTE + SUNSET_MINUTE) // 2  # 720 = 12:00

# Thermal properties
AIR_HEAT_CAPACITY = 1.005  # kJ/(kg·K) — specific heat of air
SOIL_HEAT_CAPACITY = 0.8   # kJ/(kg·K) — approximate for moist soil
THERMAL_COUPLING_AIR_SOIL = 0.15  # how strongly soil temp follows air temp per step
THERMAL_INERTIA_SOIL = 0.92       # soil retains 92% of its temp each step

# Humidity / Evaporation
MAX_ABSOLUTE_HUMIDITY = 30.0  # g/m³ at ~30°C (saturation)
EVAPORATION_RATE_BASE = 0.02  # base evaporation fraction per step
TRANSPIRATION_RATE_BASE = 0.015  # base transpiration fraction per step

# Soil hydrology
SOIL_FIELD_CAPACITY = 80.0   # % — field capacity
SOIL_WILTING_POINT = 15.0    # % — wilting point
INFILTRATION_RATE = 0.6      # fraction of surface water that infiltrates per step
DRAINAGE_RATE = 0.03         # fraction of excess water drained per step
IRRIGATION_RATE = 2.0        # % soil moisture added per irrigation step

# Plant physiology
LEAF_EMISSIVITY = 0.95
STEFAN_BOLTZMANN = 5.67e-8  # W/(m²·K⁴)
PHOTOSYNTHESIS_LIGHT_SATURATION = 1000  # μmol/m²/s — above this, no more gain
PHOTOSYNTHESIS_TEMP_OPTIMUM = 28.0      # °C
PHOTOSYNTHESIS_TEMP_HALF_WIDTH = 10.0   # °C — width of the bell curve
RESPIRATION_Q10 = 2.0                   # doubles every 10°C
RESPIRATION_BASE_TEMP = 20.0            # °C reference
GROWTH_RATE_BASE = 0.001                # base growth per step (unitless)
STRESS_ACCUMULATION_RATE = 0.05         # per step when stressed
RECOVERY_RATE = 0.03                    # per step when not stressed

# Wind (future-ready placeholder)
WIND_SPEED_DEFAULT = 1.5  # m/s — gentle breeze


# ============================================================
# Weather Engine
# ============================================================

class WeatherEngine:
    """
    Simulates sun position, daylight, air temperature, humidity,
    cloud cover, and rain. All driven by a sine-wave solar model.
    """

    def __init__(self):
        self.sim_minute = SOLAR_NOON  # start at noon
        self.air_temp = 28.0          # °C
        self.humidity = 60.0          # % relative humidity
        self.cloud_cover = 0.0        # 0–1 fraction
        self.rain_rate = 0.0          # mm per step
        self.wind_speed = WIND_SPEED_DEFAULT

        # Scenario modifiers (applied externally)
        self.scenario_temp_offset = 0.0
        self.scenario_humidity_offset = 0.0
        self.scenario_cloud_boost = 0.0
        self.scenario_rain_boost = 0.0

    # ----- Sun Model -----

    def sun_elevation(self, minute: int) -> float:
        """
        Sine-wave sun elevation: 0 at sunrise/sunset, 1 at solar noon.
        Returns 0–1 fraction of max solar intensity.
        """
        if minute < SUNRISE_MINUTE or minute > SUNSET_MINUTE:
            return 0.0
        # Normalize position within daylight window
        frac = (minute - SUNRISE_MINUTE) / DAY_LENGTH  # 0→1
        return math.sin(frac * math.pi)  # 0 at edges, 1 at noon

    def daylight(self, minute: int) -> float:
        """Returns solar irradiance in W/m² (0–1000)."""
        elevation = self.sun_elevation(minute)
        # Atmospheric attenuation + cloud effect
        cloud_factor = 1.0 - (self.cloud_cover * 0.7)
        return 1000.0 * elevation * cloud_factor

    # ----- Temperature Model -----

    def _solar_heating(self, minute: int) -> float:
        """Heating contribution from sunlight (°C gain per step)."""
        irradiance = self.daylight(minute)
        # Greenhouse effect: glass traps ~60% of solar energy
        greenhouse_factor = 0.6
        # Convert W/m² to °C/min: ~0.015°C per 100 W/m² in a greenhouse
        return irradiance * greenhouse_factor * 0.00015

    def _radiative_cooling(self) -> float:
        """Cooling via longwave radiation to sky (°C loss per step)."""
        # Stefan-Boltzmann: proportional to T^4 difference
        T_air_K = self.air_temp + 273.15
        T_sky_K = 260.0  # effective sky temperature ~ -13°C
        radiative_flux = STEFAN_BOLTZMANN * (T_air_K**4 - T_sky_K**4)
        # Convert to °C/min: greenhouse glass reduces this
        return radiative_flux * 0.00001 * (1.0 - self.cloud_cover * 0.5)

    def _convective_cooling(self) -> float:
        """Wind-driven convective cooling (°C loss per step)."""
        # Proportional to wind speed and temp difference with ambient
        ambient_temp = 22.0  # outside air temp baseline
        delta = self.air_temp - ambient_temp
        return delta * self.wind_speed * 0.002

    def _evaporative_cooling(self) -> float:
        """Cooling from evaporation/transpiration (°C loss per step)."""
        # More evaporation when air is dry and warm
        humidity_deficit = (100.0 - self.humidity) / 100.0
        temp_drive = max(0, self.air_temp - 15.0) / 15.0
        return humidity_deficit * temp_drive * 0.08

    def _humidity_evolution(self, temp_change: float) -> float:
        """
        Humidity change from temperature change + evaporation.
        Warmer air can hold more water → relative humidity drops.
        Evaporation adds moisture → relative humidity rises.
        """
        # Temperature effect: warmer = lower RH (air expands, same water = lower %)
        temp_effect = -temp_change * 1.5

        # Evaporation adds moisture
        evap_drive = max(0, self.air_temp - 10.0) / 20.0
        evap_from_soil = 0.15 * evap_drive * (1.0 - self.cloud_cover * 0.3)

        # Rain adds humidity directly
        rain_effect = self.rain_rate * 3.0

        return temp_effect + evap_from_soil + rain_effect

    def step(self, dt_minutes: float = 1.0) -> Dict:
        """
        Advance weather by dt_minutes. Returns causal chain entries.
        """
        minute = self.sim_minute
        causes = []

        # 1. Solar heating
        solar_heat = self._solar_heating(minute) * dt_minutes
        causes.append({
            "from": "Sunlight",
            "to": "Air Temperature",
            "delta": round(solar_heat, 4),
            "direction": "increase",
        })

        # 2. Cooling (radiative + convective + evaporative)
        rad_cool = self._radiative_cooling() * dt_minutes
        conv_cool = self._convective_cooling() * dt_minutes
        evap_cool = self._evaporative_cooling() * dt_minutes
        total_cooling = rad_cool + conv_cool + evap_cool

        causes.append({
            "from": "Radiative Cooling",
            "to": "Air Temperature",
            "delta": round(-rad_cool, 4),
            "direction": "decrease",
        })
        causes.append({
            "from": "Wind",
            "to": "Air Temperature",
            "delta": round(-conv_cool, 4),
            "direction": "decrease",
        })
        causes.append({
            "from": "Evaporation",
            "to": "Air Temperature",
            "delta": round(-evap_cool, 4),
            "direction": "decrease",
        })

        # 3. Net temperature change
        temp_change = solar_heat - total_cooling + self.scenario_temp_offset * dt_minutes
        old_temp = self.air_temp
        self.air_temp = max(-5.0, min(55.0, self.air_temp + temp_change))

        causes.append({
            "from": "Air Temperature (prev)",
            "to": "Air Temperature",
            "delta": round(self.air_temp - old_temp, 4),
            "direction": "increase" if temp_change > 0 else "decrease",
        })

        # 4. Humidity evolution
        hum_change = self._humidity_evolution(temp_change) * dt_minutes
        hum_change += self.scenario_humidity_offset * dt_minutes
        old_hum = self.humidity
        self.humidity = max(5.0, min(100.0, self.humidity + hum_change))

        causes.append({
            "from": "Temperature + Evaporation",
            "to": "Humidity",
            "delta": round(self.humidity - old_hum, 4),
            "direction": "increase" if hum_change > 0 else "decrease",
        })

        # 5. Rain
        self.rain_rate = self.scenario_rain_boost
        if self.rain_rate > 0:
            causes.append({
                "from": "Rain",
                "to": "Soil Moisture",
                "delta": round(self.rain_rate, 4),
                "direction": "increase",
            })

        # 6. Cloud cover
        self.cloud_cover = max(0.0, min(1.0, self.scenario_cloud_boost))

        # 7. Advance time
        self.sim_minute = (self.sim_minute + dt_minutes) % 1440  # wrap at 24h

        return causes


# ============================================================
# Soil Engine
# ============================================================

class SoilEngine:
    """
    Simulates soil moisture, soil temperature, evaporation,
    infiltration, drainage, and irrigation.
    """

    def __init__(self):
        self.soil_moisture = 60.0     # % of field capacity
        self.soil_temp = 24.0         # °C
        self.surface_water = 0.0      # mm of standing water
        self.irrigation_active = False
        self.irrigation_amount = IRRIGATION_RATE  # % per step when active

    def step(self, dt_minutes: float, air_temp: float, humidity: float,
             rain_rate: float, daylight: float) -> Dict:
        """
        Advance soil state. Returns causal chain entries.
        """
        causes = []

        # 1. Soil temperature evolution
        # Follows air temp with thermal inertia
        temp_diff = air_temp - self.soil_temp
        soil_temp_change = temp_diff * THERMAL_COUPLING_AIR_SOIL * dt_minutes
        # Solar heating of soil surface
        solar_soil_heat = daylight * 0.00003 * dt_minutes
        old_soil_temp = self.soil_temp
        self.soil_temp = self.soil_temp * THERMAL_INERTIA_SOIL + \
                         (self.soil_temp + soil_temp_change + solar_soil_heat) * \
                         (1.0 - THERMAL_INERTIA_SOIL)
        self.soil_temp = max(0.0, min(45.0, self.soil_temp))

        causes.append({
            "from": "Air Temperature",
            "to": "Soil Temperature",
            "delta": round(self.soil_temp - old_soil_temp, 4),
            "direction": "increase" if self.soil_temp > old_soil_temp else "decrease",
        })

        # 2. Evaporation from soil surface
        humidity_deficit = (100.0 - humidity) / 100.0
        evap_drive = humidity_deficit * max(0, air_temp - 5.0) / 25.0
        evaporation = EVAPORATION_RATE_BASE * evap_drive * self.soil_moisture * dt_minutes
        evaporation = min(evaporation, self.soil_moisture)  # can't evaporate more than available

        causes.append({
            "from": "Humidity Deficit + Temperature",
            "to": "Soil Moisture",
            "delta": round(-evaporation, 4),
            "direction": "decrease",
        })

        # 3. Infiltration (rain → soil)
        infiltration = 0.0
        if rain_rate > 0:
            infiltration = rain_rate * INFILTRATION_RATE * dt_minutes
            self.surface_water += rain_rate * dt_minutes - infiltration

        # 4. Drainage (excess water leaves)
        drainage = 0.0
        if self.soil_moisture > SOIL_FIELD_CAPACITY:
            excess = self.soil_moisture - SOIL_FIELD_CAPACITY
            drainage = excess * DRAINAGE_RATE * dt_minutes

        # 5. Irrigation
        irrigation_added = 0.0
        if self.irrigation_active:
            irrigation_added = self.irrigation_amount * dt_minutes
            causes.append({
                "from": "Irrigation",
                "to": "Soil Moisture",
                "delta": round(irrigation_added, 4),
                "direction": "increase",
            })

        # 6. Net soil moisture change
        old_moisture = self.soil_moisture
        self.soil_moisture += infiltration + irrigation_added - evaporation - drainage
        self.soil_moisture = max(0.0, min(100.0, self.soil_moisture))

        causes.append({
            "from": "Water Balance",
            "to": "Soil Moisture",
            "delta": round(self.soil_moisture - old_moisture, 4),
            "direction": "increase" if self.soil_moisture > old_moisture else ("decrease" if self.soil_moisture < old_moisture else "stable"),
        })

        return causes


# ============================================================
# Plant Physiology Engine
# ============================================================

class PlantPhysiology:
    """
    Simulates leaf temperature, transpiration, photosynthesis,
    respiration, water uptake, growth, stress accumulation, and recovery.
    """

    def __init__(self):
        self.leaf_temp = 30.0          # °C
        self.transpiration_rate = 0.0  # g/m²/min
        self.photosynthesis_rate = 0.0 # relative (0–1)
        self.respiration_rate = 0.0    # relative
        self.water_uptake = 0.0        # % soil moisture consumed per step
        self.growth = 0.0              # cumulative growth units
        self.stress = 0.0              # 0–100 accumulated stress
        self.stress_recovery = 0.0     # recovery counter

    def _leaf_energy_balance(self, air_temp: float, humidity: float,
                             daylight: float, wind_speed: float) -> float:
        """
        Compute leaf temperature from energy balance.
        Uses equilibrium approach: leaf temp converges toward a target
        determined by solar load minus cooling, with thermal inertia.

        The leaf does NOT diverge — it approaches equilibrium asymptotically.
        """
        # --- Compute equilibrium target temperature ---
        # Solar heating drives leaf temp above air temp
        solar_heating = daylight * 0.5 * 0.003  # °C equivalent at equilibrium

        # Longwave radiative cooling to sky (drives leaf below air at night)
        T_air_K = air_temp + 273.15
        T_sky_K = 260.0
        lw_flux = STEFAN_BOLTZMANN * LEAF_EMISSIVITY * (T_air_K**4 - T_sky_K**4)
        lw_cooling = lw_flux * 0.000015  # °C equivalent

        # Transpirational cooling (depends on VPD)
        vpd = self._vapor_pressure_deficit(air_temp, humidity)
        trans_cooling = vpd * 0.8  # °C equivalent at equilibrium

        # Equilibrium leaf temp = air temp + solar gain - radiative loss - transpirational loss
        equilibrium_leaf = air_temp + solar_heating - lw_cooling - trans_cooling

        # --- Thermal inertia: leaf approaches equilibrium gradually ---
        # Leaf has low thermal mass — converges ~30% per minute toward equilibrium
        convergence_rate = 0.30
        new_leaf_temp = self.leaf_temp + (equilibrium_leaf - self.leaf_temp) * convergence_rate

        # Clamp to physical bounds
        return max(0.0, min(55.0, new_leaf_temp))

    def _vapor_pressure_deficit(self, air_temp: float, humidity: float) -> float:
        """VPD in kPa — drives transpiration."""
        # Saturation vapor pressure (Tetens equation)
        es = 0.6108 * math.exp(17.27 * air_temp / (air_temp + 237.3))
        ea = es * humidity / 100.0
        return max(0.0, es - ea)

    def _compute_transpiration(self, air_temp: float, humidity: float,
                                soil_moisture: float, daylight: float) -> float:
        """Transpiration rate (relative 0–1 scale)."""
        vpd = self._vapor_pressure_deficit(air_temp, humidity)
        # Stomatal conductance: opens with light, closes when dry soil
        light_factor = min(1.0, daylight / 500.0)
        soil_factor = max(0.0, min(1.0, (soil_moisture - SOIL_WILTING_POINT) /
                                   (SOIL_FIELD_CAPACITY - SOIL_WILTING_POINT)))
        return TRANSPIRATION_RATE_BASE * vpd * light_factor * soil_factor * 10.0

    def _compute_photosynthesis(self, daylight: float, leaf_temp: float) -> float:
        """Photosynthesis rate (relative 0–1 scale)."""
        # Light response curve (Michaelis-Menten)
        light_factor = daylight / (daylight + 200.0)

        # Temperature response (bell curve around optimum)
        temp_diff = leaf_temp - PHOTOSYNTHESIS_TEMP_OPTIMUM
        temp_factor = math.exp(-(temp_diff**2) / (2 * PHOTOSYNTHESIS_TEMP_HALF_WIDTH**2))

        return light_factor * temp_factor

    def _compute_respiration(self, leaf_temp: float) -> float:
        """Respiration rate (relative 0–1 scale). Q10 model."""
        q10_factor = RESPIRATION_Q10 ** ((leaf_temp - RESPIRATION_BASE_TEMP) / 10.0)
        return 0.02 * q10_factor  # base respiration ~2% of max photosynthesis

    def step(self, dt_minutes: float, air_temp: float, humidity: float,
             soil_moisture: float, daylight: float, wind_speed: float) -> Dict:
        """
        Advance plant physiology. Returns causal chain entries.
        """
        causes = []

        # 1. Leaf temperature from energy balance
        old_leaf_temp = self.leaf_temp
        self.leaf_temp = self._leaf_energy_balance(air_temp, humidity, daylight, wind_speed)
        self.leaf_temp = max(0.0, min(55.0, self.leaf_temp))

        leaf_temp_delta = self.leaf_temp - air_temp

        causes.append({
            "from": "Sunlight + Air Temperature",
            "to": "Leaf Temperature",
            "delta": round(self.leaf_temp - old_leaf_temp, 4),
            "direction": "increase" if self.leaf_temp > old_leaf_temp else "decrease",
        })

        # 2. Transpiration
        self.transpiration_rate = self._compute_transpiration(
            air_temp, humidity, soil_moisture, daylight) * dt_minutes

        causes.append({
            "from": "Leaf Temperature + VPD",
            "to": "Transpiration",
            "delta": round(self.transpiration_rate, 4),
            "direction": "increase",
        })

        # 3. Water uptake from soil (driven by transpiration)
        self.water_uptake = self.transpiration_rate * 0.5 * dt_minutes

        causes.append({
            "from": "Transpiration",
            "to": "Water Loss (Soil)",
            "delta": round(-self.water_uptake, 4),
            "direction": "decrease",
        })

        # 4. Photosynthesis
        self.photosynthesis_rate = self._compute_photosynthesis(daylight, self.leaf_temp)

        causes.append({
            "from": "Sunlight + Leaf Temperature",
            "to": "Photosynthesis",
            "delta": round(self.photosynthesis_rate, 4),
            "direction": "increase",
        })

        # 5. Respiration
        self.respiration_rate = self._compute_respiration(self.leaf_temp) * dt_minutes

        causes.append({
            "from": "Leaf Temperature",
            "to": "Respiration",
            "delta": round(self.respiration_rate, 4),
            "direction": "increase",
        })

        # 6. Net carbon gain → Growth
        net_carbon = self.photosynthesis_rate - self.respiration_rate
        growth_increment = max(0.0, net_carbon) * GROWTH_RATE_BASE * dt_minutes
        self.growth += growth_increment

        causes.append({
            "from": "Photosynthesis - Respiration",
            "to": "Growth",
            "delta": round(growth_increment, 6),
            "direction": "increase" if growth_increment > 0 else "decrease",
        })

        # 7. Stress accumulation
        # Stress increases when: leaf temp too high, VPD too high, soil too dry
        stress_triggers = 0
        if leaf_temp_delta > 4.0:
            stress_triggers += 1
        if self._vapor_pressure_deficit(air_temp, humidity) > 2.5:
            stress_triggers += 1
        if soil_moisture < SOIL_WILTING_POINT + 10:
            stress_triggers += 1

        if stress_triggers > 0:
            self.stress = min(100.0, self.stress + stress_triggers * STRESS_ACCUMULATION_RATE * dt_minutes)
            self.stress_recovery = 0
            causes.append({
                "from": "Environmental Stressors",
                "to": "Stress Accumulation",
                "delta": round(stress_triggers * STRESS_ACCUMULATION_RATE * dt_minutes, 4),
                "direction": "increase",
            })
        else:
            # Recovery when no stressors
            self.stress_recovery += dt_minutes
            if self.stress_recovery > 30:  # need 30 min of good conditions
                recovery_amount = RECOVERY_RATE * dt_minutes
                self.stress = max(0.0, self.stress - recovery_amount)
                causes.append({
                    "from": "Recovery",
                    "to": "Stress",
                    "delta": round(-recovery_amount, 4),
                    "direction": "decrease",
                })

        # 8. Growth reduction from stress
        if self.stress > 30:
            stress_growth_penalty = self.stress / 100.0
            causes.append({
                "from": "Stress Accumulation",
                "to": "Growth Reduction",
                "delta": round(-stress_growth_penalty, 4),
                "direction": "decrease",
            })

        return causes


# ============================================================
# Virtual Sensors
# ============================================================

class VirtualSensors:
    """
    Reads the current state of Weather, Soil, and Plant engines
    and outputs the exact JSON schema accepted by POST /analyze.

    This is the bridge: Simulator → same format as ESP32 hardware.
    """

    @staticmethod
    def read(weather: WeatherEngine, soil: SoilEngine, plant: PlantPhysiology,
             prev_air_temp: float = None, prev_humidity: float = None,
             prev_leaf_temp_delta: float = None) -> Dict:
        """
        Produce sensor_data dict matching /analyze expected schema.
        """
        air_temp = round(weather.air_temp, 2)
        humidity = round(weather.humidity, 2)
        leaf_temp = round(plant.leaf_temp, 2)
        leaf_temp_delta = round(plant.leaf_temp - weather.air_temp, 2)

        # Rate computations (change from previous step)
        air_temp_rate = round(air_temp - (prev_air_temp or air_temp), 2)
        humidity_rate = round(humidity - (prev_humidity or humidity), 2)
        leaf_temp_rate = round(leaf_temp_delta - (prev_leaf_temp_delta or leaf_temp_delta), 2)

        return {
            "air_temp": air_temp,
            "humidity": humidity,
            "light": round(weather.daylight(weather.sim_minute), 2),
            "leaf_temp": leaf_temp,
            "soil_moisture": round(soil.soil_moisture, 2),
            "soil_temp": round(soil.soil_temp, 2),
            "air_temp_rate": air_temp_rate,
            "humidity_rate": humidity_rate,
            "leaf_temp_rate": leaf_temp_rate,
            "leaf_temp_delta": leaf_temp_delta,
            # Extended fields for history / frontend
            "co2": 420.0,  # ppm — ambient baseline
            "wind_speed": round(weather.wind_speed, 2),
            "cloud_cover": round(weather.cloud_cover, 2),
            "rain_rate": round(weather.rain_rate, 2),
            "vpd": round(plant._vapor_pressure_deficit(air_temp, humidity), 3),
            "transpiration": round(plant.transpiration_rate, 4),
            "photosynthesis": round(plant.photosynthesis_rate, 4),
            "growth": round(plant.growth, 6),
            "stress": round(plant.stress, 2),
        }


# ============================================================
# Greenhouse Simulator (Orchestrator)
# ============================================================

class GreenhouseSimulator:
    """
    Top-level orchestrator that ties Weather, Soil, and Plant engines
    together and exposes control interface (start, pause, reset, step).

    Usage:
        sim = GreenhouseSimulator()
        sim.set_scenario("heat_wave")
        sim.start()
        for _ in range(60):
            state = sim.step()
            # state["sensor_data"] → POST /analyze
    """

    def __init__(self):
        self.weather = WeatherEngine()
        self.soil = SoilEngine()
        self.plant = PlantPhysiology()

        # State
        self.running = False
        self.speed = 1.0          # simulation minutes per real second
        self.current_scenario = "normal_day"
        self.scenario_elapsed = 0.0  # minutes since scenario started

        # History
        self.history: List[Dict] = []
        self.max_history = 1440  # store up to 24h of minute-by-minute data

        # Previous values for rate computation
        self._prev_air_temp: Optional[float] = None
        self._prev_humidity: Optional[float] = None
        self._prev_leaf_temp_delta: Optional[float] = None

        # Causal chain for current step
        self.causal_chain: List[Dict] = []

    # ----- Control -----

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def reset(self):
        """Full reset to initial conditions."""
        self.__init__()

    def set_speed(self, multiplier: float):
        """Set simulation speed. 1.0 = real-time, 60.0 = 1 hour per second."""
        self.speed = max(0.1, min(600.0, multiplier))

    def set_scenario(self, scenario_name: str):
        """Apply a scenario from the scenario catalog."""
        from backend.simulator.scenarios import apply_scenario
        apply_scenario(self, scenario_name)
        self.current_scenario = scenario_name
        self.scenario_elapsed = 0.0

    # ----- Time -----

    def sim_time_str(self) -> str:
        """Return current simulation time as HH:MM string."""
        minute = int(self.weather.sim_minute) % 1440
        h = minute // 60
        m = minute % 60
        return f"{h:02d}:{m:02d}"

    def sim_day_phase(self) -> str:
        """Return 'day' or 'night' based on sun position."""
        m = self.weather.sim_minute % 1440
        return "day" if SUNRISE_MINUTE <= m <= SUNSET_MINUTE else "night"

    # ----- Step -----

    def step(self, dt_minutes: float = None, analysis: Dict = None) -> Dict:
        """
        Advance the simulation by dt_minutes (default: speed * 1 real second).
        Returns complete state dict including sensor_data for /analyze.

        If 'analysis' is provided (from run_unified_pipeline), it is attached
        to the history entry as a snapshot for later comparison/replay.
        """
        if dt_minutes is None:
            dt_minutes = self.speed  # one real second = speed sim-minutes

        self.causal_chain = []

        # 1. Weather step
        weather_causes = self.weather.step(dt_minutes)
        self.causal_chain.extend(weather_causes)

        # 2. Soil step
        soil_causes = self.soil.step(
            dt_minutes,
            air_temp=self.weather.air_temp,
            humidity=self.weather.humidity,
            rain_rate=self.weather.rain_rate,
            daylight=self.weather.daylight(self.weather.sim_minute),
        )
        self.causal_chain.extend(soil_causes)

        # 3. Apply transpiration water loss to soil
        water_loss = self.plant.water_uptake if hasattr(self.plant, 'water_uptake') else 0.0
        if water_loss > 0:
            self.soil.soil_moisture = max(0.0, self.soil.soil_moisture - water_loss)

        # 4. Plant physiology step
        plant_causes = self.plant.step(
            dt_minutes,
            air_temp=self.weather.air_temp,
            humidity=self.weather.humidity,
            soil_moisture=self.soil.soil_moisture,
            daylight=self.weather.daylight(self.weather.sim_minute),
            wind_speed=self.weather.wind_speed,
        )
        self.causal_chain.extend(plant_causes)

        # 5. Read virtual sensors
        sensor_data = VirtualSensors.read(
            self.weather, self.soil, self.plant,
            prev_air_temp=self._prev_air_temp,
            prev_humidity=self._prev_humidity,
            prev_leaf_temp_delta=self._prev_leaf_temp_delta,
        )

        # Store previous values for next rate computation
        self._prev_air_temp = sensor_data["air_temp"]
        self._prev_humidity = sensor_data["humidity"]
        self._prev_leaf_temp_delta = sensor_data["leaf_temp_delta"]

        # 6. Build state dict
        state = {
            "sim_time": self.sim_time_str(),
            "sim_minute": int(self.weather.sim_minute) % 1440,
            "day_phase": self.sim_day_phase(),
            "scenario": self.current_scenario,
            "scenario_elapsed": round(self.scenario_elapsed, 1),
            "running": self.running,
            "speed": self.speed,
            "sensor_data": sensor_data,
            "causal_chain": list(self.causal_chain),
            "weather": {
                "air_temp": self.weather.air_temp,
                "humidity": self.weather.humidity,
                "cloud_cover": self.weather.cloud_cover,
                "rain_rate": self.weather.rain_rate,
                "wind_speed": self.weather.wind_speed,
                "daylight": self.weather.daylight(self.weather.sim_minute),
                "sun_elevation": self.weather.sun_elevation(self.weather.sim_minute),
            },
            "soil": {
                "soil_moisture": self.soil.soil_moisture,
                "soil_temp": self.soil.soil_temp,
                "surface_water": self.soil.surface_water,
                "irrigation_active": self.soil.irrigation_active,
            },
            "plant": {
                "leaf_temp": self.plant.leaf_temp,
                "leaf_temp_delta": sensor_data["leaf_temp_delta"],
                "transpiration": self.plant.transpiration_rate,
                "photosynthesis": self.plant.photosynthesis_rate,
                "respiration": self.plant.respiration_rate,
                "water_uptake": self.plant.water_uptake,
                "growth": self.plant.growth,
                "stress": self.plant.stress,
            },
        }

        # 7. Attach analysis snapshot if provided (for historical comparison)
        if analysis:
            state["analysis_snapshot"] = {
                "temporal_prediction": analysis.get("temporal_prediction"),
                "stress_analysis": analysis.get("stress_analysis"),
                "biology_analysis": analysis.get("biology_analysis"),
                "recommendations": analysis.get("recommendations"),
                "confidence": analysis.get("confidence"),
                "ai_reasoning": analysis.get("ai_reasoning"),
                "decision_input": analysis.get("decision_input"),
            }

        # 8. Store in history
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # 9. Track scenario elapsed time
        self.scenario_elapsed += dt_minutes

        return state

    def get_history(self, n_steps: int = None) -> List[Dict]:
        """Return the last n_steps from history (all if None)."""
        if n_steps is None:
            return list(self.history)
        return self.history[-n_steps:]

    def get_history_sensor_stream(self, n_steps: int = None) -> List[Dict]:
        """Return just the sensor_data from history for temporal AI consumption."""
        history = self.get_history(n_steps)
        return [h["sensor_data"] for h in history]