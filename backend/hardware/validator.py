"""
Hardware Packet Validator

Validates incoming ESP32 sensor packets against the canonical schema.
Runs BEFORE the existing ai/sensor_guard.py validate_sensor_data().

Rejects:
  - Invalid JSON
  - Missing required fields
  - Impossible values (humidity >100%, negative lux, impossible temps)
  - Impossible sensor jumps (delta > threshold)
  - Invalid timestamps
"""

import json
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional

# Canonical required fields matching VirtualSensors.read() output
REQUIRED_FIELDS = [
    "air_temp",
    "humidity",
    "soil_temp",
    "soil_moisture",
    "light",
    "leaf_temp",
]

# Absolute physical limits (anything outside these is rejected)
ABSOLUTE_LIMITS = {
    "air_temp": (-20.0, 70.0),       # °C — below freezing to extreme greenhouse
    "humidity": (0.0, 100.0),         # % RH
    "soil_temp": (-10.0, 60.0),       # °C
    "soil_moisture": (0.0, 100.0),    # %
    "light": (0.0, 200_000.0),        # lux — direct sunlight ~100k, max ~200k
    "leaf_temp": (-20.0, 75.0),       # °C
}

# Maximum allowed jump between consecutive packets (per sensor)
# Exceeding this triggers a warning but does not reject
MAX_JUMP = {
    "air_temp": 10.0,       # °C per reading
    "humidity": 20.0,       # % per reading
    "soil_temp": 5.0,       # °C per reading
    "soil_moisture": 15.0,  # % per reading
    "light": 50_000.0,      # lux per reading (clouds can cause big swings)
    "leaf_temp": 10.0,      # °C per reading
}

# Required metadata fields in the packet envelope
REQUIRED_META = ["timestamp", "device_id"]


def validate_hardware_packet(
    raw_body: bytes | str | dict,
    previous_packet: Optional[Dict] = None,
) -> Tuple[bool, Dict, list]:
    """
    Validate an incoming ESP32 hardware packet.

    Args:
        raw_body: Raw request body (bytes, string, or already-parsed dict)
        previous_packet: The last accepted packet from this device (for jump detection)

    Returns:
        (is_valid, normalized_packet, errors)
        - is_valid: True if packet passes all checks
        - normalized_packet: The cleaned packet dict (only if valid)
        - errors: List of error dicts with 'field' and 'message'
    """
    errors = []

    # --- Step 1: Parse JSON ---
    if isinstance(raw_body, bytes):
        try:
            raw_body = raw_body.decode("utf-8")
        except UnicodeDecodeError as e:
            return False, {}, [{"field": "body", "message": f"Invalid UTF-8 encoding: {str(e)}"}]

    if isinstance(raw_body, str):
        try:
            packet = json.loads(raw_body)
        except json.JSONDecodeError as e:
            return False, {}, [{"field": "body", "message": f"Invalid JSON: {str(e)}"}]
    elif isinstance(raw_body, dict):
        packet = raw_body
    else:
        return False, {}, [{"field": "body", "message": f"Expected JSON object, got {type(raw_body).__name__}"}]

    if not isinstance(packet, dict):
        return False, {}, [{"field": "body", "message": "Top-level JSON must be an object"}]

    # --- Step 2: Validate metadata ---
    for field in REQUIRED_META:
        if field not in packet:
            errors.append({"field": field, "message": f"Missing required metadata field: {field}"})

    # Validate timestamp
    timestamp = packet.get("timestamp")
    if timestamp:
        try:
            # Accept ISO8601 with or without timezone
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # Must not be in the future (allow 5 min clock skew)
            now = datetime.now(timezone.utc)
            if parsed > now.replace(tzinfo=None) if parsed.tzinfo is None else now:
                # Compare naive with naive
                if parsed.tzinfo is None:
                    now_naive = datetime.now()
                    if parsed > now_naive:
                        errors.append({"field": "timestamp", "message": "Timestamp is in the future"})
        except (ValueError, TypeError):
            errors.append({"field": "timestamp", "message": f"Invalid ISO8601 timestamp: {timestamp}"})
    else:
        errors.append({"field": "timestamp", "message": "Missing timestamp"})

    # Validate device_id
    device_id = packet.get("device_id", "")
    if not device_id or not isinstance(device_id, str):
        errors.append({"field": "device_id", "message": "Missing or invalid device_id"})

    # --- Step 3: Validate sensor_data ---
    sensor_data = packet.get("sensor_data")
    if not sensor_data or not isinstance(sensor_data, dict):
        errors.append({"field": "sensor_data", "message": "Missing or invalid sensor_data object"})
        return False, packet, errors

    # Check required sensor fields
    for field in REQUIRED_FIELDS:
        if field not in sensor_data:
            errors.append({"field": f"sensor_data.{field}", "message": f"Missing required sensor field: {field}"})

    # Check value types and absolute limits
    for field, (low, high) in ABSOLUTE_LIMITS.items():
        value = sensor_data.get(field)
        if value is None:
            continue  # missing field already reported above

        if not isinstance(value, (int, float)):
            errors.append({"field": f"sensor_data.{field}", "message": f"Expected number, got {type(value).__name__}: {value}"})
            continue

        if isinstance(value, bool):
            errors.append({"field": f"sensor_data.{field}", "message": f"Expected number, got boolean: {value}"})
            continue

        if value < low or value > high:
            errors.append({
                "field": f"sensor_data.{field}",
                "message": f"Value {value} outside absolute limits [{low}, {high}]"
            })

    # --- Step 4: Jump detection (if previous packet available) ---
    if previous_packet and not errors:
        prev_sensors = previous_packet.get("sensor_data", {})
        for field, max_jump in MAX_JUMP.items():
            curr_val = sensor_data.get(field)
            prev_val = prev_sensors.get(field)
            if curr_val is not None and prev_val is not None:
                delta = abs(curr_val - prev_val)
                if delta > max_jump:
                    errors.append({
                        "field": f"sensor_data.{field}",
                        "message": f"Suspicious jump: {prev_val} → {curr_val} (Δ={delta:.1f}, max={max_jump})",
                        "severity": "warning",  # warning, not rejection
                    })

    # --- Step 5: Compute leaf_temp_delta if not provided ---
    if "leaf_temp_delta" not in sensor_data and "air_temp" in sensor_data and "leaf_temp" in sensor_data:
        air = sensor_data.get("air_temp")
        leaf = sensor_data.get("leaf_temp")
        if air is not None and leaf is not None:
            sensor_data["leaf_temp_delta"] = round(leaf - air, 2)

    # --- Step 6: Add missing extended fields with defaults ---
    defaults = {
        "air_temp_rate": 0.0,
        "humidity_rate": 0.0,
        "leaf_temp_rate": 0.0,
        "co2": 420.0,
        "wind_speed": 0.0,
        "cloud_cover": 0.0,
        "rain_rate": 0.0,
        "vpd": None,
        "transpiration": 0.0,
        "photosynthesis": 0.0,
        "growth": 0.0,
        "stress": 0.0,
    }
    for k, v in defaults.items():
        if k not in sensor_data:
            sensor_data[k] = v

    # Separate hard errors from warnings
    hard_errors = [e for e in errors if e.get("severity") != "warning"]
    is_valid = len(hard_errors) == 0

    return is_valid, packet, errors