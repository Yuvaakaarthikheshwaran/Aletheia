"""
Aletheia Unified Production Pipeline

Client Request → Flask API → Plant Lookup → Tavily Search (cached)
→ Plant Data Parser → Temporal AI Prediction → Biology Engine
→ Unified Decision Engine → OpenRouter AI Explanation → Unified JSON Response

Reuses every existing module. No duplicated logic.
"""

import sys
import os
import traceback
import json
import logging

logger = logging.getLogger(__name__)

# Ensure ai/ is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_DIR = os.path.abspath(os.path.join(BASE_DIR, "../ai"))
if AI_DIR not in sys.path:
    sys.path.append(AI_DIR)

from unified_engine import unified_analysis
from decision_engine import analyze as decision_analyze
from sensor_guard import validate_sensor_data

from backend.plant_pipeline import get_dynamic_plant_profile
from backend.biology_engine import evaluate_biology
from backend.plant_cache import get_cached_plant, store_plant
from backend.tavily_search import search_plant_tavily
from backend.parser_extractor import parse_plant_data
from backend.openrouter_extractor import extract_with_openrouter
from backend.plant_profile_schema import DEFAULT_PROFILE
from backend.ai_reasoning_cache import get_cached_ai_reasoning, store_ai_reasoning
import hashlib


def _get_or_fetch_plant_profile(plant_name: str) -> dict:
    """
    Check cache first. If stale or missing, query Tavily, parse, cache, and return.
    Never crashes on Tavily failure — falls back to DEFAULT_PROFILE.
    """
    plant_key = plant_name.lower().strip()

    # 1. Try cache
    cached = get_cached_plant(plant_key)
    if cached:
        return cached

    # 2. Try Tavily + Parser
    try:
        tavily_results = search_plant_tavily(plant_key)
        if tavily_results and tavily_results.get("results"):
            profile, confidence = parse_plant_data(plant_key, tavily_results)
            if profile and confidence > 0:
                store_plant(plant_key, profile)
                return profile
    except Exception as e:
        logger.warning(f"Tavily/Parser fallback triggered: {e}")
        traceback.print_exc()

    # 3. Fallback to default profile
    fallback = dict(DEFAULT_PROFILE)
    fallback["plant"] = plant_key
    fallback["_source"] = "default_fallback"
    return fallback


def _build_temporal_input(sensor_data: dict, sensor_stream: list = None) -> dict:
    """
    Build temporal input from current sensor data + optional historical stream.

    The Temporal AI model expects 12 features:
      air_temp_prev2, air_temp_prev1, air_temp,
      humidity_prev2, humidity_prev1, humidity,
      soil_moisture_prev2, soil_moisture_prev1, soil_moisture,
      leaf_temp_delta_prev2, leaf_temp_delta_prev1, leaf_temp_delta

    When sensor_stream is provided (list of historical sensor_data dicts from
    the simulator), real values are extracted for prev1/prev2. Otherwise,
    synthetic fallback values are used.

    Historical window logic:
      - prev1 = the most recent historical entry (t-1 step)
      - prev2 = the second most recent historical entry (t-2 steps)
      - If fewer than 2 entries exist, synthetic fallback fills the gaps
    """
    air_temp = sensor_data.get("air_temp", 30)
    humidity = sensor_data.get("humidity", 50)
    soil_moisture = sensor_data.get("soil_moisture", 50)
    leaf_temp_delta = sensor_data.get("leaf_temp_delta", 3)

    # Default synthetic fallbacks
    prev2_air = max(air_temp - 4, 0)
    prev1_air = max(air_temp - 2, 0)
    prev2_hum = min(humidity + 8, 100)
    prev1_hum = min(humidity + 4, 100)
    prev2_sm = min(soil_moisture + 8, 100)
    prev1_sm = min(soil_moisture + 4, 100)
    prev2_ld = max(leaf_temp_delta - 2, 0)
    prev1_ld = max(leaf_temp_delta - 1, 0)

    # Override with real historical values when available
    if sensor_stream and len(sensor_stream) >= 1:
        prev1 = sensor_stream[-1]
        prev1_air = prev1.get("air_temp", prev1_air)
        prev1_hum = prev1.get("humidity", prev1_hum)
        prev1_sm = prev1.get("soil_moisture", prev1_sm)
        prev1_ld = prev1.get("leaf_temp_delta", prev1_ld)

    if sensor_stream and len(sensor_stream) >= 2:
        prev2 = sensor_stream[-2]
        prev2_air = prev2.get("air_temp", prev2_air)
        prev2_hum = prev2.get("humidity", prev2_hum)
        prev2_sm = prev2.get("soil_moisture", prev2_sm)
        prev2_ld = prev2.get("leaf_temp_delta", prev2_ld)

    return {
        "air_temp_prev2": prev2_air,
        "air_temp_prev1": prev1_air,
        "air_temp": air_temp,
        "humidity_prev2": prev2_hum,
        "humidity_prev1": prev1_hum,
        "humidity": humidity,
        "soil_moisture_prev2": prev2_sm,
        "soil_moisture_prev1": prev1_sm,
        "soil_moisture": soil_moisture,
        "leaf_temp_delta_prev2": prev2_ld,
        "leaf_temp_delta_prev1": prev1_ld,
        "leaf_temp_delta": leaf_temp_delta,
    }


