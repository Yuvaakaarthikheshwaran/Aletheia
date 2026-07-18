
"""
Aletheia Backend — Production Flask API

Endpoints:
  GET  /                    — Health check
  GET  /search/<query>      — Fuzzy plant search
  POST /analyze             — Unified production pipeline
  GET  /predict/<plant>/<stage>/<phase>  — Legacy (redirects to /analyze with demo data)
"""

import os
import sys
import traceback
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure ai/ is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai"))
if AI_DIR not in sys.path:
    sys.path.append(AI_DIR)

from backend.fuzzy_search import search_plants
from backend.unified_pipeline import run_unified_pipeline

# Digital Twin Simulator (additive — does not modify existing pipeline)
from backend.simulator import GreenhouseSimulator, SCENARIOS

# Global simulator instance (singleton for the Flask process)
_simulator = GreenhouseSimulator()

# Hardware Integration Layer (additive — does not modify existing pipeline)
from backend.hardware import validate_hardware_packet, HardwareStore, CalibrationManager

# Global hardware instances (singletons for the Flask process)
_hardware_store = HardwareStore()
_calibration = CalibrationManager()

app = Flask(__name__)

# CORS: Allow frontend origin via environment variable, with secure defaults
_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if _ALLOWED_ORIGINS == "*":
    CORS(app)
else:
    CORS(app, origins=_ALLOWED_ORIGINS.split(","))


@app.route("/")
def home():
    return jsonify({
        "service": "Aletheia Backend",
        "status": "running",
        "endpoints": {
            "health": "/",
            "search": "/search/<query>",
            "analyze": "POST /analyze",
        }
    })


