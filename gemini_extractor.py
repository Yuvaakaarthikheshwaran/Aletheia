import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def extract_plant_profile(plant_name, tavily_results):
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

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt
    )

    text = response.text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)