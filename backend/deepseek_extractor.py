import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def extract_plant_profile(plant_name, tavily_results):
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

    return json.loads(text)