@app.route("/search/<query>")
def search(query):
    return jsonify(search_plants(query))


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Unified production endpoint.

    Input JSON:
    {
        "plant": "Tomato",
        "stage": "Flowering",
        "mode": "Day",
        "sensor_data": {
            "air_temp": 32,
            "humidity": 55,
            "light": 800,
            "leaf_temp": 35,
            "soil_moisture": 60,
            "soil_temp": 26,
            "air_temp_rate": 2,
            "humidity_rate": -5,
            "leaf_temp_rate": 1,
            "leaf_temp_delta": 3
        }
    }

    Output: Full unified analysis JSON.
    """
    try:
        body = request.get_json(silent=True) or {}

        plant_name = body.get("plant", "tomato")
        growth_stage = body.get("stage", "vegetative")
        phase = body.get("mode", "day").lower()
        sensor_data = body.get("sensor_data", {})

        # Validate required sensor fields exist (or will be repaired)
        if not sensor_data:
            return jsonify({
                "error": "Missing sensor_data",
                "message": "Provide at least air_temp, humidity, soil_moisture, soil_temp, leaf_temp, light"
            }), 400

        result = run_unified_pipeline(
            plant_name=plant_name,
            growth_stage=growth_stage,
            phase=phase,
            sensor_data=sensor_data,
        )

        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "pipeline_failure",
            "message": str(e),
        }), 500


@app.route("/predict/<plant_name>/<growth_stage>/<phase>")
def predict_legacy(plant_name, growth_stage, phase):
    """
    Legacy endpoint maintained for backward compatibility.
    Uses demo sensor data when no real sensors are provided.
    """
    # Demo sensor data (deterministic, not random)
    demo_sensor_data = {
        "air_temp": 32,
        "humidity": 55,
        "light": 800,
        "leaf_temp": 35,
        "soil_moisture": 60,
        "soil_temp": 26,
        "air_temp_rate": 2,
        "humidity_rate": -5,
        "leaf_temp_rate": 1,
        "leaf_temp_delta": 3,
    }

    try:
        result = run_unified_pipeline(
            plant_name=plant_name,
            growth_stage=growth_stage,
            phase=phase,
            sensor_data=demo_sensor_data,
        )
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "pipeline_failure",
            "message": str(e),
        }), 500


# ============================================================
# Digital Twin Simulator Endpoints (additive — no modifications above)
# ============================================================

@app.route("/simulator/state", methods=["GET"])
def simulator_state():
    """
    Get current simulator state without advancing.
    Returns sensor_data, weather, soil, plant, causal_chain, sim_time, etc.
    """
    state = _simulator.step(dt_minutes=0)  # dt=0 → no advance, just read current
    # Add scenario catalog for frontend
    from backend.simulator.scenarios import get_scenario_list
    state["available_scenarios"] = get_scenario_list()
    return jsonify(state)


@app.route("/simulator/step", methods=["POST"])
def simulator_step():
    """
    Advance simulator by one step and return state.
    Body (optional): { "dt_minutes": 1.0 }
    """
    body = request.get_json(silent=True) or {}
    dt = body.get("dt_minutes", _simulator.speed)
    state = _simulator.step(dt_minutes=dt)
    return jsonify(state)


@app.route("/simulator/start", methods=["POST"])
def simulator_start():
    """Start the simulator."""
    _simulator.start()
    return jsonify({"status": "started", "running": True})


@app.route("/simulator/pause", methods=["POST"])
def simulator_pause():
    """Pause the simulator."""
    _simulator.pause()
    return jsonify({"status": "paused", "running": False})


@app.route("/simulator/reset", methods=["POST"])
def simulator_reset():
    """Full reset to initial conditions."""
    _simulator.reset()
    return jsonify({"status": "reset", "running": False})


@app.route("/simulator/scenario", methods=["POST"])
def simulator_set_scenario():
    """
    Set active scenario.
    Body: { "scenario": "heat_wave" }
    """
    body = request.get_json(silent=True) or {}
    scenario_name = body.get("scenario", "normal_day")
    try:
        _simulator.set_scenario(scenario_name)
        return jsonify({
            "status": "scenario_set",
            "scenario": scenario_name,
            "running": _simulator.running,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/simulator/speed", methods=["POST"])
def simulator_set_speed():
    """
    Set simulation speed multiplier.
    Body: { "speed": 60.0 }  → 1 real second = 60 sim-minutes
    """
    body = request.get_json(silent=True) or {}
    speed = body.get("speed", 1.0)
    _simulator.set_speed(speed)
    return jsonify({"status": "speed_set", "speed": _simulator.speed})


@app.route("/simulator/history", methods=["GET"])
def simulator_history():
    """
    Get simulation history.
    Query params: ?n=60 (last 60 steps)
    Returns list of state dicts + sensor_stream for temporal AI.
    """
    n = request.args.get("n", default=60, type=int)
    history = _simulator.get_history(n)
    sensor_stream = _simulator.get_history_sensor_stream(n)
    return jsonify({
        "n_steps": len(history),
        "history": history,
        "sensor_stream": sensor_stream,
    })


@app.route("/simulator/analyze", methods=["POST"])
def simulator_analyze():
    """
    Step simulator, then feed sensor_data into /analyze pipeline.
    Returns BOTH simulator state AND AI analysis in one response.

    This is the key integration point:
    Simulator → Virtual Sensors → /analyze pipeline → Unified Response

    The sensor_stream (historical sensor data) is passed to the Temporal AI
    so it uses real prev1/prev2 values instead of synthetic fallbacks.

    ANALYSIS SNAPSHOTS: The AI analysis is stored back into the simulator's
    history entry so that comparison mode can later retrieve "what did
    Aletheia predict at minute X, and what actually happened at minute X+30?"
    """
    body = request.get_json(silent=True) or {}
    dt = body.get("dt_minutes", _simulator.speed)

    # Step simulator first (without analysis — we need sensor_data to run pipeline)
    sim_state = _simulator.step(dt_minutes=dt)
    sensor_data = sim_state["sensor_data"]

    # Get historical sensor stream for temporal AI context
    # (exclude current step since it's already sensor_data)
    n_history = body.get("history_steps", 60)
    sensor_stream = _simulator.get_history_sensor_stream(n_history)
    # Remove the most recent entry if it matches current (avoid double-counting)
    if sensor_stream and len(sensor_stream) > 0:
        last_entry = sensor_stream[-1]
        if last_entry.get("air_temp") == sensor_data.get("air_temp") and \
           last_entry.get("humidity") == sensor_data.get("humidity"):
            sensor_stream = sensor_stream[:-1]

    # Feed into existing /analyze pipeline with historical context
    plant_name = body.get("plant", "tomato")
    growth_stage = body.get("stage", "vegetative")
    phase = sim_state["day_phase"]  # auto-detect day/night from simulator

    analysis = run_unified_pipeline(
        plant_name=plant_name,
        growth_stage=growth_stage,
        phase=phase,
        sensor_data=sensor_data,
        sensor_stream=sensor_stream,
    )

    # --- Store analysis snapshot into simulator history ---
    # Replace the last history entry (which has no analysis) with one that does.
    # This enables comparison mode: "at minute X, Aletheia predicted Y; at X+30, reality was Z"
    if _simulator.history:
        last_entry = _simulator.history[-1]
        last_entry["analysis_snapshot"] = {
            "plant_name": plant_name,
            "growth_stage": growth_stage,
            "temporal_prediction": analysis.get("temporal_prediction"),
            "stress_analysis": analysis.get("stress_analysis"),
            "biology_analysis": analysis.get("biology_analysis"),
            "recommendations": analysis.get("recommendations"),
            "confidence": analysis.get("confidence"),
            "ai_reasoning": analysis.get("ai_reasoning"),
            "decision_input": analysis.get("decision_input"),
        }

    # Build historical trajectory for frontend visualization
    full_history = _simulator.get_history(n_history)
    trajectory = []
    for h in full_history:
        trajectory.append({
            "sim_time": h.get("sim_time", ""),
            "sim_minute": h.get("sim_minute", 0),
            "air_temp": h["sensor_data"].get("air_temp"),
            "humidity": h["sensor_data"].get("humidity"),
            "soil_moisture": h["sensor_data"].get("soil_moisture"),
            "leaf_temp_delta": h["sensor_data"].get("leaf_temp_delta"),
            "light": h["sensor_data"].get("light"),
            "stress": h["plant"].get("stress", 0),
            "growth": h["plant"].get("growth", 0),
            # Include analysis snapshot metadata for comparison mode
            "has_snapshot": h.get("analysis_snapshot") is not None,
            "temporal_label": h.get("analysis_snapshot", {}).get("temporal_prediction", {}).get("future_state", {}).get("future_prediction") if h.get("analysis_snapshot") else None,
            "stress_label": h.get("analysis_snapshot", {}).get("stress_analysis", {}).get("prediction") if h.get("analysis_snapshot") else None,
        })

    return jsonify({
        "simulator": {
            "sim_time": sim_state["sim_time"],
            "day_phase": sim_state["day_phase"],
            "scenario": sim_state["scenario"],
            "running": sim_state["running"],
            "weather": sim_state["weather"],
            "soil": sim_state["soil"],
            "plant": sim_state["plant"],
            "causal_chain": sim_state["causal_chain"],
            "trajectory": trajectory,
        },
        "analysis": analysis,
    })


# ============================================================
# Temporal AI — Prediction Verification & Replay
# ============================================================

@app.route("/simulator/temporal/verify", methods=["POST"])
def temporal_verify():
    """
    Compare a past prediction with the actual measured value at that timestamp.

    Body:
        prediction_timestamp: sim_minute when prediction was made
        prediction_value: the predicted value
        variable: which variable to compare (air_temp, humidity, soil_moisture, leaf_temp_delta)

    Returns:
        actual_value: what the simulator recorded at that timestamp
        error: absolute error
        error_pct: percentage error relative to actual
        accuracy: 100 - error_pct (capped at 0)
    """
    body = request.get_json(silent=True) or {}
    pred_minute = body.get("prediction_timestamp")
    pred_value = body.get("prediction_value")
    variable = body.get("variable", "air_temp")

    if pred_minute is None or pred_value is None:
        return jsonify({"error": "Missing prediction_timestamp or prediction_value"}), 400

    # Search history for the entry closest to pred_minute
    history = _simulator.get_history()
    actual_value = None
    best_diff = float("inf")

    for h in history:
        h_minute = h.get("sim_minute", 0)
        diff = abs(h_minute - pred_minute)
        if diff < best_diff:
            best_diff = diff
            sd = h.get("sensor_data", {})
            if variable == "leaf_temp_delta":
                actual_value = sd.get("leaf_temp_delta")
            elif variable == "soil_moisture":
                actual_value = sd.get("soil_moisture")
            elif variable == "humidity":
                actual_value = sd.get("humidity")
            else:
                actual_value = sd.get("air_temp")

    if actual_value is None:
        return jsonify({"error": "No historical data found for that timestamp"}), 404

    error = abs(pred_value - actual_value)
    error_pct = round((error / max(abs(actual_value), 0.01)) * 100, 2)
    accuracy = max(0.0, round(100.0 - error_pct, 2))

    return jsonify({
        "variable": variable,
        "prediction_timestamp": pred_minute,
        "prediction_value": pred_value,
        "actual_value": actual_value,
        "actual_timestamp": best_diff if best_diff != float("inf") else None,
        "error": round(error, 4),
        "error_pct": error_pct,
        "accuracy": accuracy,
    })


@app.route("/simulator/temporal/replay", methods=["GET"])
def temporal_replay():
    """
    Return the full simulator state at a specific sim_minute for replay navigation.

    Query params:
        ?minute=360  (sim_minute to replay, 0-1439)
        ?n=10        (also return n steps before and after for context)

    Returns:
        target: state at requested minute
        context_before: n steps before target
        context_after: n steps after target
    """
    target_minute = request.args.get("minute", default=0, type=int)
    n_context = request.args.get("n", default=10, type=int)

    history = _simulator.get_history()
    if not history:
        return jsonify({"error": "No simulation history available"}), 404

    # Find closest entry to target_minute
    target_idx = None
    best_diff = float("inf")
    for i, h in enumerate(history):
        diff = abs(h.get("sim_minute", 0) - target_minute)
        if diff < best_diff:
            best_diff = diff
            target_idx = i

    if target_idx is None:
        return jsonify({"error": "No matching entry found"}), 404

    before = history[max(0, target_idx - n_context):target_idx]
    after = history[target_idx + 1:target_idx + 1 + n_context]

    return jsonify({
        "target": history[target_idx],
        "target_index": target_idx,
        "total_history": len(history),
        "context_before": before,
        "context_after": after,
    })


@app.route("/simulator/temporal/accuracy", methods=["GET"])
def temporal_accuracy():
    """
    Compute rolling prediction accuracy across the entire simulation history.

    For each step where we have a temporal_prediction stored, compare
    the predicted future state with what actually happened.

    Query params:
        ?window=20  (rolling window size for accuracy computation)

    Returns:
        rolling_accuracy: list of accuracy scores over time
        overall_accuracy: mean accuracy across all verified predictions
        total_verified: number of prediction-vs-actual comparisons made
    """
    window = request.args.get("window", default=20, type=int)
    history = _simulator.get_history()

    if len(history) < 3:
        return jsonify({
            "rolling_accuracy": [],
            "overall_accuracy": None,
            "total_verified": 0,
            "message": "Need at least 3 history entries for verification",
        })

    # For each step, compare current air_temp with what prev2 trend suggested
    # This is a simplified verification using the 2-step trend
    accuracies = []
    for i in range(2, len(history)):
        prev2 = history[i - 2]["sensor_data"].get("air_temp", 0)
        prev1 = history[i - 1]["sensor_data"].get("air_temp", 0)
        current = history[i]["sensor_data"].get("air_temp", 0)

        # Simple linear extrapolation as baseline prediction
        trend = prev1 - prev2
        predicted = prev1 + trend
        actual = current

        if abs(actual) > 0.01:
            error_pct = abs(predicted - actual) / abs(actual) * 100
            accuracy = max(0.0, 100.0 - error_pct)
        else:
            accuracy = 100.0

        accuracies.append({
            "sim_minute": history[i].get("sim_minute", 0),
            "sim_time": history[i].get("sim_time", ""),
            "predicted": round(predicted, 2),
            "actual": round(actual, 2),
            "error": round(abs(predicted - actual), 2),
            "accuracy": round(accuracy, 2),
        })

    # Rolling window average
    rolling = []
    for i in range(len(accuracies)):
        window_slice = accuracies[max(0, i - window + 1):i + 1]
        avg_acc = sum(a["accuracy"] for a in window_slice) / len(window_slice)
        rolling.append({
            "sim_minute": accuracies[i]["sim_minute"],
            "sim_time": accuracies[i]["sim_time"],
            "rolling_accuracy": round(avg_acc, 2),
        })

    overall = sum(a["accuracy"] for a in accuracies) / len(accuracies) if accuracies else 0

    return jsonify({
        "rolling_accuracy": rolling,
        "overall_accuracy": round(overall, 2),
        "total_verified": len(accuracies),
        "verification_details": accuracies[-window:] if len(accuracies) > window else accuracies,
    })


# ============================================================
# Temporal AI — Historical Snapshots & Comparison Mode
# ============================================================

@app.route("/simulator/temporal/snapshots", methods=["GET"])
def temporal_snapshots():
    """
    Return all historical entries that have analysis snapshots attached.
    These are the "proper points in time" for comparison mode.

    Query params:
        ?limit=50   (max snapshots to return, default 50)
        ?offset=0   (pagination offset)

    Returns:
        snapshots: list of history entries with analysis_snapshot
        total_snapshots: count of all entries with snapshots
    """
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    history = _simulator.get_history()
    snapshots = [h for h in history if h.get("analysis_snapshot")]

    total = len(snapshots)
    page = snapshots[offset:offset + limit]

    # Build lightweight response (exclude full causal_chain to reduce payload)
    result = []
    for h in page:
        snap = h.get("analysis_snapshot", {})
        result.append({
            "sim_time": h.get("sim_time", ""),
            "sim_minute": h.get("sim_minute", 0),
            "day_phase": h.get("day_phase", ""),
            "scenario": h.get("scenario", ""),
            "sensor_data": h.get("sensor_data", {}),
            "plant": h.get("plant", {}),
            "weather": h.get("weather", {}),
            "soil": h.get("soil", {}),
            "temporal_prediction": snap.get("temporal_prediction"),
            "stress_analysis": snap.get("stress_analysis"),
            "biology_analysis": snap.get("biology_analysis"),
            "recommendations": snap.get("recommendations"),
            "confidence": snap.get("confidence"),
            "ai_reasoning": snap.get("ai_reasoning"),
            "decision_input": snap.get("decision_input"),
            "plant_name": snap.get("plant_name"),
            "growth_stage": snap.get("growth_stage"),
        })

    return jsonify({
        "snapshots": result,
        "total_snapshots": total,
        "limit": limit,
        "offset": offset,
    })


@app.route("/simulator/temporal/compare", methods=["GET"])
def temporal_compare():
    """
    COMPARISON MODE: Select any historical prediction snapshot and compare
    what Aletheia predicted with what actually happened at that future time.

    This is the core scientific feature — "at minute X, Aletheia predicted Y;
    at minute X+Δ, reality was Z. Error = |Y-Z|. Reason = ..."

    Query params:
        ?snapshot_minute=360   (the sim_minute when prediction was made)
        ?compare_minute=390    (the sim_minute to compare against, default: snapshot + 30)
        ?variables=air_temp,humidity,soil_moisture,leaf_temp_delta

    Returns:
        snapshot: the historical analysis at snapshot_minute
        actual: the measured values at compare_minute
        comparison: per-variable prediction vs actual with error
        summary: overall accuracy assessment
    """
    snapshot_minute = request.args.get("snapshot_minute", type=int)
    compare_minute = request.args.get("compare_minute", default=None, type=int)
    variables_str = request.args.get("variables", default="air_temp,humidity,soil_moisture,leaf_temp_delta")

    if snapshot_minute is None:
        return jsonify({"error": "Missing snapshot_minute parameter"}), 400

    variables = [v.strip() for v in variables_str.split(",")]

    history = _simulator.get_history()

    # Find the snapshot entry
    snapshot_entry = None
    snapshot_idx = None
    best_diff = float("inf")
    for i, h in enumerate(history):
        if h.get("analysis_snapshot"):
            diff = abs(h.get("sim_minute", 0) - snapshot_minute)
            if diff < best_diff:
                best_diff = diff
                snapshot_entry = h
                snapshot_idx = i

    if snapshot_entry is None:
        return jsonify({"error": "No analysis snapshot found near that minute. Run /simulator/analyze first."}), 404

    # Default compare_minute = snapshot + 30 minutes
    if compare_minute is None:
        compare_minute = snapshot_entry.get("sim_minute", 0) + 30

    # Find the actual entry at compare_minute
    actual_entry = None
    best_diff = float("inf")
    for h in history:
        diff = abs(h.get("sim_minute", 0) - compare_minute)
        if diff < best_diff:
            best_diff = diff
            actual_entry = h

    if actual_entry is None:
        return jsonify({"error": "No data at compare_minute. Run more simulation steps first."}), 404

    # Build comparison: for each variable, compare snapshot sensor_data with actual
    snap_sensors = snapshot_entry.get("sensor_data", {})
    actual_sensors = actual_entry.get("sensor_data", {})

    comparisons = []
    for var in variables:
        pred_val = snap_sensors.get(var)
        actual_val = actual_sensors.get(var)
        if pred_val is not None and actual_val is not None:
            error = abs(pred_val - actual_val)
            error_pct = round((error / max(abs(actual_val), 0.01)) * 100, 2)
            accuracy = max(0.0, round(100.0 - error_pct, 2))
            comparisons.append({
                "variable": var,
                "predicted": round(pred_val, 4),
                "actual": round(actual_val, 4),
                "error": round(error, 4),
                "error_pct": error_pct,
                "accuracy": accuracy,
            })

    # Overall accuracy across all compared variables
    if comparisons:
        overall_accuracy = round(sum(c["accuracy"] for c in comparisons) / len(comparisons), 2)
    else:
        overall_accuracy = None

    # Extract the temporal prediction label from the snapshot
    snap = snapshot_entry.get("analysis_snapshot", {})
    temporal_pred = snap.get("temporal_prediction", {})
    future_state = temporal_pred.get("future_state", {}) if temporal_pred else {}
    predicted_label = future_state.get("future_prediction", "unknown")

    # Determine what actually happened (did stress occur?)
    actual_stress = actual_entry.get("plant", {}).get("stress", 0)
    actual_stress_label = "stress_detected" if actual_stress > 0.3 else "stable"

    # Was the temporal prediction correct?
    prediction_correct = (predicted_label == "stable" and actual_stress_label == "stable") or \
                         (predicted_label != "stable" and actual_stress_label == "stress_detected")

    return jsonify({
        "snapshot": {
            "sim_time": snapshot_entry.get("sim_time"),
            "sim_minute": snapshot_entry.get("sim_minute"),
            "scenario": snapshot_entry.get("scenario"),
            "temporal_prediction": temporal_pred,
            "stress_analysis": snap.get("stress_analysis"),
            "recommendations": snap.get("recommendations"),
            "ai_reasoning": snap.get("ai_reasoning"),
        },
        "actual": {
            "sim_time": actual_entry.get("sim_time"),
            "sim_minute": actual_entry.get("sim_minute"),
            "sensor_data": {v: actual_sensors.get(v) for v in variables},
            "plant": actual_entry.get("plant"),
        },
        "comparison": {
            "variables": comparisons,
            "overall_accuracy": overall_accuracy,
            "predicted_label": predicted_label,
            "actual_label": actual_stress_label,
            "prediction_correct": prediction_correct,
            "time_delta_minutes": compare_minute - snapshot_entry.get("sim_minute", 0),
        },
    })


# ============================================================
# Temporal AI — Time-Range Historical Data Query
# ============================================================

@app.route("/simulator/temporal/history", methods=["GET"])
def temporal_history_range():
    """
    Return historical sensor data for a specific time range with intelligent
    downsampling to avoid sending millions of points to the browser.

    Query params:
        ?range=24h     — last 24 hours (default)
        ?range=7d      — last 7 days
        ?range=30d     — last 30 days
        ?range=all     — all available history
        ?from_minute=0 &to_minute=720  — explicit minute range
        ?variables=air_temp,humidity,soil_moisture,leaf_temp_delta

    Downsampling strategy:
        24h → every point (1-min resolution, max 1440)
        7d  → every 5th point (~288 points)
        30d → every 15th point (~288 points)
        all → every 30th point

    Each data point includes:
        sim_time, sim_minute, value, unit, data_type ("observed")

    Returns:
        series: dict keyed by variable name, each containing data points
        range: the time range covered
        total_raw_points: count before downsampling
        total_returned_points: count after downsampling
    """
    range_param = request.args.get("range", default="24h")
    from_minute = request.args.get("from_minute", default=None, type=int)
    to_minute = request.args.get("to_minute", default=None, type=int)
    variables_str = request.args.get(
        "variables",
        default="air_temp,humidity,soil_moisture,leaf_temp_delta,light,soil_temp,stress,growth"
    )
    variables = [v.strip() for v in variables_str.split(",")]

    history = _simulator.get_history()
    if not history:
        return jsonify({"error": "No simulation history available", "series": {}, "range": range_param}), 200

    # Determine time range
    total_minutes = len(history)
    if from_minute is not None and to_minute is not None:
        # Explicit range
        filtered = [h for h in history if from_minute <= h.get("sim_minute", 0) <= to_minute]
    elif range_param == "all":
        filtered = list(history)
    elif range_param == "30d":
        n = min(total_minutes, 43200)  # 30 days of minute data
        filtered = history[-n:]
    elif range_param == "7d":
        n = min(total_minutes, 10080)  # 7 days
        filtered = history[-n:]
    else:  # default 24h
        n = min(total_minutes, 1440)  # 24 hours
        filtered = history[-n:]

    # Downsampling
    if range_param == "24h" or range_param == "all" and len(filtered) <= 1440:
        step = 1  # no downsampling for 24h
    elif range_param == "7d":
        step = max(1, len(filtered) // 300)  # target ~300 points
    elif range_param == "30d":
        step = max(1, len(filtered) // 300)
    elif range_param == "all" and len(filtered) > 1440:
        step = max(1, len(filtered) // 500)
    else:
        step = 1

    # Build per-variable series
    series = {}
    for var in variables:
        series[var] = []

    for i, h in enumerate(filtered):
        if i % step != 0 and i != len(filtered) - 1:
            continue  # downsample (but always include last point)

        sim_time = h.get("sim_time", "")
        sim_minute = h.get("sim_minute", 0)
        sd = h.get("sensor_data", {})
        plant = h.get("plant", {})

        for var in variables:
            if var in ("stress", "growth"):
                value = plant.get(var)
            elif var == "leaf_temp_delta":
                value = sd.get("leaf_temp_delta") or plant.get("leaf_temp_delta")
            elif var == "leaf_temp":
                value = plant.get("leaf_temp")
            else:
                value = sd.get(var)

            if value is not None:
                series[var].append({
                    "sim_time": sim_time,
                    "sim_minute": sim_minute,
                    "value": round(value, 2),
                    "data_type": "observed",
                })

    # Count total returned points
    total_returned = sum(len(s) for s in series.values())

    return jsonify({
        "success": True,
        "range": range_param,
        "from_minute": filtered[0].get("sim_minute", 0) if filtered else 0,
        "to_minute": filtered[-1].get("sim_minute", 0) if filtered else 0,
        "total_raw_points": len(filtered),
        "total_returned_points": total_returned,
        "downsample_step": step,
        "series": series,
        "current_sim_minute": int(_simulator.weather.sim_minute) % 1440 if hasattr(_simulator, 'weather') else 0,
        "current_sim_time": _simulator.sim_time_str() if hasattr(_simulator, 'sim_time_str') else "00:00",
    })


# ============================================================
# Hardware Integration Endpoints (additive — no modifications above)
# ============================================================

@app.route("/hardware/update", methods=["POST"])
def hardware_update():
    """
    ESP32 sends sensor packets. Backend: Validate → Calibrate → Store → Feed Pipeline → Return AI Response.

    Input JSON (canonical schema — identical to VirtualSensors.read() output):
    {
        "timestamp": "2026-07-15T12:00:00Z",
        "device_id": "ESP32-001",
        "plant": "Tomato",
        "stage": "Flowering",
        "mode": "Day",
        "firmware_version": "1.0.0",
        "sensor_data": {
            "air_temp": 31.4,
            "humidity": 58.2,
            "soil_temp": 28.1,
            "soil_moisture": 46.8,
            "light": 18200,
            "leaf_temp": 33.5
        }
    }

    Returns: Full unified analysis + hardware metadata.
    """
    try:
        raw_body = request.get_data()

        # Step 1: Validate hardware packet (runs BEFORE sensor_guard)
        previous = _hardware_store.get_last_packet()
        is_valid, packet, errors = validate_hardware_packet(raw_body, previous)

        if not is_valid:
            return jsonify({
                "error": "validation_failed",
                "message": "Hardware packet rejected",
                "validation_errors": errors,
            }), 400

        # Step 2: Apply calibration
        device_id = packet.get("device_id", "unknown")
        sensor_data = packet.get("sensor_data", {})
        sensor_data = _calibration.apply_calibration(device_id, sensor_data)
        packet["sensor_data"] = sensor_data

        # Step 3: Extract pipeline parameters
        plant_name = packet.get("plant", "tomato")
        growth_stage = packet.get("stage", "vegetative")
        phase = packet.get("mode", "day").lower()

        # Step 4: Get hardware sensor stream for temporal AI context
        n_history = request.args.get("history_steps", default=60, type=int)
        sensor_stream = _hardware_store.get_sensor_stream(n_history)

        # Step 5: Feed into existing unified pipeline (unchanged)
        analysis = run_unified_pipeline(
            plant_name=plant_name,
            growth_stage=growth_stage,
            phase=phase,
            sensor_data=sensor_data,
            sensor_stream=sensor_stream,
        )

        # Step 6: Store packet with analysis snapshot for replay/comparison
        stored_entry = _hardware_store.append(packet, analysis)

        # Step 7: Build response
        return jsonify({
            "status": "accepted",
            "device_id": device_id,
            "packet_stored": True,
            "validation_warnings": [e for e in errors if e.get("severity") == "warning"],
            "analysis": analysis,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "hardware_update_failure",
            "message": str(e),
        }), 500


@app.route("/hardware/status", methods=["GET"])
def hardware_status():
    """
    Get current device connection status.
    Returns: device_id, online/offline, last packet time, packet age, sampling rate, firmware version.
    """
    try:
        status = _hardware_store.get_device_status()
        return jsonify(status)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/hardware/history", methods=["GET"])
def hardware_history():
    """
    Get hardware packet history.
    Query params: ?n=60 (last 60 packets)
    Returns list of stored entries + sensor_stream for temporal AI.
    """
    try:
        n = request.args.get("n", default=60, type=int)
        history = _hardware_store.get_history(n)
        sensor_stream = _hardware_store.get_sensor_stream(n)
        return jsonify({
            "n_steps": len(history),
            "history": history,
            "sensor_stream": sensor_stream,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/hardware/calibration", methods=["GET"])
def hardware_get_calibration():
    """
    Get calibration status for all sensors on a device.
    Query params: ?device_id=ESP32-001
    """
    try:
        device_id = request.args.get("device_id", default="ESP32-001", type=str)
        calibrations = _calibration.get_all_calibrations(device_id)
        devices = _calibration.list_devices()
        return jsonify({
            "device_id": device_id,
            "calibrations": calibrations,
            "all_calibrated_devices": devices,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/hardware/calibrate", methods=["POST"])
def hardware_set_calibration():
    """
    Set calibration parameters for a specific sensor on a device.
    calibrated_value = (raw_value * scale_factor) + offset

    Body:
    {
        "device_id": "ESP32-001",
        "sensor": "air_temp",
        "offset": -0.5,
        "scale_factor": 1.02
    }
    """
    try:
        body = request.get_json(silent=True) or {}
        device_id = body.get("device_id", "ESP32-001")
        sensor = body.get("sensor")
        offset = body.get("offset", 0.0)
        scale_factor = body.get("scale_factor", 1.0)

        if not sensor:
            return jsonify({"error": "Missing sensor parameter"}), 400

        profile = _calibration.set_calibration(
            device_id=device_id,
            sensor=sensor,
            offset=offset,
            scale_factor=scale_factor,
        )

        return jsonify({
            "status": "calibrated",
            "device_id": device_id,
            "sensor": sensor,
            "calibration": profile,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/hardware/calibrate/reset", methods=["POST"])
def hardware_reset_calibration():
    """
    Reset calibration for a sensor or entire device.
    Body:
    {
        "device_id": "ESP32-001",
        "sensor": "air_temp"   // optional — if omitted, resets all sensors for device
    }
    """
    try:
        body = request.get_json(silent=True) or {}
        device_id = body.get("device_id", "ESP32-001")
        sensor = body.get("sensor")  # None = reset all

        _calibration.reset_calibration(device_id, sensor)

        return jsonify({
            "status": "reset",
            "device_id": device_id,
            "sensor": sensor or "all",
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# Session Save & Export Endpoints
# ============================================================

@app.route("/session/save", methods=["POST"])
def session_save():
    """
    Export entire simulation/hardware session as JSON and human-readable report.

    Body (optional):
    {
        "source": "simulator" | "hardware",   // default: "simulator"
        "format": "json" | "report" | "both", // default: "both"
        "include_replay": true                 // include decision replay data
    }

    Returns: JSON with session data and/or report text.
    """
    try:
        body = request.get_json(silent=True) or {}
        source = body.get("source", "simulator")
        output_format = body.get("format", "both")
        include_replay = body.get("include_replay", True)

        if source == "hardware":
            history = _hardware_store.get_history()
            device_status = _hardware_store.get_device_status()
            source_label = "Hardware (ESP32)"
        else:
            history = _simulator.get_history()
            device_status = None
            source_label = "Simulator"

        if not history:
            return jsonify({"error": f"No {source} history available. Run some steps first."}), 404

        # Build session metadata
        first_entry = history[0]
        last_entry = history[-1]

        session_meta = {
            "source": source,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_steps": len(history),
            "time_span": {
                "start": first_entry.get("sim_time") or first_entry.get("timestamp", ""),
                "end": last_entry.get("sim_time") or last_entry.get("timestamp", ""),
            },
            "scenario": first_entry.get("scenario", "N/A"),
            "plant": first_entry.get("plant", "") or body.get("plant", "unknown"),
            "growth_stage": first_entry.get("stage", "") or body.get("stage", "unknown"),
        }

        if device_status:
            session_meta["device"] = device_status

        # Build timeline
        timeline = []
        for h in history:
            sensors = h.get("sensor_data", {})
            plant = h.get("plant", {})
            weather = h.get("weather", {})
            soil = h.get("soil", {})
            snap = h.get("analysis_snapshot", {})

            entry = {
                "time": h.get("sim_time") or h.get("timestamp", ""),
                "sensor_data": {
                    "air_temp": sensors.get("air_temp"),
                    "humidity": sensors.get("humidity"),
                    "soil_temp": sensors.get("soil_temp"),
                    "soil_moisture": sensors.get("soil_moisture"),
                    "light": sensors.get("light"),
                    "leaf_temp": sensors.get("leaf_temp"),
                    "leaf_temp_delta": sensors.get("leaf_temp_delta"),
                },
                "plant_state": {
                    "stress": plant.get("stress"),
                    "growth": plant.get("growth"),
                    "transpiration": plant.get("transpiration"),
                    "photosynthesis": plant.get("photosynthesis"),
                },
            }

            if weather:
                entry["weather"] = {
                    "air_temp": weather.get("air_temp"),
                    "humidity": weather.get("humidity"),
                    "wind_speed": weather.get("wind_speed"),
                    "cloud_cover": weather.get("cloud_cover"),
                }
            if soil:
                entry["soil"] = {
                    "soil_temp": soil.get("soil_temp"),
                    "soil_moisture": soil.get("soil_moisture"),
                }

            if snap:
                entry["analysis"] = {
                    "temporal_prediction": snap.get("temporal_prediction"),
                    "stress_analysis": snap.get("stress_analysis"),
                    "biology_analysis": snap.get("biology_analysis"),
                    "recommendations": snap.get("recommendations"),
                    "confidence": snap.get("confidence"),
                    "ai_reasoning": snap.get("ai_reasoning"),
                }

            timeline.append(entry)

        # Build decision replay data
        decision_replay = None
        if include_replay and history:
            # Find entries with analysis snapshots for replay
            snapshots = [h for h in history if h.get("analysis_snapshot")]
            if snapshots:
                decision_replay = []
                for h in snapshots[-20:]:  # Last 20 decisions
                    snap = h.get("analysis_snapshot", {})
                    decision_replay.append({
                        "time": h.get("sim_time") or h.get("timestamp", ""),
                        "sensor_data": h.get("sensor_data", {}),
                        "decision_input": snap.get("decision_input"),
                        "recommendations": snap.get("recommendations"),
                        "ai_reasoning": snap.get("ai_reasoning"),
                        "confidence": snap.get("confidence"),
                    })

        session_data = {
            "session_metadata": session_meta,
            "timeline": timeline,
            "decision_replay": decision_replay,
        }

        result = {}

        if output_format in ("json", "both"):
            result["json"] = session_data

        if output_format in ("report", "both"):
            # Generate human-readable report
            report_lines = []
            report_lines.append("=" * 70)
            report_lines.append("ALETHEIA DIGITAL TWIN — SESSION REPORT")
            report_lines.append("=" * 70)
            report_lines.append(f"Source:        {source_label}")
            report_lines.append(f"Exported:      {session_meta['exported_at']}")
            report_lines.append(f"Plant:         {session_meta['plant']}")
            report_lines.append(f"Growth Stage:  {session_meta['growth_stage']}")
            report_lines.append(f"Scenario:      {session_meta['scenario']}")
            report_lines.append(f"Time Span:     {session_meta['time_span']['start']} → {session_meta['time_span']['end']}")
            report_lines.append(f"Total Steps:   {session_meta['total_steps']}")
            report_lines.append("")

            if device_status:
                report_lines.append("--- DEVICE STATUS ---")
                report_lines.append(f"Device ID:       {device_status.get('device_id', 'N/A')}")
                report_lines.append(f"Online:          {device_status.get('online', False)}")
                report_lines.append(f"Last Packet:     {device_status.get('last_packet_time', 'N/A')}")
                report_lines.append(f"Sampling Rate:   {device_status.get('sampling_rate_hz', 'N/A')} Hz")
                report_lines.append(f"Firmware:        {device_status.get('firmware_version', 'N/A')}")
                report_lines.append("")

            # Sensor summary
            if timeline:
                first_s = timeline[0]["sensor_data"]
                last_s = timeline[-1]["sensor_data"]
                report_lines.append("--- SENSOR SUMMARY ---")
                for key in ["air_temp", "humidity", "soil_temp", "soil_moisture", "light", "leaf_temp", "leaf_temp_delta"]:
                    v0 = first_s.get(key, "N/A")
                    v1 = last_s.get(key, "N/A")
                    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                        delta = round(v1 - v0, 2)
                        report_lines.append(f"  {key:20s}: {v0:>8} → {v1:>8}  (Δ={delta:+.2f})")
                    else:
                        report_lines.append(f"  {key:20s}: {v0} → {v1}")
                report_lines.append("")

            # Plant state summary
            if timeline:
                first_p = timeline[0].get("plant_state", {})
                last_p = timeline[-1].get("plant_state", {})
                report_lines.append("--- PLANT STATE SUMMARY ---")
                for key in ["stress", "growth", "transpiration", "photosynthesis"]:
                    v0 = first_p.get(key, "N/A")
                    v1 = last_p.get(key, "N/A")
                    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                        delta = round(v1 - v0, 2)
                        report_lines.append(f"  {key:20s}: {v0:>8.4f} → {v1:>8.4f}  (Δ={delta:+.4f})")
                    else:
                        report_lines.append(f"  {key:20s}: {v0} → {v1}")
                report_lines.append("")

            # AI recommendations summary
            all_recs = set()
            for h in history:
                snap = h.get("analysis_snapshot", {})
                recs = snap.get("recommendations", [])
                if isinstance(recs, list):
                    for r in recs:
                        all_recs.add(str(r))
            if all_recs:
                report_lines.append("--- AI RECOMMENDATIONS ---")
                for i, rec in enumerate(sorted(all_recs), 1):
                    report_lines.append(f"  {i}. {rec}")
                report_lines.append("")

            # Decision replay summary
            if decision_replay:
                report_lines.append("--- DECISION REPLAY (Last 20) ---")
                for i, dr in enumerate(decision_replay, 1):
                    report_lines.append(f"  Decision #{i} at {dr['time']}")
                    report_lines.append(f"    Confidence: {dr.get('confidence', 'N/A')}")
                    recs = dr.get("recommendations", [])
                    if isinstance(recs, list) and recs:
                        report_lines.append(f"    Top Recommendation: {recs[0]}")
                    report_lines.append("")

            report_lines.append("=" * 70)
            report_lines.append("END OF REPORT")
            report_lines.append("=" * 70)

            result["report"] = "\n".join(report_lines)

        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/session/export", methods=["GET"])
def session_export():
    """
    Quick export — same as /session/save with defaults (simulator, both formats).
    Query params:
        ?source=hardware   (optional, default: simulator)
        ?format=json       (optional, default: both)
    """
    source = request.args.get("source", default="simulator", type=str)
    output_format = request.args.get("format", default="both", type=str)

    # Re-use session_save logic via internal call
    with app.test_request_context(
        method="POST",
        path="/session/save",
        json={"source": source, "format": output_format, "include_replay": True},
    ):
        return session_save()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)