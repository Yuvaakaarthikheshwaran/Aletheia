
def evaluate_biology(sensor_data, profile, growth_stage, phase):
    analysis = {}
    warnings = []
    score = 100

    # Get profiles
    stage_profile = profile["growth_stages"][growth_stage]

    phase_profile = (
        profile["day_profile"]
        if phase == "day"
        else profile["night_profile"]
    )

    # Metrics to evaluate
    metrics = [
        "air_temp",
        "humidity",
        "light",
        "soil_moisture",
        "soil_temp"
    ]

    for metric in metrics:
        value = sensor_data.get(metric, 0)

        # Priority: growth stage profile > phase profile
        if metric in stage_profile:
            optimal = stage_profile[metric]
        elif metric in phase_profile:
            optimal = phase_profile[metric]
        else:
            continue

        low, high = optimal

        status = "optimal"

        if value < low or value > high:
            status = "stress"
            score -= 15
            warnings.append(f"{metric.replace('_', ' ').title()} outside optimal range")

        analysis[metric] = {
            "value": value,
            "optimal_range": optimal,
            "status": status
        }

    # Stress threshold logic
    thresholds = profile.get("stress_thresholds", {})

    air_temp = sensor_data.get("air_temp", 0)
    soil_moisture = sensor_data.get("soil_moisture", 50)

    if air_temp >= thresholds.get("heat_stress", 999):
        warnings.append("Heat stress risk")
        score -= 15

    if air_temp >= thresholds.get("severe_heat_stress", 999):
        warnings.append("Severe heat stress")
        score -= 20

    if air_temp <= thresholds.get("cold_stress", -999):
        warnings.append("Cold stress risk")
        score -= 15

    if soil_moisture <= thresholds.get("drought_stress", -999):
        warnings.append("Drought stress risk")
        score -= 20

    if soil_moisture >= thresholds.get("waterlogging_stress", 999):
        warnings.append("Waterlogging stress risk")
        score -= 20

    score = max(score, 0)

    return {
        "analysis": analysis,
        "health_score": score,
        "phase": phase,
        "warnings": warnings
    }