def _build_decision_input(sensor_data: dict) -> dict:
    """
    Build the 10-feature input required by decision_engine.analyze().
    Computes derived features (rates, leaf_temp) from raw sensor data.
    """
    air_temp = sensor_data.get("air_temp", 30)
    humidity = sensor_data.get("humidity", 50)
    leaf_temp_delta = sensor_data.get("leaf_temp_delta", 3)

    # Compute derived features
    air_temp_prev1 = sensor_data.get("air_temp_prev1", max(air_temp - 2, 0))
    humidity_prev1 = sensor_data.get("humidity_prev1", min(humidity + 4, 100))
    leaf_temp_delta_prev1 = sensor_data.get("leaf_temp_delta_prev1", max(leaf_temp_delta - 1, 0))

    return {
        "air_temp": air_temp,
        "humidity": humidity,
        "light": sensor_data.get("light", 800),
        "leaf_temp": air_temp + leaf_temp_delta,
        "leaf_temp_delta": leaf_temp_delta,
        "soil_moisture": sensor_data.get("soil_moisture", 50),
        "soil_temp": sensor_data.get("soil_temp", 25),
        "air_temp_rate": air_temp - air_temp_prev1,
        "humidity_rate": humidity - humidity_prev1,
        "leaf_temp_rate": leaf_temp_delta - leaf_temp_delta_prev1,
    }


