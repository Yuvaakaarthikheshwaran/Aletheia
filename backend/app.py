
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

app = Flask(__name__)
CORS(app)


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
    """
    body = request.get_json(silent=True) or {}
    dt = body.get("dt_minutes", _simulator.speed)

    # Step simulator
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)