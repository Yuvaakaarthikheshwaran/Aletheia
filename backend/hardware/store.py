"""
Hardware Data Store

Persists every validated ESP32 hardware packet along with its AI analysis.
Supports replay exactly like simulator replay — same data structure,
same endpoints, same pipeline consumption.

Storage: JSON file (hardware_history.json) for persistence across restarts.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

STORE_FILE = os.path.join(os.path.dirname(__file__), "hardware_history.json")
MAX_HISTORY = 1440  # 24h of minute-by-minute data


class HardwareStore:
    """
    Stores hardware packets with their AI analysis snapshots.
    Mirrors GreenhouseSimulator.history structure for replay compatibility.
    """

    def __init__(self):
        self.history: List[Dict] = []
        self._load()

    def _load(self):
        """Load persisted history from disk."""
        if os.path.exists(STORE_FILE):
            try:
                with open(STORE_FILE, "r") as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.history = []

    def _save(self):
        """Persist history to disk."""
        with open(STORE_FILE, "w") as f:
            json.dump(self.history[-MAX_HISTORY:], f, indent=2)

    def append(self, packet: Dict, analysis: Optional[Dict] = None) -> Dict:
        """
        Store a hardware packet with optional AI analysis snapshot.

        Args:
            packet: The validated hardware packet (with sensor_data, device_id, etc.)
            analysis: AI pipeline output from run_unified_pipeline()

        Returns:
            The stored entry (packet + analysis snapshot)
        """
        entry = {
            "timestamp": packet.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "device_id": packet.get("device_id", "unknown"),
            "plant": packet.get("plant", ""),
            "stage": packet.get("stage", ""),
            "mode": packet.get("mode", "day"),
            "sensor_data": packet.get("sensor_data", {}),
            "source": "hardware",  # distinguishes from simulator entries
        }

        if analysis:
            entry["analysis_snapshot"] = {
                "plant_name": analysis.get("plant"),
                "growth_stage": analysis.get("stage"),
                "temporal_prediction": analysis.get("temporal_prediction"),
                "stress_analysis": analysis.get("stress_analysis"),
                "biology_analysis": analysis.get("biology_analysis"),
                "recommendations": analysis.get("recommendations"),
                "confidence": analysis.get("confidence"),
                "ai_reasoning": analysis.get("ai_reasoning"),
                "decision_input": analysis.get("decision_input"),
            }

        self.history.append(entry)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        self._save()
        return entry

    def get_history(self, n_steps: int = None) -> List[Dict]:
        """Return the last n_steps from history (all if None)."""
        if n_steps is None:
            return list(self.history)
        return self.history[-n_steps:]

    def get_sensor_stream(self, n_steps: int = None) -> List[Dict]:
        """Return just sensor_data from history for temporal AI consumption."""
        history = self.get_history(n_steps)
        return [h["sensor_data"] for h in history]

    def get_last_packet(self) -> Optional[Dict]:
        """Return the most recent packet (for jump detection)."""
        if self.history:
            return self.history[-1]
        return None

    def get_device_status(self) -> Dict:
        """Return current device connection status."""
        last = self.get_last_packet()
        if not last:
            return {
                "device_id": None,
                "online": False,
                "last_packet_time": None,
                "packet_age_seconds": None,
                "total_packets": 0,
            }

        last_time_str = last.get("timestamp", "")
        try:
            last_time = datetime.fromisoformat(last_time_str.replace("Z", "+00:00"))
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - last_time).total_seconds()
        except (ValueError, TypeError):
            age = None

        # Device is "online" if last packet within 60 seconds
        online = age is not None and age < 60

        # Compute sampling rate from recent packets
        recent = self.history[-20:]
        sampling_rate = None
        if len(recent) >= 2:
            try:
                t0 = datetime.fromisoformat(recent[0]["timestamp"].replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(recent[-1]["timestamp"].replace("Z", "+00:00"))
                if t0.tzinfo is None:
                    t0 = t0.replace(tzinfo=timezone.utc)
                if t1.tzinfo is None:
                    t1 = t1.replace(tzinfo=timezone.utc)
                span = (t1 - t0).total_seconds()
                if span > 0:
                    sampling_rate = round((len(recent) - 1) / span, 2)
            except (ValueError, TypeError):
                pass

        return {
            "device_id": last.get("device_id"),
            "online": online,
            "last_packet_time": last_time_str,
            "packet_age_seconds": round(age, 1) if age is not None else None,
            "total_packets": len(self.history),
            "sampling_rate_hz": sampling_rate,
            "firmware_version": last.get("firmware_version", "unknown"),
        }

    def clear(self):
        """Clear all stored history."""
        self.history = []
        if os.path.exists(STORE_FILE):
            os.remove(STORE_FILE)