def _call_openrouter_reasoning(
    plant_name: str,
    plant_profile: dict,
    sensor_data: dict,
    temporal_prediction: dict,
    biology_analysis: dict,
    stress_analysis: dict,
    confidence_scores: dict,
) -> dict:
    """
    Call OpenRouter for reasoning/explanation only.
    OpenRouter does NOT perform calculations — it generates narrative.
    Uses the lazy-initialized client from openrouter_extractor.
    Falls back gracefully if OpenRouter is unavailable.
    """
    try:
        # Use the existing lazy client from openrouter_extractor
        from backend.openrouter_extractor import _get_client as _get_or_client
        client = _get_or_client()

        # Build a structured context for the LLM
        context = {
            "plant": plant_name,
            "plant_profile_summary": {
                "day_temp_range": plant_profile.get("day_profile", {}).get("air_temp", [20, 30]),
                "night_temp_range": plant_profile.get("night_profile", {}).get("air_temp", [16, 24]),
                "humidity_range": plant_profile.get("day_profile", {}).get("humidity", [50, 70]),
                "stress_thresholds": plant_profile.get("stress_thresholds", {}),
            },
            "current_sensor_readings": sensor_data,
            "temporal_prediction": temporal_prediction,
            "biology_health_score": biology_analysis.get("health_score", 0),
            "biology_warnings": biology_analysis.get("warnings", []),
            "stress_analysis": stress_analysis,
            "confidence_scores": confidence_scores,
        }

        prompt = f"""
You are Aletheia, an autonomous plant intelligence AI.

Analyze the following plant health data and generate:
1. A concise explanation of the plant's current state
2. A diagnosis of any detected issues
3. Specific, actionable recommendations
4. A confidence narrative explaining how reliable this assessment is

Context (JSON):
{json.dumps(context, indent=2)}

Return STRICT JSON only:
{{
  "explanation": "string",
  "diagnosis": "string",
  "recommendations": ["string", "string", "string"],
  "confidence_narrative": "string"
}}
"""

        llm_response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[
                {"role": "system", "content": "You are Aletheia plant intelligence. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1200,
        )

        raw = (llm_response.choices[0].message.content or "").strip()
        if not raw:
            raise ValueError("OpenRouter returned empty response")
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        # Try strict parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Attempt to repair truncated JSON by closing braces/quotes
            # Count braces to see if it's truncated
            open_braces = raw.count("{") - raw.count("}")
            if open_braces > 0:
                # Try closing the JSON structure
                repaired = raw.rstrip(",\n\r\t ") + ("}" * open_braces)
                try:
                    result = json.loads(repaired)
                    logger.info("OpenRouter JSON repaired (truncated response)")
                    return result
                except json.JSONDecodeError:
                    pass
            # If repair fails, try extracting just the fields we can find via regex
            import re
            partial = {}
            for field in ["explanation", "diagnosis", "confidence_narrative"]:
                m = re.search(rf'"{field}"\s*:\s*"([^"]*)', raw)
                if m:
                    partial[field] = m.group(1)
            recs_m = re.findall(r'"recommendations"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
            if recs_m:
                rec_strs = re.findall(r'"([^"]*)"', recs_m[0])
                partial["recommendations"] = rec_strs if rec_strs else ["Review sensor data for anomalies"]
            if partial:
                partial.setdefault("explanation", "Partial AI analysis recovered from truncated response.")
                partial.setdefault("diagnosis", "AI response was truncated — review biology engine data.")
                partial.setdefault("recommendations", ["Monitor sensor readings closely"])
                partial.setdefault("confidence_narrative", "Confidence reduced due to truncated AI response.")
                partial["_partial"] = True
                logger.info("OpenRouter partial extraction succeeded")
                return partial
            raise  # re-raise original error if nothing could be salvaged

    except Exception as e:
        logger.warning(f"OpenRouter fallback triggered: {e}")
        traceback.print_exc()
        return {
            "explanation": "AI reasoning engine unavailable. Analysis based on sensor data and biological models.",
            "diagnosis": "Unable to generate AI diagnosis at this time.",
            "recommendations": [
                "Monitor sensor readings closely",
                "Check plant for visible stress signs",
                "Review biology engine warnings"
            ],
            "confidence_narrative": "Confidence based on sensor validation and temporal models only.",
            "_fallback": True,
        }


def run_unified_pipeline(
    plant_name: str,
    growth_stage: str,
    phase: str,
    sensor_data: dict,
    sensor_stream: list = None,
) -> dict:
    """
    The single entry point for the Aletheia production pipeline.

    Args:
        plant_name: e.g. "Tomato"
        growth_stage: e.g. "flowering"
        phase: "day" or "night"
        sensor_data: dict of real sensor readings
        sensor_stream: optional list of historical sensor_data dicts
                       (from simulator history) for temporal AI context

    Returns:
        Unified JSON response with all analysis layers.
    """
    response = {
        "plant": plant_name,
        "stage": growth_stage,
        "phase": phase,
        "timestamp": None,  # filled below
    }

    # --- Step 1: Plant Profile (cached Tavily → Parser) ---
    plant_profile = _get_or_fetch_plant_profile(plant_name)
    response["plant_profile"] = plant_profile

    # --- Step 2: Sensor Validation ---
    sensor_result = validate_sensor_data(sensor_data)
    repaired_data = sensor_result["repaired_data"]
    response["sensor_validation"] = {
        "sensor_ok": sensor_result["sensor_ok"],
        "warnings": sensor_result["warnings"],
        "sensor_confidence": sensor_result["sensor_confidence"],
    }

    # --- Step 3: Temporal AI Prediction ---
    temporal_input = _build_temporal_input(repaired_data, sensor_stream)
    temporal_result = unified_analysis(repaired_data, temporal_input)
    response["temporal_prediction"] = temporal_result

    # --- Step 4: Biology Engine ---
    biology_result = evaluate_biology(
        repaired_data,
        plant_profile,
        growth_stage,
        phase,
    )
    response["biology_analysis"] = biology_result

    # --- Step 5: Decision Engine (stress analysis) ---
    decision_input = _build_decision_input(repaired_data)
    decision_result = decision_analyze(decision_input)
    response["stress_analysis"] = {
        "prediction": decision_result.get("prediction"),
        "severity": decision_result.get("severity"),
        "risk_state": decision_result.get("risk_state"),
        "reasons": decision_result.get("reasons"),
        "recommendation": decision_result.get("recommendation"),
    }

    # --- Step 6: Confidence Aggregation ---
    confidence = {
        "sensor_confidence": sensor_result["sensor_confidence"],
        "ai_confidence": decision_result.get("confidence", 0),
        "temporal_confidence": (
            temporal_result.get("future_state", {}).get("future_confidence", 0)
            if temporal_result.get("status") == "ok"
            else 0
        ),
        "biology_health_score": biology_result.get("health_score", 0),
        "overall": 0,
    }
    # Weighted overall confidence
    weights = {"sensor": 0.15, "ai": 0.30, "temporal": 0.25, "biology": 0.30}
    confidence["overall"] = round(
        confidence["sensor_confidence"] * weights["sensor"]
        + confidence["ai_confidence"] * weights["ai"]
        + confidence["temporal_confidence"] * weights["temporal"]
        + confidence["biology_health_score"] * weights["biology"],
        2,
    )
    response["confidence"] = confidence

    # --- Step 7: OpenRouter AI Reasoning ---
    # Generate a cache key based on core inputs for AI reasoning
    # Using a simple hash of relevant data to identify unique reasoning contexts
    reasoning_context_str = json.dumps({
        "plant": plant_name,
        "stage": growth_stage,
        "phase": phase,
        "sensor_summary": {
            "air_temp": repaired_data.get("air_temp"),
            "humidity": repaired_data.get("humidity"),
            "soil_moisture": repaired_data.get("soil_moisture"),
            "leaf_temp_delta": repaired_data.get("leaf_temp_delta"),
        },
        "temporal_prediction_label": temporal_result.get("future_state", {}).get("future_prediction"),
        "stress_prediction_label": response["stress_analysis"].get("prediction"),
    }, sort_keys=True)
    cache_key = hashlib.md5(reasoning_context_str.encode("utf-8")).hexdigest()

    ai_reasoning = get_cached_ai_reasoning(cache_key)
    
    if ai_reasoning:
        logger.info(f"AI Reasoning cache hit for {cache_key[:8]}...")
        ai_reasoning["_source"] = "ai_reasoning_cache"
    else:
        logger.info(f"AI Reasoning cache miss for {cache_key[:8]}... Calling OpenRouter.")
        try:
            ai_reasoning = _call_openrouter_reasoning(
                plant_name=plant_name,
                plant_profile=plant_profile,
                sensor_data=repaired_data,
                temporal_prediction=temporal_result,
                biology_analysis=biology_result,
                stress_analysis=response["stress_analysis"],
                confidence_scores=confidence,
            )
            # If successful, store in cache
            if ai_reasoning and not ai_reasoning.get("_fallback") and not ai_reasoning.get("_partial"):
                store_ai_reasoning(cache_key, ai_reasoning)
        except Exception as e:
            # Catch any OpenRouter specific errors (e.g., 402 Insufficient Credits)
            if hasattr(e, 'response') and e.response.status_code == 402:
                logger.warning(f"OpenRouter API Error (402): {e.response.json().get('error', {}).get('message', 'Insufficient Credits')}")
                logger.info("Falling back to AI Reasoning cache or generic fallback.")
                ai_reasoning = get_cached_ai_reasoning(cache_key)
                if not ai_reasoning:
                    ai_reasoning = {
                        "explanation": "AI reasoning engine unavailable (credits exhausted). Analysis based on sensor data and biological models.",
                        "diagnosis": "Unable to generate AI diagnosis at this time due to API limits.",
                        "recommendations": [
                            "Monitor sensor readings closely",
                            "Check plant for visible stress signs",
                            "Review biology engine warnings"
                        ],
                        "confidence_narrative": "Confidence based on sensor validation and temporal models only; AI reasoning is a fallback.",
                        "_fallback": True,
                        "_api_error": True,
                    }
                else:
                    ai_reasoning["_source"] = "ai_reasoning_cache_fallback"
            else:
                # Re-raise other unexpected exceptions
                raise

    response["ai_reasoning"] = ai_reasoning

    # --- Step 8: Recommendations (merged) ---
    recommendations = []
    # From decision engine
    if decision_result.get("recommendation"):
        recommendations.append(decision_result["recommendation"])
    # From biology warnings
    for w in biology_result.get("warnings", []):
        recommendations.append(w)
    # From AI reasoning
    if ai_reasoning.get("recommendations"):
        recommendations.extend(ai_reasoning["recommendations"])
    # Deduplicate
    response["recommendations"] = list(dict.fromkeys(recommendations))

    # --- Step 9: Timestamp ---
    from datetime import datetime, timezone
    response["timestamp"] = datetime.now(timezone.utc).isoformat()

    return response