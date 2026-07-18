import json
import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "ai_reasoning_cache.json")
CACHE_EXPIRY_HOURS = 24  # Cache AI reasoning for 24 hours

_ai_reasoning_cache = {}

def _load_cache():
    global _ai_reasoning_cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                _ai_reasoning_cache = json.load(f)
            except json.JSONDecodeError:
                _ai_reasoning_cache = {}
    else:
        _ai_reasoning_cache = {}

def _save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_ai_reasoning_cache, f, indent=2)

def get_cached_ai_reasoning(cache_key: str) -> dict | None:
    if not _ai_reasoning_cache:
        _load_cache()

    cached_entry = _ai_reasoning_cache.get(cache_key)
    if cached_entry:
        cached_time_str = cached_entry.get("timestamp")
        if cached_time_str:
            cached_time = datetime.fromisoformat(cached_time_str)
            # Make sure cached_time is timezone-aware for comparison
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            if current_time - cached_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                logger.info(f"Cache hit for {cache_key}")
                return cached_entry.get("reasoning")
            else:
                logger.info(f"Cache expired for {cache_key}")
                del _ai_reasoning_cache[cache_key]
                _save_cache() # Clean up expired entry
        
    return None

def store_ai_reasoning(cache_key: str, reasoning_data: dict):
    _ai_reasoning_cache[cache_key] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reasoning": reasoning_data,
    }
    _save_cache()

# Initial load when module is imported
_load_cache()
