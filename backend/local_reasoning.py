"""
Local AI Reasoning Generator — produces real, context-aware reasoning
from the existing pipeline outputs (biology engine, decision engine,
temporal AI, sensor validation). No external API dependency.

This serves as the PRIMARY reasoning source. OpenRouter is an optional
enhancement layer that can override with richer narrative when available.
"""

import logging

logger = logging.getLogger(__name__)


def generate_local_reasoning(
    plant_name: str,
    growth_stage: str,
    phase: str,
    sensor_data: dict,
    temporal_prediction: dict,
    biology_analysis: dict,
    stress_analysis: dict,
    confidence_scores: dict,
) -> dict:
    """
    Generate AI reasoning entirely from local pipeline data.
    Produces explanation, diagnosis, recommendations, and confidence_narrative
    based on real sensor readings, biology health, stress predictions,
    and temporal forecasts.

    Returns the same structure as _call_openrouter_reasoning():
    {
        "explanation": str,
        "diagnosis": str,
        "recommendations": [str, ...],
        "confidence_narrative": str,
        "_source": "local_reasoning"
    }
    """

    # ── Extract key data points ──────────────────────────────────
    air_temp = sensor_data.get("air_temp", "N/A")
    humidity = sensor_data.get("humidity", "N/A")
    soil_moisture = sensor_data.get("soil_moisture", "N/A")
    soil_temp = sensor_data.get("soil_temp", "N/A")
    light = sensor_data.get("light", "N/A")
    leaf_temp_delta = sensor_data.get("leaf_temp_delta", "N/A")

    health_score = biology_analysis.get("health_score", 0)
    biology_warnings = biology_analysis.get("warnings", [])
    biology_details = biology_analysis.get("analysis", {})

    stress_prediction = stress_analysis.get("prediction", "unknown")
    stress_severity = stress_analysis.get("severity", 0)
    stress_risk = stress_analysis.get("risk_state", "unknown")
    stress_reasons = stress_analysis.get("reasons", [])
    stress_recommendation = stress_analysis.get("recommendation", "")

    temporal_status = temporal_prediction.get("status", "unknown")
    future_state = temporal_prediction.get("future_state", {})
    future_prediction = future_state.get("future_prediction", "unknown")
    future_confidence = future_state.get("future_confidence", 0)

    overall_confidence = confidence_scores.get("overall", 0)
    sensor_confidence = confidence_scores.get("sensor_confidence", 0)
    ai_confidence = confidence_scores.get("ai_confidence", 0)
    temporal_confidence = confidence_scores.get("temporal_confidence", 0)
    biology_health = confidence_scores.get("biology_health_score", 0)

    # ── Build sensor status summary ──────────────────────────────
    sensor_status_parts = []
    for metric_key, metric_label in [
        ("air_temp", "Air Temperature"),
        ("humidity", "Humidity"),
        ("soil_moisture", "Soil Moisture"),
        ("soil_temp", "Soil Temperature"),
        ("light", "Light Intensity"),
    ]:
        detail = biology_details.get(metric_key, {})
        if detail:
            val = detail.get("value", "N/A")
            status = detail.get("status", "unknown")
            opt_range = detail.get("optimal_range", [0, 0])
            if status == "optimal":
                sensor_status_parts.append(
                    f"{metric_label} is optimal at {val} (range: {opt_range[0]}–{opt_range[1]})"
                )
            else:
                sensor_status_parts.append(
                    f"{metric_label} is at {val}, outside optimal range {opt_range[0]}–{opt_range[1]}"
                )

    sensor_summary = "; ".join(sensor_status_parts) if sensor_status_parts else "Sensor data received and validated."

    # ── Build explanation ────────────────────────────────────────
    # Describe the plant's current state based on all available data

    # Health assessment
    if health_score >= 85:
        health_phrase = "in excellent health"
    elif health_score >= 65:
        health_phrase = "in good health with minor concerns"
    elif health_score >= 40:
        health_phrase = "showing moderate stress signs"
    else:
        health_phrase = "under significant stress"

    # Phase context
    phase_context = "daytime" if phase == "day" else "nighttime"
    stage_display = growth_stage.replace("_", " ").title()

    # Temporal outlook
    if temporal_status == "ok" and future_prediction != "unknown":
        if future_prediction == "optimal":
            temporal_outlook = "Temporal AI predicts conditions will remain optimal in the near future"
        elif future_prediction == "stress":
            temporal_outlook = "Temporal AI forecasts increasing stress levels ahead"
        else:
            temporal_outlook = f"Temporal AI predicts a shift toward {future_prediction} conditions"
    else:
        temporal_outlook = "Temporal AI has limited historical context for a reliable forecast"

    # Stress context
    if stress_prediction != "unknown" and stress_prediction != "optimal":
        stress_context = (
            f"Decision engine detects {stress_prediction} stress "
            f"at severity {stress_severity:.1f}/100 ({stress_risk} risk level)"
        )
    elif stress_prediction == "optimal":
        stress_context = "Decision engine confirms no significant stress detected"
    else:
        stress_context = "Stress analysis is inconclusive with current data"

    explanation = (
        f"The {plant_name} plant in {stage_display} stage during {phase_context} is {health_phrase}. "
        f"{sensor_summary}. "
        f"{stress_context}. "
        f"{temporal_outlook}. "
        f"Overall confidence in this assessment is {overall_confidence:.1f}%."
    )

    # ── Build diagnosis ──────────────────────────────────────────
    diagnosis_parts = []

    # Biology warnings
    if biology_warnings:
        diagnosis_parts.append("Biology engine flags the following concerns:")
        for w in biology_warnings:
            diagnosis_parts.append(f"  • {w}")
    else:
        diagnosis_parts.append("Biology engine reports all metrics within optimal ranges.")

    # Stress reasons
    if stress_reasons:
        diagnosis_parts.append("Decision engine identifies these stress factors:")
        for r in stress_reasons:
            diagnosis_parts.append(f"  • {r}")

    # Leaf temperature delta (key stress indicator)
    if isinstance(leaf_temp_delta, (int, float)):
        if leaf_temp_delta > 5:
            diagnosis_parts.append(
                f"Leaf temperature delta is elevated ({leaf_temp_delta:.1f}°C above air), "
                f"indicating possible transpiration stress or stomatal closure."
            )
        elif leaf_temp_delta < 0:
            diagnosis_parts.append(
                f"Leaf temperature is below air temperature ({leaf_temp_delta:.1f}°C), "
                f"suggesting evaporative cooling is active — a positive sign."
            )

    # Confidence gaps
    low_confidence_items = []
    if sensor_confidence < 60:
        low_confidence_items.append("sensor validation")
    if ai_confidence < 50:
        low_confidence_items.append("decision engine")
    if temporal_confidence < 50:
        low_confidence_items.append("temporal prediction")
    if biology_health < 50:
        low_confidence_items.append("biology health score")

    if low_confidence_items:
        diagnosis_parts.append(
            f"Note: Lower confidence in {', '.join(low_confidence_items)} "
            f"may affect diagnostic precision."
        )

    diagnosis = "\n".join(diagnosis_parts) if diagnosis_parts else (
        f"No specific issues detected. The {plant_name} plant appears to be "
        f"functioning normally for its {stage_display} stage."
    )

    # ── Build recommendations ────────────────────────────────────
    recommendations = []

    # From decision engine
    if stress_recommendation:
        recommendations.append(stress_recommendation)

    # From biology warnings — convert to actionable items
    for w in biology_warnings:
        if "air_temp" in w.lower() or "air temperature" in w.lower():
            if isinstance(air_temp, (int, float)):
                if air_temp > 30:
                    recommendations.append(
                        f"Increase ventilation or shading to reduce air temperature "
                        f"(currently {air_temp:.1f}°C)"
                    )
                elif air_temp < 15:
                    recommendations.append(
                        f"Activate heating or row covers to raise air temperature "
                        f"(currently {air_temp:.1f}°C)"
                    )
        elif "humidity" in w.lower():
            if isinstance(humidity, (int, float)):
                if humidity < 40:
                    recommendations.append(
                        f"Increase humidity via misting or fog systems "
                        f"(currently {humidity:.1f}%)"
                    )
                elif humidity > 85:
                    recommendations.append(
                        f"Improve air circulation to reduce humidity "
                        f"(currently {humidity:.1f}%)"
                    )
        elif "soil_moisture" in w.lower() or "drought" in w.lower():
            recommendations.append(
                f"Increase irrigation frequency or volume — soil moisture is below optimal"
            )
        elif "waterlogging" in w.lower():
            recommendations.append(
                f"Reduce irrigation and improve drainage — waterlogging detected"
            )
        elif "heat_stress" in w.lower() or "heat stress" in w.lower():
            recommendations.append(
                f"Apply shade cloth or increase airflow to mitigate heat stress"
            )
        elif "cold_stress" in w.lower() or "cold stress" in w.lower():
            recommendations.append(
                f"Deploy frost protection or heating to prevent cold damage"
            )

    # General recommendations based on growth stage
    stage_recs = {
        "germination": "Maintain consistent moisture and temperature for successful germination.",
        "seedling": "Protect from extreme conditions; seedlings are vulnerable to stress.",
        "vegetative": "Ensure adequate nitrogen and water for vigorous vegetative growth.",
        "flowering": "Maintain stable conditions — stress during flowering reduces yield.",
        "fruiting": "Optimize potassium and phosphorus availability for fruit development.",
        "harvest": "Monitor for peak ripeness indicators; reduce water before harvest.",
    }
    stage_rec = stage_recs.get(growth_stage)
    if stage_rec:
        recommendations.append(stage_rec)

    # Temporal-based recommendation
    if future_prediction == "stress" and temporal_status == "ok":
        recommendations.append(
            "Temporal AI predicts upcoming stress — take preventive action now "
            "rather than waiting for symptoms to appear."
        )

    # Deduplicate while preserving order
    seen = set()
    unique_recs = []
    for r in recommendations:
        if r not in seen:
            seen.add(r)
            unique_recs.append(r)
    recommendations = unique_recs

    # Ensure at least 3 recommendations
    while len(recommendations) < 3:
        fallback_recs = [
            "Continue regular monitoring of all sensor readings.",
            "Maintain current irrigation and climate control schedules.",
            "Review historical trends to identify emerging patterns.",
        ]
        for fb in fallback_recs:
            if fb not in seen:
                recommendations.append(fb)
                seen.add(fb)
                if len(recommendations) >= 3:
                    break

    # ── Build confidence narrative ───────────────────────────────
    confidence_parts = []

    # Overall confidence level description
    if overall_confidence >= 80:
        conf_level = "high"
    elif overall_confidence >= 55:
        conf_level = "moderate"
    else:
        conf_level = "low"

    confidence_parts.append(
        f"Overall assessment confidence is {conf_level} at {overall_confidence:.1f}%, "
        f"derived from a weighted combination of four independent analysis layers."
    )

    # Per-layer breakdown
    confidence_parts.append(
        f"Sensor validation confidence: {sensor_confidence:.1f}% "
        f"(weight: 15%) — measures data quality and sensor reliability."
    )
    confidence_parts.append(
        f"Decision engine confidence: {ai_confidence:.1f}% "
        f"(weight: 30%) — the ML model's certainty in its stress classification."
    )
    confidence_parts.append(
        f"Temporal AI confidence: {temporal_confidence:.1f}% "
        f"(weight: 25%) — confidence in the future state prediction."
    )
    confidence_parts.append(
        f"Biology health score: {biology_health:.1f}% "
        f"(weight: 30%) — how well current conditions match the plant's optimal profile."
    )

    # Highlight the strongest and weakest layers
    layers = [
        ("Sensor Validation", sensor_confidence),
        ("Decision Engine", ai_confidence),
        ("Temporal AI", temporal_confidence),
        ("Biology Health", biology_health),
    ]
    strongest = max(layers, key=lambda x: x[1])
    weakest = min(layers, key=lambda x: x[1])

    confidence_parts.append(
        f"The strongest signal comes from {strongest[0]} ({strongest[1]:.1f}%), "
        f"while {weakest[0]} provides the weakest contribution ({weakest[1]:.1f}%)."
    )

    # Temporal-specific note
    if temporal_status != "ok":
        confidence_parts.append(
            "Temporal AI confidence is limited due to insufficient historical context. "
            "Forecast reliability will improve as more sensor data accumulates."
        )

    confidence_narrative = " ".join(confidence_parts)

    return {
        "explanation": explanation,
        "diagnosis": diagnosis,
        "recommendations": recommendations,
        "confidence_narrative": confidence_narrative,
        "_source": "local_reasoning",
    }