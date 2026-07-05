import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


def extract_with_openrouter(plant_name, tavily_results):
    text = ""

    for result in tavily_results.get("results", []):
        text += result.get("content", "") + "\n"

    prompt = f"""
Extract full plant biology profile for {plant_name}.
Return STRICT JSON only.

Data:
{text}
"""

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": "Return only JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response.choices[0].message.content.strip()

    if result.startswith("```json"):
        result = result.replace("```json", "").replace("```", "").strip()

    return json.loads(result)
