import os
import json
import traceback
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env relative to this file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

_client = None


def _get_client():
    """Lazy-initialize OpenRouter client. Never crashes on import."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        from openai import OpenAI
        _client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    return _client


def extract_with_openrouter(plant_name, tavily_results):
    """
    Extract plant biology profile using OpenRouter LLM.
    Falls back gracefully if API is unavailable.
    """
    try:
        client = _get_client()
    except Exception as e:
        logger.error(f"Client init failed: {e}")
        return None

    text = ""
    for result in tavily_results.get("results", []):
        text += result.get("content", "") + "\n"

    prompt = f"""
Extract full plant biology profile for {plant_name}.
Return STRICT JSON only.

Data:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="openrouter/auto",
            messages=[
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        result = response.choices[0].message.content.strip()

        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()
        elif result.startswith("```"):
            result = result.replace("```", "").strip()

        return json.loads(result)

    except Exception as e:
        logger.error(f"API call failed: {e}")
        traceback.print_exc()
        return None
