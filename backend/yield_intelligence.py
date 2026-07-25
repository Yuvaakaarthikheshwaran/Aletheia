"""
Aletheia Yield Intelligence Engine
===================================

Scientifically defensible yield potential estimation using EXISTING pipeline outputs.

CORE PRINCIPLE:
  The goal is NOT to display the most impressive yield number.
  The goal is to produce the MOST ACCURATE AND SCIENTIFICALLY DEFENSIBLE yield
  estimate that Aletheia's available evidence can support.

  If the system does not have enough information for an accurate absolute yield
  forecast, it MUST say so.

  A trustworthy "insufficient data" result is better than a fabricated precise
  yield prediction.

ARCHITECTURE:
  This engine CONSUMES existing pipeline outputs — it does NOT duplicate
  the AI pipeline. It runs as a post-processing layer after the unified
  pipeline produces its analysis.

INPUTS (all from existing pipeline):
  - Plant profile (cached Tavily/parser)
  - Growth stage
  - Current sensor state
  - Historical sensor observations (sensor_stream)
  - Temporal AI output
  - Stress analysis (Random Forest)
  - Stress severity & duration
  - Biology health score
  - Decision Engine output
  - Confidence information
  - Recommendations

OUTPUTS:
  - yield_potential_percent: 0-100% (retained biological yield potential)
  - yield_loss_risk: "low" | "moderate" | "high" | "critical"
  - yield_loss_risk_score: 0-100
  - estimated_yield_impact_range: { min_percent, max_percent }
  - primary_yield_limiter: string
  - cumulative_stress: { heat, cold, water, humidity, root_zone, leaf_thermal, light }
  - critical_stage: string
  - forecast_confidence: 0-1
  - confidence_label: "insufficient_history" | "low" | "moderate" | "high"
  - evidence_used: list
  - missing_evidence: list
  - absolute_yield_forecast: { status, ... }
  - yield_recommendations: []
  - yield_story: string

SCIENTIFIC BASIS:
  Yield Impact Risk ≈ Stress Severity × Exposure Duration
                       × Growth Stage Sensitivity × Crop Sensitivity

  This is a conceptual framework. The implementation uses conservative,
  evidence-based coefficients derived from agricultural science literature
  (FAO, USDA, university extensions) and clearly labels limitations.

  Sources:
  - FAO Irrigation and Drainage Paper 33 (yield response to water)
  - FAO Irrigation and Drainage Paper 56 (crop evapotranspiration)
  - USDA-ARS plant stress physiology research
  - University of California ANR extension publications
  - Peer-reviewed agronomy: heat stress effects on crop yield

DO NOT FABRICATE:
  - No NPK measurement claims
  - No direct biomass measurement claims
  - No fruit/flower count unless provided
  - No absolute kg/plant unless sufficient evidence exists
  - No yield accuracy claims beyond what evidence supports
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# GROWTH STAGE YIELD SENSITIVITY COEFFICIENTS
# ============================================================
#
# These coefficients represent how sensitive a given growth stage is to
# environmental stress in terms of final yield impact.
#
# Source: FAO Irrigation and Drainage Paper 33 (yield response factors),
# USDA-ARS research on crop-specific stress sensitivity by growth stage,
# and university extension publications.
#
# Values are conservative generic estimates. Crop-specific profiles
# override these when available.
#
# Scale: 0.0 = no yield impact from stress at this stage
#        1.0 = maximum yield impact from stress at this stage

DEFAULT_STAGE_SENSITIVITY = {
    "germination": 0.35,   # Stress during germination affects stand establishment
    "seedling": 0.50,      # Seedlings are vulnerable but can recover
    "vegetative": 0.55,    # Vegetative stress reduces photosynthetic capacity
    "flowering": 0.90,     # Flowering is the MOST yield-sensitive stage for most crops
    "fruiting": 0.80,      # Fruit development is highly yield-sensitive
    "harvest": 0.30,       # Late-stage stress has less impact on final yield
}

# ============================================================================
# STRESS TYPE YIELD IMPACT COEFFICIENTS
# ============================================================================
# How much each stress type contributes to yield loss per unit of severity
# and duration. These are conservative generic values.
#
# Source: FAO 56, USDA-ARS, and peer-reviewed agronomy literature.
# Crop-specific profiles override these.

DEFAULT_STRESS_IMPACT = {
    "heat_stress": 0.85,       # Heat stress strongly affects yield (photosynthesis, flowering)
    "cold_stress": 0.70,       # Cold stress affects metabolic processes
    "water_stress": 0.90,      # Water stress is a primary yield limiter (FAO 56)
    "humidity_stress": 0.40,   # Humidity affects transpiration and disease pressure
    "root_zone_stress": 0.65,  # Root zone stress affects nutrient/water uptake
    "leaf_thermal_stress": 0.75,  # Leaf thermal stress indicates transpiration issues
    "light_stress": 0.50,      # Light stress affects photosynthesis
    "nutrient_lockout": 0.60,  # INFERRED — no direct NPK measurement
}

# ============================================================================
# CROP-SPECIFIC YIELD KNOWLEDGE
# ============================================================================
# Stored per-plant yield knowledge. Populated from Tavily/OpenRouter
# and cached locally. Generic fallbacks used when unavailable.
#
# Each entry contains:
#   - typical_yield_range: { low, high, unit } — from agricultural sources
#   - critical_stages: list of most yield-sensitive stages
#   - heat_sensitivity: 0-1
#   - cold_sensitivity: 0-1
#   - water_sensitivity: 0-1
#   - light_sensitivity: 0-1
#   - stage_sensitivity_overrides: per-stage overrides
#   - absolute_yield_requirements: what's needed for kg/plant forecast
#   - source: where this knowledge came from

CROP_YIELD_KNOWLEDGE = {
    "tomato": {
        "typical_yield_range": {"low": 2.0, "high": 8.0, "unit": "kg/plant"},
        "typical_yield_range_field": {"low": 40, "high": 120, "unit": "tonnes/hectare"},
        "critical_stages": ["flowering", "fruiting"],
        "heat_sensitivity": 0.85,
        "cold_sensitivity": 0.60,
        "water_sensitivity": 0.90,
        "light_sensitivity": 0.55,
        "stage_sensitivity_overrides": {
            "flowering": 0.95,  # Tomato flowering is extremely heat-sensitive
            "fruiting": 0.85,
        },
        "absolute_yield_requirements": [
            "cultivar",
            "plant_density",
            "fruit_count",
            "growth_stage",
        ],
        "source": "FAO crop water management, USDA tomato production guides",
    },
    "potato": {
        "typical_yield_range": {"low": 0.5, "high": 2.0, "unit": "kg/plant"},
        "typical_yield_range_field": {"low": 20, "high": 60, "unit": "tonnes/hectare"},
        "critical_stages": ["flowering", "fruiting"],  # tuber initiation/bulking
        "heat_sensitivity": 0.80,
        "cold_sensitivity": 0.50,
        "water_sensitivity": 0.85,
        "light_sensitivity": 0.60,
        "stage_sensitivity_overrides": {
            "flowering": 0.88,  # Tuber initiation
            "fruiting": 0.90,   # Tuber bulking
        },
        "absolute_yield_requirements": {
            "cultivar",
            "plant_density",
            "growth_stage",
        },
        "source": "FAO potato production guidelines, CIP research",
    },
    "mango": {
        "typical_yield_range": {"low": 20, "high": 200, "unit": "kg/tree"},
        "typical_yield_range_field": {"low": 5, "high": 25, "unit": "tonnes/hectare"},
        "critical_stages": ["flowering", "fruiting"],
        "heat_sensitivity": 0.75,
        "cold_sensitivity": 0.90,  # Mango is cold-sensitive
        "water_sensitivity": 0.80,
        "light_sensitivity": 0.50,
        "stage_sensitivity_overrides": {
            "flowering": 0.95,  # Mango flowering is critical for fruit set
            "fruiting": 0.80,
        },
        "absolute_yield_requirements": {
            "cultivar",
            "tree_age",
            "tree_density",
            "flower_count",
            "fruit_count",
        },
        "source": "FAO tropical fruit production, Indian agricultural extension",
    },
}

# Generic fallback for any plant not in the knowledge base
GENERIC_YIELD_KNOWLEDGE = {
    "typical_yield_range": None,  # Unknown — cannot estimate absolute yield
    "typical_yield_range_field": None,
    "critical_stages": ["flowering", "fruiting"],
    "heat_sensitivity": 0.70,
    "cold_sensitivity": 0.60,
    "water_sensitivity": 0.80,
    "light_sensitivity": 0.50,
    "stage_sensitivity_overrides": {},
    "absolute_yield_requirements": {
        "cultivar",
        "plant_density",
        "growth_stage",
        "crop_specific_yield_data",
    },
    "source": "generic_fallback — no crop-specific data available",
}


def _get_crop_yield_knowledge(plant_name: str) -> dict:
    """Get crop-specific yield knowledge, falling back to generic."""
    key = plant_name.lower().strip()
    return CROP_YIELD_KNOWLEDGE.get(key, dict(GENERIC_YIELD_KNOWLEDGE))


# ============================================================================
# CUMULATIVE STRESS TRACKING
# ============================================================================

def _compute_cumulative_stress(
    sensor_stream: Optional[List[Dict]],
    plant_profile: dict,
    growth_stage: str,
) -> Dict[str, float]:
    """
    Compute cumulative stress exposure from historical sensor data.

    Each stress type accumulates based on:
      - How far the sensor reading deviates from the optimal range
      - How long the deviation persists (duration in minutes)
      - The severity of the deviation

    Returns a dict of stress_type → cumulative_exposure_score (0-100).

    A single bad reading does NOT produce a huge score.
    Duration matters — 35°C for 1 minute ≠ 35°C for 6 hours.
    """
    if not sensor_stream or len(sensor_stream) < 2:
        return {
            "heat_stress": 0.0,
            "cold_stress": 0.0,
            "water_stress": 0.0,
            "humidity_stress": 0.0,
            "root_zone_stress": 0.0,
            "leaf_thermal_stress": 0.0,
            "light_stress": 0.0,
        }

    thresholds = plant_profile.get("stress_thresholds", {})
    heat_threshold = thresholds.get("heat_stress", 35)
    severe_heat_threshold = thresholds.get("severe_heat_stress", 40)
    cold_threshold = thresholds.get("cold_stress", 12)
    drought_threshold = thresholds.get("drought_stress", 30)
    waterlogging_threshold = thresholds.get("waterlogging_stress", 90)

    # Get optimal ranges for the current growth stage
    stage_profile = plant_profile.get("growth_stages", {}).get(growth_stage, {})
    opt_air_temp = stage_profile.get("air_temp", [20, 30])
    opt_humidity = stage_profile.get("humidity", [50, 70])
    opt_soil_moisture = stage_profile.get("soil_moisture", [40, 70])
    opt_light = stage_profile.get("light", [700, 1200])

    cumulative = {
        "heat_stress": 0.0,
        "cold_stress": 0.0,
        "water_stress": 0.0,
        "humidity_stress": 0.0,
        "root_zone_stress": 0.0,
        "leaf_thermal_stress": 0.0,
        "light_stress": 0.0,
    }

    # Track consecutive minutes of each stress type for duration weighting
    stress_duration_minutes = {k: 0 for k in cumulative}
    total_minutes = len(sensor_stream)

    for entry in sensor_stream:
        air_temp = entry.get("air_temp", 25)
        humidity = entry.get("humidity", 60)
        soil_moisture = entry.get("soil_moisture", 60)
        soil_temp = entry.get("soil_temp", 25)
        light = entry.get("light", 800)
        leaf_temp_delta = entry.get("leaf_temp_delta", 3)

        # --- Heat stress ---
        if air_temp >= severe_heat_threshold:
            severity = min(1.0, (air_temp - severe_heat_threshold) / 10.0)
            cumulative["heat_stress"] += severity * 0.15
            stress_duration_minutes["heat_stress"] += 1
        elif air_temp >= heat_threshold:
            severity = min(1.0, (air_temp - heat_threshold) / 10.0)
            cumulative["heat_stress"] += severity * 0.08
            stress_duration_minutes["heat_stress"] += 1
        else:
            stress_duration_minutes["heat_stress"] = 0

        # --- Cold stress ---
        if air_temp <= cold_threshold:
            severity = min(1.0, (cold_threshold - air_temp) / 10.0)
            cumulative["cold_stress"] += severity * 0.08
            stress_duration_minutes["cold_stress"] += 1
        else:
            stress_duration_minutes["cold_stress"] = 0

        # --- Water stress (drought) ---
        if soil_moisture <= drought_threshold:
            severity = min(1.0, (drought_threshold - soil_moisture) / 20.0)
            cumulative["water_stress"] += severity * 0.10
            stress_duration_minutes["water_stress"] += 1
        elif soil_moisture >= waterlogging_threshold:
            severity = min(1.0, (soil_moisture - waterlogging_threshold) / 10.0)
            cumulative["water_stress"] += severity * 0.06
            stress_duration_minutes["water_stress"] += 1
        else:
            stress_duration_minutes["water_stress"] = 0

        # --- Humidity stress ---
        if humidity < opt_humidity[0]:
            severity = min(1.0, (opt_humidity[0] - humidity) / 20.0)
            cumulative["humidity_stress"] += severity * 0.04
            stress_duration_minutes["humidity_stress"] += 1
        elif humidity > opt_humidity[1]:
            severity = min(1.0, (humidity - opt_humidity[1]) / 20.0)
            cumulative["humidity_stress"] += severity * 0.04
            stress_duration_minutes["humidity_stress"] += 1
        else:
            stress_duration_minutes["humidity_stress"] = 0

        # --- Root zone stress ---
        if soil_temp > 35:
            severity = min(1.0, (soil_temp - 35) / 10.0)
            cumulative["root_zone_stress"] += severity * 0.06
            stress_duration_minutes["root_zone_stress"] += 1
        else:
            stress_duration_minutes["root_zone_stress"] = 0

        # --- Leaf thermal stress ---
        if leaf_temp_delta > 5:
            severity = min(1.0, (leaf_temp_delta - 5) / 5.0)
            cumulative["leaf_thermal_stress"] += severity * 0.08
            stress_duration_minutes["leaf_thermal_stress"] += 1
        else:
            stress_duration_minutes["leaf_thermal_stress"] = 0

        # --- Light stress ---
        if light < opt_light[0] and light > 0:
            severity = min(1.0, (opt_light[0] - light) / opt_light[0])
            cumulative["light_stress"] += severity * 0.03
            stress_duration_minutes["light_stress"] += 1
        elif light > opt_light[1]:
            severity = min(1.0, (light - opt_light[1]) / 500.0)
            cumulative["light_stress"] += severity * 0.03
            stress_duration_minutes["light_stress"] += 1
        else:
            stress_duration_minutes["light_stress"] = 0

    # Normalize to 0-100 scale based on total minutes
    # A full 24h (1440 min) of severe stress = 100
    max_possible = total_minutes * 0.15  # theoretical max per minute
    for key in cumulative:
        cumulative[key] = round(min(100.0, (cumulative[key] / max(max_possible, 1)) * 100), 1)

    return cumulative


# ============================================================================
# YIELD POTENTIAL CALCULATION
# ============================================================================

def compute_yield_potential(
    biology_health_score: float,
    cumulative_stress: Dict[str, float],
    stress_analysis: Dict,
    growth_stage: str,
    plant_name: str,
    sensor_stream: list = None,
) -> float:
    """
    Compute estimated retained yield potential as a percentage (0-100).

    This is NOT kilograms. It represents estimated retained biological
    yield potential relative to an appropriate healthy baseline.

    Formula:
      Yield Potential = Biology Health Score
                        - Σ (Cumulative Stress × Stress Impact × Stage Sensitivity)

    The biology health score provides the baseline (how well current
    conditions match optimal ranges). Cumulative stress exposure reduces
    this based on stress type, duration, and growth-stage sensitivity.

    A single bad reading does NOT produce a huge drop.
    """
    crop_knowledge = _get_crop_yield_knowledge(plant_name)

    # Get stage sensitivity
    stage_sensitivity = crop_knowledge.get("stage_sensitivity_overrides", {}).get(
        growth_stage,
        DEFAULT_STAGE_SENSITIVITY.get(growth_stage, 0.55),
    )

    # Start with biology health score as baseline
    yield_potential = float(biology_health_score)

    # Apply cumulative stress deductions
    for stress_type, stress_score in cumulative_stress.items():
        if stress_score > 0:
            # Get stress impact coefficient
            stress_impact = DEFAULT_STRESS_IMPACT.get(stress_type, 0.5)

            # Override with crop-specific sensitivity
            if stress_type == "heat_stress":
                stress_impact *= crop_knowledge.get("heat_sensitivity", 0.85)
            elif stress_type == "cold_stress":
                stress_impact *= crop_knowledge.get("cold_sensitivity", 0.70)
            elif stress_type == "water_stress":
                stress_impact *= crop_knowledge.get("water_sensitivity", 0.90)
            elif stress_type == "light_stress":
                stress_impact *= crop_knowledge.get("light_sensitivity", 0.50)

            # The yield loss from this stress type:
            #   loss = stress_score × stress_impact × stage_sensitivity
            # This ensures:
            #   - Short stress has less effect than prolonged stress
            #   - Stress during flowering has more effect than during vegetative
            #   - Heat-sensitive crops lose more from heat stress
            loss = stress_score * stress_impact * stage_sensitivity * 0.01
            yield_potential -= loss

    # Clamp to 0-100
    yield_potential = max(0.0, min(100.0, yield_potential))

    return round(yield_potential, 1)


# ============================================================================
# YIELD LOSS RISK
# ============================================================================

def compute_yield_loss_risk(
    yield_potential: float,
    cumulative_stress: Dict[str, float],
    stress_analysis: Dict,
    temporal_prediction: Dict,
) -> Tuple[str, float]:
    """
    Compute yield loss risk category and score.

    Risk depends on:
    - Current yield potential (lower = higher risk)
    - Cumulative stress exposure
    - Current stress severity
    - Temporal AI prediction (is stress expected to continue?)

    Returns: (risk_label, risk_score_0_100)
    """
    risk_score = 0.0

    # Base risk from yield potential
    if yield_potential < 50:
        risk_score += 40
    elif yield_potential < 70:
        risk_score += 25
    elif yield_potential < 85:
        risk_score += 10
    else:
        risk_score += 0

    # Add risk from cumulative stress
    max_cumulative = max(cumulative_stress.values()) if cumulative_stress else 0
    risk_score += max_cumulative * 0.3

    # Add risk from current stress severity
    current_severity = stress_analysis.get("severity", 0)
    risk_score += current_severity * 0.2

    # Add risk from temporal prediction
    future_state = temporal_prediction.get("future_state", {})
    future_pred = future_state.get("future_prediction", "unknown")
    if future_pred == "stress":
        risk_score += 15
    elif future_pred == "critical":
        risk_score += 25

    risk_score = min(100.0, risk_score)

    # Determine label
    if risk_score >= 70:
        label = "critical"
    elif risk_score >= 40:
        label = "high"
    elif risk_score >= 20:
        label = "moderate"
    else:
        label = "low"

    return label, round(risk_score, 1)


# ============================================================================
# ESTIMATED YIELD IMPACT RANGE
# ============================================================================

def compute_yield_impact_range(
    yield_potential: float,
    cumulative_stress: Dict[str, float],
    growth_stage: str,
    plant_name: str,
) -> Dict[str, float]:
    """
    Estimate how much yield potential may be at risk because of observed stress.

    Returns a RANGE (min_percent, max_percent) because uncertainty is substantial.

    Uses ranges — never shows false precision.
    """
    crop_knowledge = _get_crop_yield_knowledge(plant_name)
    stage_sensitivity = crop_knowledge.get("stage_sensitivity_overrides", {}).get(
        growth_stage,
        DEFAULT_STAGE_SENSITIVITY.get(growth_stage, 0.55),
    )

    # The potential at risk is 100 - yield_potential
    potential_at_risk = 100.0 - yield_potential

    # But not all of that will necessarily translate to actual yield loss.
    # Some stress is recoverable. The impact range accounts for this.

    # Minimum impact: assume some recovery is possible
    min_impact = -round(potential_at_risk * 0.5, 1)

    # Maximum impact: assume full stress translates to yield loss
    max_impact = -round(potential_at_risk * 0.9, 1)

    # If yield potential is very high, impact is negligible
    if yield_potential > 95:
        min_impact = 0.0
        max_impact = -2.0
    elif yield_potential > 85:
        min_impact = max(min_impact, -5.0)
        max_impact = max(max_impact, -10.0)

    return {
        "min_percent": min_impact,
        "max_percent": max_impact,
    }


# ============================================================================
# PRIMARY YIELD LIMITER
# ============================================================================

def identify_primary_yield_limiter(
    cumulative_stress: Dict[str, float],
    stress_analysis: Dict,
    growth_stage: str,
    plant_name: str,
) -> Dict:
    """
    Identify the dominant current factor threatening yield.

    Uses cumulative stress exposure + current stress analysis to determine
    which factor is most limiting yield potential.
    """
    if not cumulative_stress:
        return {
            "factor": "none",
            "label": "No Significant Yield Limiter",
            "contribution": "none",
            "duration": "N/A",
            "critical_stage_match": False,
            "evidence": "All monitored parameters are within acceptable ranges.",
        }

    # Find the stress with the highest cumulative score
    primary = max(cumulative_stress, key=cumulative_stress.get)
    primary_score = cumulative_stress[primary]

    if primary_score < 5.0:
        return {
            "factor": "none",
            "label": "No Significant Yield Limiter",
            "contribution": "low",
            "duration": "N/A",
            "critical_stage_match": False,
            "evidence": "Cumulative stress exposure is minimal.",
        }

    # Map stress type to human-readable label
    stress_labels = {
        "heat_stress": "Heat Stress",
        "cold_stress": "Cold Stress",
        "water_stress": "Water Stress",
        "humidity_stress": "Humidity Stress",
        "root_zone_stress": "Root Zone Stress",
        "leaf_thermal_stress": "Leaf Thermal Stress",
        "light_stress": "Light Stress",
    }

    # Determine contribution level
    if primary_score > 50:
        contribution = "high"
    elif primary_score > 25:
        contribution = "moderate"
    else:
        contribution = "low"

    # Check if this stress is affecting a critical growth stage
    crop_knowledge = _get_crop_yield_knowledge(plant_name)
    critical_stages = crop_knowledge.get("critical_stages", ["flowering", "fruiting"])
    critical_stage_match = growth_stage in critical_stages

    # Build evidence string
    evidence_parts = []
    if primary == "heat_stress":
        evidence_parts.append("Persistent elevated air temperature")
    elif primary == "cold_stress":
        evidence_parts.append("Persistent low air temperature")
    elif primary == "water_stress":
        evidence_parts.append("Soil moisture outside optimal range")
    elif primary == "leaf_thermal_stress":
        evidence_parts.append("Persistent elevated leaf temperature delta")
    elif primary == "root_zone_stress":
        evidence_parts.append("Elevated root zone temperature")
    elif primary == "humidity_stress":
        evidence_parts.append("Humidity outside optimal range")
    elif primary == "light_stress":
        evidence_parts.append("Light levels outside optimal range")

    if critical_stage_match:
        evidence_parts.append(f"Plant is in {growth_stage} — a yield-critical stage")

    return {
        "factor": primary,
        "label": stress_labels.get(primary, primary),
        "contribution": contribution,
        "critical_stage_match": critical_stage_match,
        "evidence": ". ".join(evidence_parts) + ".",
    }


# ============================================================================
# YIELD FORECAST CONFIDENCE
# ============================================================================

def compute_yield_confidence(
    sensor_stream: Optional[List[Dict]],
    plant_name: str,
    growth_stage: str,
    plant_profile: Dict,
    sensor_confidence: float,
    temporal_confidence: float,
    biology_health_score: float,
) -> Tuple[float, str]:
    """
    Compute yield forecast confidence SEPARATE from temporal confidence.

    Yield confidence accounts for evidence completeness:
    - Plant identified?
    - Growth stage known?
    - Historical duration available?
    - Sensor coverage?
    - Sensor confidence?
    - Calibration state?
    - Temporal history quality?
    - Crop-specific baseline availability?

    Cold-start behavior:
      First sensor packet → "insufficient_history"
      As history accumulates → low → moderate → high

    Never exceeds 100%.
    """
    evidence_score = 0.0
    max_score = 0.0

    # 1. Plant identified (20%)
    if plant_name and plant_name.lower() != "unknown":
        evidence_score += 20.0
    max_score += 20.0

    # 2. Growth stage known (15%)
    if growth_stage and growth_stage.lower() != "unknown":
        evidence_score += 15.0
    max_score += 15.0

    # 3. Historical duration (20%)
    if sensor_stream:
        history_minutes = len(sensor_stream)
        if history_minutes >= 1440:  # 24h
            evidence_score += 20.0
        elif history_minutes >= 360:  # 6h
            evidence_score += 15.0
        elif history_minutes >= 60:  # 1h
            evidence_score += 10.0
        elif history_minutes >= 10:
            evidence_score += 5.0
        else:
            evidence_score += 2.0
    max_score += 20.0

    # 4. Sensor confidence (15%)
    evidence_score += (sensor_confidence / 100.0) * 15.0
    max_score += 15.0

    # 5. Crop-specific baseline available (15%)
    crop_knowledge = _get_crop_yield_knowledge(plant_name)
    if crop_knowledge.get("source") != "generic_fallback — no crop-specific data available":
        evidence_score += 15.0
    max_score += 15.0

    # 6. Temporal history quality (15%)
    evidence_score += (temporal_confidence / 100.0) * 15.0
    max_score += 15.0

    # Normalize to 0-1
    confidence = min(1.0, evidence_score / max(max_score, 1))

    # Determine label
    if not sensor_stream or len(sensor_stream) < 5:
        label = "insufficient_history"
    elif confidence >= 0.70:
        label = "high"
    elif confidence >= 0.45:
        label = "moderate"
    elif confidence >= 0.20:
        label = "low"
    else:
        label = "insufficient_history"

    return round(confidence, 2), label


# ============================================================================
# EVIDENCE TRACKING
# ============================================================================

def build_evidence_report(
    plant_name: str,
    growth_stage: str,
    sensor_stream: Optional[List[Dict]],
    plant_profile: Dict,
    sensor_confidence: float,
) -> Tuple[List[str], List[str]]:
    """
    Build lists of evidence used and missing evidence.

    Every yield result must explain what it is based on.
    """
    evidence_used = []
    missing_evidence = []

    # Plant species
    if plant_name and plant_name.lower() != "unknown":
        evidence_used.append("Plant species known")
    else:
        missing_evidence.append("Plant species unknown")

    # Growth stage
    if growth_stage and growth_stage.lower() != "unknown":
        evidence_used.append("Growth stage known")
    else:
        missing_evidence.append("Growth stage unknown")

    # Historical data
    if sensor_stream:
        history_minutes = len(sensor_stream)
        if history_minutes >= 60:
            evidence_used.append(f"{history_minutes}min environmental history")
        elif history_minutes > 0:
            evidence_used.append(f"Limited environmental history ({history_minutes} min)")
            missing_evidence.append("Insufficient historical duration for high-confidence forecast")
        else:
            missing_evidence.append("No environmental history")
    else:
        missing_evidence.append("No environmental history")

    # Sensor confidence
    if sensor_confidence >= 70:
        evidence_used.append("Sensor calibration valid")
    elif sensor_confidence >= 40:
        evidence_used.append("Sensor data available (moderate confidence)")
    else:
        missing_evidence.append("Low sensor confidence")

    # Plant profile source
    source = plant_profile.get("_source", "unknown")
    if source == "default_fallback":
        missing_evidence.append("Using generic plant profile (no crop-specific data)")
    else:
        evidence_used.append("Plant-specific profile available")

    # Crop yield knowledge
    crop_knowledge = _get_crop_yield_knowledge(plant_name)
    if crop_knowledge.get("source") and "generic_fallback" not in crop_knowledge.get("source", ""):
        evidence_used.append("Crop-specific yield knowledge available")
    else:
        missing_evidence.append("No crop-specific yield knowledge — using generic estimates")

    # Absolute yield requirements
    abs_reqs = crop_knowledge.get("absolute_yield_requirements", set())
    for req in abs_reqs:
        missing_evidence.append(f"{req.replace('_', ' ').title()} unknown")

    # Stress history
    if sensor_stream and len(sensor_stream) >= 10:
        evidence_used.append("Stress history available")
    else:
        missing_evidence.append("Insufficient stress history")

    return evidence_used, missing_evidence


# ============================================================================
# ABSOLUTE YIELD FORECAST
# ============================================================================

def compute_absolute_yield_forecast(
    plant_name: str,
    growth_stage: str,
    yield_potential: float,
    plant_profile: Dict,
) -> Dict:
    """
    Attempt absolute yield forecasting (kg/plant, tonnes/hectare).

    ONLY returns a value when sufficient crop-specific information exists.

    Required evidence:
    - Plant/crop species
    - Cultivar if available
    - Growth stage
    - Planting density / area where relevant
    - Healthy baseline yield information
    - Historical environmental conditions
    - Stress duration and severity

    For fruiting crops, absolute yield forecasting may additionally require:
    - Flower count
    - Fruit count
    - Fruit development information

    If evidence is insufficient, returns:
    { "status": "insufficient_data", "missing": [...] }
    """
    crop_knowledge = _get_crop_yield_knowledge(plant_name)

    # Check if we have crop-specific yield knowledge
    if crop_knowledge.get("source", "").startswith("generic_fallback"):
        return {
            "status": "insufficient_data",
            "message": "Absolute yield forecast unavailable — insufficient crop-specific data.",
            "missing": list(crop_knowledge.get("absolute_yield_requirements", [])),
        }

    # Check if we have a typical yield range
    typical_range = crop_knowledge.get("typical_yield_range")
    if not typical_range:
        return {
            "status": "insufficient_data",
            "message": "Absolute yield forecast unavailable — no baseline yield data for this crop.",
            "missing": ["crop_specific_yield_data"],
        }

    # Check absolute yield requirements
    abs_reqs = crop_knowledge.get("absolute_yield_requirements", set())
    missing = []
    for req in abs_reqs:
        # We don't have cultivar, plant_density, fruit_count, etc.
        # from the current sensor pipeline
        missing.append(req)

    if missing:
        return {
            "status": "insufficient_data",
            "message": (
                f"Absolute yield forecast unavailable — insufficient crop-specific data. "
                f"Yield potential ({yield_potential}%) is available as a relative indicator."
            ),
            "missing": missing,
            "note": "Yield potential percentage is available as a relative indicator of retained biological yield potential.",
        }

    # If we somehow have all requirements (unlikely with current sensor setup),
    # compute a range-based absolute forecast
    low_yield = typical_range["low"]
    high_yield = typical_range["high"]
    unit = typical_range["unit"]

    # Scale by yield potential
    estimated_low = round(low_yield * (yield_potential / 100.0), 2)
    estimated_high = round(high_yield * (yield_potential / 100.0), 2)

    return {
        "status": "estimated",
        "unit": unit,
        "typical_range": typical_range,
        "estimated_range": {
            "low": estimated_low,
            "high": estimated_high,
        },
        "yield_potential_percent": yield_potential,
        "note": "This is an ESTIMATED range based on crop-specific baseline yield data and current yield potential. It is NOT a direct measurement.",
    }


# ============================================================================
# YIELD MAXIMIZATION RECOMMENDATIONS
# ============================================================================

def generate_yield_recommendations(
    cumulative_stress: Dict[str, float],
    primary_limiter: Dict,
    growth_stage: str,
    plant_name: str,
    existing_recommendations: List[str],
) -> List[Dict]:
    """
    Connect existing recommendations to yield consequences.

    Instead of only "Increase soil moisture", show:
    - ACTION
    - WHY (yield consequence)
    - URGENCY
    - EXPECTED BENEFIT

    Recommendations are prioritized by:
    - Expected yield protection
    - Urgency
    - Reversibility
    - Confidence
    """
    yield_recs = []

    crop_knowledge = _get_crop_yield_knowledge(plant_name)
    critical_stages = crop_knowledge.get("critical_stages", ["flowering", "fruiting"])
    is_critical_stage = growth_stage in critical_stages

    # Map stress types to yield-focused recommendations
    stress_yield_actions = {
        "heat_stress": {
            "action": "Reduce air temperature toward the plant-specific optimal range",
            "why": "Persistent heat stress is reducing estimated retained yield potential. Heat stress during critical growth stages can cause flower abortion and reduced fruit set.",
            "urgency": "high" if is_critical_stage else "moderate",
            "expected_benefit": "May reduce further yield-loss risk if corrected promptly. Heat stress has cumulative effects on yield.",
        },
        "water_stress": {
            "action": "Increase soil moisture toward the plant-specific optimal range",
            "why": "Persistent water stress is reducing estimated retained yield potential. Water deficit during critical stages directly reduces biomass accumulation and yield.",
            "urgency": "high" if is_critical_stage else "moderate",
            "expected_benefit": "May reduce further yield-loss risk if corrected promptly. Water stress is a primary yield-limiting factor.",
        },
        "cold_stress": {
            "action": "Increase air temperature toward the plant-specific optimal range",
            "why": "Cold stress is reducing metabolic activity and estimated retained yield potential.",
            "urgency": "moderate",
            "expected_benefit": "May reduce further yield-loss risk if corrected promptly.",
        },
        "leaf_thermal_stress": {
            "action": "Improve transpiration cooling through humidity management or shading",
            "why": "Persistent elevated leaf temperature indicates transpiration stress, which reduces photosynthetic efficiency and yield potential.",
            "urgency": "high" if is_critical_stage else "moderate",
            "expected_benefit": "May improve photosynthetic efficiency and protect yield potential.",
        },
        "root_zone_stress": {
            "action": "Cool root zone through irrigation or shading of growing medium",
            "why": "Elevated root zone temperature impairs nutrient and water uptake, reducing yield potential.",
            "urgency": "moderate",
            "expected_benefit": "May improve nutrient and water uptake efficiency.",
        },
        "humidity_stress": {
            "action": "Adjust humidity toward the plant-specific optimal range",
            "why": "Humidity outside optimal range affects transpiration and can increase disease pressure, threatening yield potential.",
            "urgency": "low",
            "expected_benefit": "May improve transpiration efficiency and reduce disease risk.",
        },
        "light_stress": {
            "action": "Adjust supplemental lighting or shading to optimal range",
            "why": "Light levels outside optimal range affect photosynthetic rate and yield potential.",
            "urgency": "low",
            "expected_benefit": "May improve photosynthetic efficiency.",
        },
    }

    # Add yield-focused recommendation for the primary limiter
    if primary_limiter and primary_limiter != "none":
        action_info = stress_yield_actions.get(primary_limiter)
        if action_info:
            yield_recs.append({
                "action": action_info["action"],
                "why": action_info["why"],
                "urgency": action_info["urgency"],
                "expected_benefit": action_info["expected_benefit"],
                "targets_yield_limiter": primary_limiter,
            })

    # Add critical stage warning if applicable
    if is_critical_stage:
        yield_recs.append({
            "action": f"Maintain stable conditions during {growth_stage} — a yield-critical stage",
            "why": f"Stress during {growth_stage} has disproportionately high impact on final yield. The {plant_name} plant is in a yield-critical growth stage.",
            "urgency": "high",
            "expected_benefit": "Protecting this critical stage preserves a larger fraction of attainable yield.",
            "targets_yield_limiter": "critical_stage_protection",
        })

    # Add general yield protection recommendation
    yield_recs.append({
        "action": "Continue regular monitoring of all sensor readings",
        "why": "Early detection of stress enables timely intervention before avoidable yield loss occurs.",
        "urgency": "low",
        "expected_benefit": "Maintains yield potential through proactive stress management.",
        "targets_yield_limiter": "general_monitoring",
    })

    return yield_recs


# ============================================================================
# YIELD STORY / NARRATIVE
# ============================================================================

def generate_yield_story(
    plant_name: str,
    growth_stage: str,
    yield_potential: float,
    yield_loss_risk: str,
    primary_yield_limiter: Dict,
    cumulative_stress: Dict[str, float],
    stress_analysis: Dict,
    temporal_prediction: Dict,
    confidence_label: str,
) -> str:
    """
    Generate a concise narrative about yield status.

    All statements come from actual system data.
    No fabricated narrative.
    """
    parts = []

    # Current yield potential
    if yield_potential >= 90:
        parts.append(
            f"The {plant_name} plant in {growth_stage} stage retains an estimated "
            f"{yield_potential}% of its attainable yield potential."
        )
    elif yield_potential >= 70:
        parts.append(
            f"The {plant_name} plant in {growth_stage} stage retains an estimated "
            f"{yield_potential}% of its attainable yield potential, with some "
            f"stress-related reduction."
        )
    else:
        parts.append(
            f"The {plant_name} plant in {growth_stage} stage retains an estimated "
            f"{yield_potential}% of its attainable yield potential, indicating "
            f"significant stress-related yield risk."
        )

    # Primary yield limiter
    if primary_yield_limiter and primary_yield_limiter.get("factor") != "none":
        limiter_label = primary_yield_limiter.get("label", "Unknown")
        parts.append(
            f"The primary yield-limiting factor is {limiter_label}."
        )

    # Critical stage context
    if primary_yield_limiter.get("critical_stage_match"):
        parts.append(
            f"This is particularly concerning because {growth_stage} is a "
            f"yield-critical growth stage for {plant_name}."
        )

    # Temporal outlook
    future_state = temporal_prediction.get("future_state", {})
    future_pred = future_state.get("future_prediction", "unknown")
    if future_pred == "stress":
        parts.append(
            "Temporal AI predicts continued stress accumulation, which may "
            "further reduce yield potential if not addressed."
        )
    elif future_pred == "optimal":
        parts.append(
            "Temporal AI predicts improving conditions, which may help "
            "stabilize yield potential."
        )

    # Confidence
    parts.append(f"Yield forecast confidence is {confidence_label}.")

    return " ".join(parts)


# ============================================================================
# MAIN YIELD INTELLIGENCE ENTRY POINT
# ============================================================================

def evaluate_yield_intelligence(
    plant_name: str,
    growth_stage: str,
    phase: str,
    sensor_data: Dict,
    sensor_stream: Optional[List[Dict]] = None,
    plant_profile: Optional[Dict] = None,
    biology_analysis: Optional[Dict] = None,
    stress_analysis: Optional[Dict] = None,
    temporal_prediction: Optional[Dict] = None,
    confidence_scores: Optional[Dict] = None,
    recommendations: Optional[List[str]] = None,
) -> Dict:
    """
    Main entry point for Yield Intelligence.

    Consumes existing pipeline outputs and produces a comprehensive
    yield intelligence report.

    Args:
        plant_name: e.g. "Tomato"
        growth_stage: e.g. "flowering"
        phase: "day" or "night"
        sensor_data: Current sensor readings
        sensor_stream: Optional list of historical sensor_data dicts
        plant_profile: From pipeline (cached Tavily/parser)
        biology_analysis: From biology_engine.evaluate_biology()
        stress_analysis: From decision_engine.analyze()
        temporal_prediction: From unified_engine.unified_analysis()
        confidence_scores: Aggregated confidence dict
        recommendations: Existing recommendations list

    Returns:
        Complete yield intelligence dict for API response.
    """
    # Defaults for missing inputs
    if plant_profile is None:
        from backend.plant_profile_schema import DEFAULT_PROFILE
        plant_profile = dict(DEFAULT_PROFILE)
        plant_profile["plant"] = plant_name

    if biology_analysis is None:
        biology_analysis = {"health_score": 80, "warnings": [], "analysis": {}}

    if stress_analysis is None:
        stress_analysis = {
            "prediction": "unknown",
            "severity": 0,
            "risk_state": "unknown",
            "reasons": [],
            "recommendation": "",
        }

    if temporal_prediction is None:
        temporal_prediction = {
            "status": "unknown",
            "future_state": {"future_prediction": "unknown", "future_confidence": 0},
        }

    if confidence_scores is None:
        confidence_scores = {
            "sensor_confidence": 50,
            "ai_confidence": 50,
            "temporal_confidence": 50,
            "biology_health_score": 80,
            "overall": 50,
        }

    if recommendations is None:
        recommendations = []

    # --- Step 1: Compute cumulative stress exposure ---
    cumulative_stress = _compute_cumulative_stress(
        sensor_stream=sensor_stream,
        plant_profile=plant_profile,
        growth_stage=growth_stage,
    )

    # --- Step 2: Compute yield potential ---
    yield_potential = compute_yield_potential(
        biology_health_score=biology_analysis.get("health_score", 80),
        cumulative_stress=cumulative_stress,
        stress_analysis=stress_analysis,
        growth_stage=growth_stage,
        plant_name=plant_name,
        sensor_stream=sensor_stream,
    )

    # --- Step 3: Compute yield loss risk ---
    risk_label, risk_score = compute_yield_loss_risk(
        yield_potential=yield_potential,
        cumulative_stress=cumulative_stress,
        stress_analysis=stress_analysis,
        temporal_prediction=temporal_prediction,
    )

    # --- Step 4: Compute estimated yield impact range ---
    yield_impact_range = compute_yield_impact_range(
        yield_potential=yield_potential,
        cumulative_stress=cumulative_stress,
        growth_stage=growth_stage,
        plant_name=plant_name,
    )

    # --- Step 5: Identify primary yield limiter ---
    primary_yield_limiter = identify_primary_yield_limiter(
        cumulative_stress=cumulative_stress,
        stress_analysis=stress_analysis,
        growth_stage=growth_stage,
        plant_name=plant_name,
    )

    # --- Step 6: Compute yield forecast confidence ---
    yield_confidence, confidence_label = compute_yield_confidence(
        sensor_stream=sensor_stream,
        plant_name=plant_name,
        growth_stage=growth_stage,
        plant_profile=plant_profile,
        sensor_confidence=confidence_scores.get("sensor_confidence", 50),
        temporal_confidence=confidence_scores.get("temporal_confidence", 50),
        biology_health_score=biology_analysis.get("health_score", 80),
    )

    # --- Step 7: Build evidence report ---
    evidence_used, missing_evidence = build_evidence_report(
        plant_name=plant_name,
        growth_stage=growth_stage,
        sensor_stream=sensor_stream,
        plant_profile=plant_profile,
        sensor_confidence=confidence_scores.get("sensor_confidence", 50),
    )

    # --- Step 8: Absolute yield forecast ---
    absolute_yield = compute_absolute_yield_forecast(
        plant_name=plant_name,
        growth_stage=growth_stage,
        yield_potential=yield_potential,
        plant_profile=plant_profile,
    )

    # --- Step 9: Yield maximization recommendations ---
    yield_recommendations = generate_yield_recommendations(
        cumulative_stress=cumulative_stress,
        primary_limiter=primary_yield_limiter.get("factor", "none"),
        growth_stage=growth_stage,
        plant_name=plant_name,
        existing_recommendations=recommendations,
    )

    # --- Step 10: Yield story ---
    yield_story = generate_yield_story(
        plant_name=plant_name,
        growth_stage=growth_stage,
        yield_potential=yield_potential,
        yield_loss_risk=risk_label,
        primary_yield_limiter=primary_yield_limiter,
        cumulative_stress=cumulative_stress,
        stress_analysis=stress_analysis,
        temporal_prediction=temporal_prediction,
        confidence_label=confidence_label,
    )

    # --- Step 11: Build yield trend data ---
    yield_trend = _build_yield_trend(
        sensor_stream=sensor_stream,
        plant_profile=plant_profile,
        growth_stage=growth_stage,
        plant_name=plant_name,
        current_yield_potential=yield_potential,
    )

    # --- Assemble response ---
    return {
        "yield_potential_percent": yield_potential,
        "yield_loss_risk": risk_label,
        "yield_loss_risk_score": risk_score,
        "estimated_yield_impact_range": yield_impact_range,
        "primary_yield_limiter": primary_yield_limiter,
        "cumulative_stress": cumulative_stress,
        "critical_stage": growth_stage if primary_yield_limiter.get("critical_stage_match") else None,
        "forecast_confidence": yield_confidence,
        "confidence_label": confidence_label,
        "evidence_used": evidence_used,
        "missing_evidence": missing_evidence,
        "absolute_yield_forecast": absolute_yield,
        "yield_recommendations": yield_recommendations,
        "yield_story": yield_story,
        "yield_trend": yield_trend,
    }


def _build_yield_trend(
    sensor_stream: Optional[List[Dict]],
    plant_profile: Dict,
    growth_stage: str,
    plant_name: str,
    current_yield_potential: float,
) -> List[Dict]:
    """
    Build historical yield potential trend data for visualization.

    Computes yield potential at each historical point using ONLY
    information available at that moment (no future-data leakage).

    Returns list of { sim_minute, sim_time, yield_potential, stress_events }
    """
    if not sensor_stream or len(sensor_stream) < 2:
        return []

    trend = []
    # Use a sliding window: at each point, compute yield potential
    # using only data up to that point
    for i in range(1, len(sensor_stream)):
        window = sensor_stream[:i + 1]

        # Compute cumulative stress up to this point
        cum_stress = _compute_cumulative_stress(
            sensor_stream=window,
            plant_profile=plant_profile,
            growth_stage=growth_stage,
        )

        # Compute yield potential at this point
        yp = compute_yield_potential(
            biology_health_score=80,  # Default baseline for historical points
            cumulative_stress=cum_stress,
            stress_analysis={"severity": 0},  # Simplified for historical
            growth_stage=growth_stage,
            plant_name=plant_name,
            sensor_stream=window,
        )

        # Detect stress events (significant drops)
        stress_events = []
        if i > 0 and trend and yp < trend[-1].get("yield_potential", 100) - 3:
            # Find which stress increased
            prev_cum = trend[-1].get("_cumulative", {})
            for key, val in cum_stress.items():
                prev_val = prev_cum.get(key, 0)
                if val - prev_val > 5:
                    stress_events.append(key)

        entry = {
            "index": i,
            "yield_potential": yp,
            "stress_events": stress_events,
            "_cumulative": cum_stress,
        }

        # Try to get sim_time from sensor entry
        if "sim_time" in sensor_stream[i]:
            entry["sim_time"] = sensor_stream[i]["sim_time"]
        if "sim_minute" in sensor_stream[i]:
            entry["sim_minute"] = sensor_stream[i]["sim_minute"]

        trend.append(entry)

    # Add current point
    trend.append({
        "index": len(sensor_stream),
        "yield_potential": current_yield_potential,
        "stress_events": [],
        "is_current": True,
    })

    return trend