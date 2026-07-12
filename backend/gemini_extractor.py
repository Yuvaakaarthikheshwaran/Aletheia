import os
import json
import traceback
from dotenv import load_dotenv

# Load .env relative to this file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

_client = None


def _get_client():
    """Lazy-initialize Gemini client. Never crashes on import."""
    global _client
    if _client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def extract_plant_profile(plant_name, tavily_results):
    """
    Extract plant biology profile using Gemini LLM.
    Returns None gracefully on any failure.
    """
    try:
        client = _get_client()
    except Exception as e:
        print(f"[Gemini] Client init failed: {e}")
        return None

    combined_text = ""
    for result in tavily_results.get("results", []):
        combined_text += result.get("content", "") + "\n"

    prompt = f"""
You are an agricultural intelligence AI.

Extract plant biological profile for {plant_name}.

Return STRICT JSON only.

Format:
{{
  "plant": "{plant_name}",
  "day_profile": {{
    "air_temp": [min,max],
    "humidity": [min,max],
    "soil_moisture": [min,max],
    "soil_temp": [min,max],
    "light": [min,max],
    "leaf_temp_delta": [min,max]
  }},
  "night_profile": {{
    "air_temp": [min,max],
    "humidity": [min,max],
    "soil_moisture": [min,max],
    "soil_temp": [min,max],
    "light": [min,max],
    "leaf_temp_delta": [min,max]
  }},
  "growth_stages": {{
    "germination": {{}},
    "seedling": {{}},
    "vegetative": {{}},
    "flowering": {{}},
    "fruiting": {{}}
  }},
  "stress_thresholds": {{
    "heat_stress": 35,
    "severe_heat_stress": 40,
    "cold_stress": 12,
    "drought_stress": 30,
    "waterlogging_stress": 90
  }}
}}

Fill missing values intelligently.

Data:
{combined_text}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        print(f"[Gemini] API call failed: {e}")
        traceback.print_exc()
        return None