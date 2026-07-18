"""
Hardware Integration Layer for Aletheia

ESP32 DevKit V1 with sensors:
  - SHT31  (Air Temperature, Humidity)
  - BH1750 (Light Intensity)
  - Capacitive Soil Moisture Sensor v2
  - DS18B20 Waterproof (Soil Temperature)
  - MLX90614 (Leaf Temperature)

This package extends the existing Aletheia backend without modifying
any AI models, pipelines, or existing logic.
"""

from backend.hardware.validator import validate_hardware_packet
from backend.hardware.store import HardwareStore
from backend.hardware.calibration import CalibrationManager

__all__ = [
    "validate_hardware_packet",
    "HardwareStore",
    "CalibrationManager",
]