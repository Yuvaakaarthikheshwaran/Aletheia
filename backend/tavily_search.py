
import os
import traceback
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env relative to this file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Multi-Key Rotation ---
# Keys are tried in order. If one fails with a usage/rate-limit error,
# it's marked exhausted and the next key is used.
# Order: TAVILY_API_KEY_1 (new), TAVILY_API_KEY_BE (new), TAVILY_API_KEY (old/fallback)
_KEY_POOL = [
    "TAVILY_API_KEY_1",
    "TAVILY_API_KEY_BE",
    "TAVILY_API_KEY",
]
_exhausted_keys = set()
_current_key_index = 0
_client = None


def _get_client():
    """
    Lazy-initialize Tavily client with automatic key rotation.
    If the current key is exhausted, tries the next one in the pool.
    Never crashes on import.
    """
    global _client, _current_key_index

    if _client is not None:
        return _client

    from tavily import TavilyClient

    # Try each key in the pool until one works
    for _ in range(len(_KEY_POOL)):
        idx = _current_key_index % len(_KEY_POOL)
        env_var = _KEY_POOL[idx]
        api_key = os.getenv(env_var)

        if env_var in _exhausted_keys:
            _current_key_index += 1
            continue

        if not api_key:
            logger.warning(f"Key env var '{env_var}' not set, skipping")
            _current_key_index += 1
            continue

        try:
            _client = TavilyClient(api_key=api_key)
            logger.info(f"Using key: {env_var}")
            return _client
        except Exception as e:
            logger.error(f"Failed to init client with {env_var}: {e}")
            _current_key_index += 1

    raise ValueError("All Tavily API keys exhausted or unavailable")


def _mark_key_exhausted():
    """Mark the current key as exhausted and reset client so next call rotates."""
    global _client, _current_key_index
    idx = _current_key_index % len(_KEY_POOL)
    env_var = _KEY_POOL[idx]
    _exhausted_keys.add(env_var)
    logger.warning(f"Marked {env_var} as EXHAUSTED")
    _client = None
    _current_key_index += 1


def search_plant_tavily(plant_name):
    """
    Search Tavily for plant biology data.
    Automatically rotates API keys on usage-limit errors.
    Returns None gracefully if ALL keys are exhausted.
    """
    query = f"""
    {plant_name} plant optimal day temperature night temperature humidity
    soil moisture soil temperature light requirements growth stages
    heat stress cold stress drought stress
    """

    # Try up to the number of keys in the pool
    for attempt in range(len(_KEY_POOL)):
        try:
            client = _get_client()
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=8
            )
            logger.info("SUCCESS")
            return response

        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"ERROR: {e}")

            # Check if this is a usage-limit / rate-limit error
            is_usage_error = any(kw in error_msg for kw in [
                "usage limit", "exceeds", "forbidden", "429",
                "rate limit", "quota", "insufficient", "plan",
            ])

            if is_usage_error:
                _mark_key_exhausted()
                logger.warning(f"Rotating to next key (attempt {attempt + 1}/{len(_KEY_POOL)})")
                continue  # try next key
            else:
                # Not a usage error — don't rotate, just fail
                traceback.print_exc()
                return None

    # All keys exhausted
    logger.error("ALL KEYS EXHAUSTED — returning None")
    return None

