"""
Sensor Calibration Manager

Stores calibration parameters for each sensor on each device.
Calibration is applied BEFORE validation:
  calibrated_value = (raw_value * scale_factor) + offset

Supports:
  - Per-device, per-sensor calibration
  - Offset and scale factor
  - Calibration date tracking
  - Calibration status (active, expired, none)
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), "calibration.json")

# Sensors that support calibration
CALIBRATABLE_SENSORS = [
    "air_temp",
    "humidity",
    "soil_temp",
    "soil_moisture",
    "light",
    "leaf_temp",
]

# Default calibration (identity: no adjustment)
DEFAULT_CALIBRATION = {
    "offset": 0.0,
    "scale_factor": 1.0,
    "calibrated_at": None,
    "status": "none",
}


class CalibrationManager:
    """
    Manages per-device, per-sensor calibration profiles.
    """

    def __init__(self):
        self._profiles: Dict[str, Dict[str, Dict]] = {}
        self._load()

    def _load(self):
        if os.path.exists(CALIBRATION_FILE):
            try:
                with open(CALIBRATION_FILE, "r") as f:
                    self._profiles = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._profiles = {}

    def _save(self):
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(self._profiles, f, indent=2)

    def get_calibration(self, device_id: str, sensor: str) -> Dict:
        """
        Get calibration for a specific sensor on a device.
        Returns default (identity) if not calibrated.
        """
        device_profiles = self._profiles.get(device_id, {})
        return device_profiles.get(sensor, dict(DEFAULT_CALIBRATION))

    def set_calibration(
        self,
        device_id: str,
        sensor: str,
        offset: float = 0.0,
        scale_factor: float = 1.0,
    ) -> Dict:
        """
        Set calibration parameters for a sensor.

        Args:
            device_id: ESP32 device identifier
            sensor: Sensor name (air_temp, humidity, etc.)
            offset: Additive offset (raw + offset)
            scale_factor: Multiplicative factor (raw * scale_factor)

        Returns:
            The stored calibration profile
        """
        if sensor not in CALIBRATABLE_SENSORS:
            raise ValueError(f"Sensor '{sensor}' is not calibratable. Options: {CALIBRATABLE_SENSORS}")

        if device_id not in self._profiles:
            self._profiles[device_id] = {}

        self._profiles[device_id][sensor] = {
            "offset": offset,
            "scale_factor": scale_factor,
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        self._save()
        return self._profiles[device_id][sensor]

    def reset_calibration(self, device_id: str, sensor: Optional[str] = None):
        """
        Reset calibration. If sensor is None, reset all sensors for the device.
        """
        if sensor:
            if device_id in self._profiles and sensor in self._profiles[device_id]:
                del self._profiles[device_id][sensor]
        else:
            if device_id in self._profiles:
                del self._profiles[device_id]
        self._save()

    def apply_calibration(self, device_id: str, sensor_data: Dict) -> Dict:
        """
        Apply stored calibration to raw sensor data.
        calibrated = (raw * scale_factor) + offset

        Args:
            device_id: ESP32 device identifier
            sensor_data: Raw sensor readings dict

        Returns:
            Calibrated sensor_data dict
        """
        calibrated = dict(sensor_data)
        for sensor in CALIBRATABLE_SENSORS:
            if sensor in calibrated and calibrated[sensor] is not None:
                cal = self.get_calibration(device_id, sensor)
                raw = calibrated[sensor]
                calibrated[sensor] = round((raw * cal["scale_factor"]) + cal["offset"], 2)
        return calibrated

    def get_all_calibrations(self, device_id: str) -> Dict:
        """
        Get calibration status for all sensors on a device.
        """
        result = {}
        for sensor in CALIBRATABLE_SENSORS:
            cal = self.get_calibration(device_id, sensor)
            result[sensor] = cal
        return result

    def list_devices(self) -> list:
        """List all devices that have calibration profiles."""
        return list(self._profiles.keys())