import os
import json
import traceback
from dotenv import load_dotenv

# Load .env relative to this file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

_client = None


def _get_client():
    """Lazy-initialize DeepSeek client. Never crashes on import."""
    global _client
    if _client is None:
        from openai import OpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    return _client


def extract_plant_profile(plant_name, tavily_results):
    """
    Extract plant biology profile using DeepSeek LLM.
    Returns None gracefully on any failure.
    """
    try:
        client = _get_client()
    except Exception as e:
        print(f"[DeepSeek] Client init failed: {e}")
        return None

    combined_text = ""
    for result in tavily_results.get("results", []):
        combined_text += result.get("content", "") + "\n"

    prompt = f"""
You are an agricultural AI expert.

Extract plant biology profile for {plant_name}.

Return STRICT JSON only.

Required JSON:
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
    "heat_stress": value,
    "severe_heat_stress": value,
    "cold_stress": value,
    "drought_stress": value,
    "waterlogging_stress": value
  }}
}}

Fill missing values intelligently.

Data:
{combined_text}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        text = response.choices[0].message.content.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        print(f"[DeepSeek] API call failed: {e}")
        traceback.print_exc()
        return None
