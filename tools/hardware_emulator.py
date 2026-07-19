#!/usr/bin/env python3
"""
Aletheia Hardware Emulator — Developer Test Utility
====================================================
Simulates an ESP32-S3 sending sensor packets to the Aletheia backend
through the REAL /hardware/update endpoint.

This is NOT a simulator replacement. It sends properly-formed packets
that exercise the full hardware pipeline:
  Validate → Calibrate → Store → Temporal AI → Biology → Decision → Confidence → OpenRouter

Usage:
  # Single packet
  python tools/hardware_emulator.py --url http://127.0.0.1:5000 --key dev-key

  # Continuous stream (1 packet every 5 seconds)
  python tools/hardware_emulator.py --url http://127.0.0.1:5000 --key dev-key --stream

  # With custom plant
  python tools/hardware_emulator.py --url http://127.0.0.1:5000 --key dev-key --plant mango --stage fruiting

  # Production (HTTPS required)
  python tools/hardware_emulator.py --url https://your-space.hf.space --key YOUR_SECRET_KEY

Requirements:
  pip install requests
"""

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ── Canonical Device Identity ──────────────────────────────────────────
CANONICAL_DEVICE_ID = "ALETHEIA-ESP32-001"
CANONICAL_FIRMWARE = "1.0.0"

# ── Realistic sensor ranges for a greenhouse ───────────────────────────
SENSOR_RANGES = {
    "air_temp": (22.0, 38.0),       # °C — typical greenhouse range
    "humidity": (40.0, 85.0),        # % RH
    "soil_temp": (18.0, 32.0),       # °C
    "soil_moisture": (30.0, 75.0),   # %
    "light": (5000, 85000),          # lux — dawn to full sun
    "leaf_temp": (20.0, 42.0),       # °C — leaf surface temp
}

# ── Sensor drift simulation ────────────────────────────────────────────
class SensorState:
    """Maintains drifting sensor values for realistic continuous streams."""
    def __init__(self):
        self.values = {
            "air_temp": 28.0,
            "humidity": 60.0,
            "soil_temp": 24.0,
            "soil_moisture": 55.0,
            "light": 45000,
            "leaf_temp": 31.0,
        }

    def step(self):
        """Apply small random drift within realistic bounds."""
        for sensor, (low, high) in SENSOR_RANGES.items():
            drift = random.gauss(0, 0.3)  # mean 0, std 0.3
            self.values[sensor] += drift
            # Clamp to realistic range
            self.values[sensor] = max(low, min(high, self.values[sensor]))
            self.values[sensor] = round(self.values[sensor], 2)
        return dict(self.values)


def build_packet(sensor_data: dict, plant: str, stage: str, mode: str,
                 device_id: str = CANONICAL_DEVICE_ID,
                 firmware: str = CANONICAL_FIRMWARE) -> dict:
    """Build a canonical hardware packet matching the ESP32 schema."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": device_id,
        "plant": plant,
        "stage": stage,
        "mode": mode,
        "firmware_version": firmware,
        "sensor_data": sensor_data,
    }


def send_packet(url: str, api_key: str, packet: dict, verbose: bool = True) -> dict | None:
    """POST a packet to /hardware/update and return the response."""
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoint = url.rstrip("/") + "/hardware/update"

    try:
        resp = requests.post(endpoint, json=packet, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if verbose:
                analysis = data.get("analysis", {})
                confidence = analysis.get("confidence", {})
                stress = analysis.get("stress_analysis", {})
                temporal = analysis.get("temporal_prediction", {})
                print(f"  ✓ Accepted | "
                      f"Confidence: {confidence.get('overall', '?')}% | "
                      f"Stress: {stress.get('prediction', '?')} | "
                      f"Temporal: {temporal.get('future_state', {}).get('future_prediction', '?')} | "
                      f"Warnings: {len(data.get('validation_warnings', []))}")
            return data
        elif resp.status_code == 401:
            print(f"  ✗ UNAUTHORIZED — check your HARDWARE_API_KEY")
            return None
        elif resp.status_code == 400:
            data = resp.json()
            print(f"  ✗ Validation failed: {data.get('message', 'unknown')}")
            if verbose:
                for err in data.get("validation_errors", []):
                    print(f"    - {err.get('field', '?')}: {err.get('message', '?')}")
            return None
        else:
            print(f"  ✗ HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection refused — is the backend running at {url}?")
        return None
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Aletheia Hardware Emulator — Test ESP32 packet flow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local dev (no auth)
  python tools/hardware_emulator.py --url http://127.0.0.1:5000

  # Local dev with auth key
  python tools/hardware_emulator.py --url http://127.0.0.1:5000 --key dev-key-123

  # Production HF Space
  python tools/hardware_emulator.py --url https://alethelia.hf.space --key $HARDWARE_API_KEY

  # Continuous stream for 60 seconds
  python tools/hardware_emulator.py --url http://127.0.0.1:5000 --stream --duration 60
        """,
    )
    parser.add_argument("--url", default="http://127.0.0.1:5000",
                        help="Backend base URL (default: http://127.0.0.1:5000)")
    parser.add_argument("--key", default=os.environ.get("HARDWARE_API_KEY", ""),
                        help="HARDWARE_API_KEY for auth (default: from env HARDWARE_API_KEY)")
    parser.add_argument("--plant", default="tomato",
                        help="Plant name (default: tomato)")
    parser.add_argument("--stage", default="flowering",
                        help="Growth stage (default: flowering)")
    parser.add_argument("--mode", default="day",
                        help="Day/night mode (default: day)")
    parser.add_argument("--device-id", default=CANONICAL_DEVICE_ID,
                        help=f"Device ID (default: {CANONICAL_DEVICE_ID})")
    parser.add_argument("--stream", action="store_true",
                        help="Send continuous stream of packets")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between packets in stream mode (default: 5.0)")
    parser.add_argument("--duration", type=float, default=0,
                        help="Stream duration in seconds (0 = indefinite)")
    parser.add_argument("--count", type=int, default=0,
                        help="Number of packets to send in stream mode (0 = indefinite)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-packet output")
    args = parser.parse_args()

    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║       Aletheia Hardware Emulator — Dev Test Tool         ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║  Backend:  {args.url:<44}║")
    print(f"║  Auth:     {'Enabled' if args.key else 'Disabled (no key set)':<44}║")
    print(f"║  Device:   {args.device_id:<44}║")
    print(f"║  Plant:    {args.plant} / {args.stage} / {args.mode:<30}║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    print()

    if not args.key:
        print("⚠  WARNING: No HARDWARE_API_KEY set. If the backend requires auth,")
        print("   packets will be rejected with 401 Unauthorized.")
        print("   Set --key or export HARDWARE_API_KEY=your-key")
        print()

    sensor_state = SensorState()
    packets_sent = 0
    packets_ok = 0
    start_time = time.time()

    if args.stream:
        print(f"▶ Starting continuous stream (interval: {args.interval}s)...")
        print(f"  Press Ctrl+C to stop.\n")

        try:
            while True:
                # Check duration limit
                if args.duration > 0 and (time.time() - start_time) >= args.duration:
                    break
                # Check count limit
                if args.count > 0 and packets_sent >= args.count:
                    break

                sensor_data = sensor_state.step()
                packet = build_packet(sensor_data, args.plant, args.stage, args.mode,
                                      device_id=args.device_id)

                if not args.quiet:
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] Packet {packets_sent + 1}: ", end="")

                result = send_packet(args.url, args.key, packet, verbose=not args.quiet)
                packets_sent += 1
                if result:
                    packets_ok += 1

                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n⏹ Stream stopped by user.")

    else:
        # Single packet mode
        sensor_data = sensor_state.step()
        packet = build_packet(sensor_data, args.plant, args.stage, args.mode,
                              device_id=args.device_id)

        print("Sending single test packet...")
        print(f"  Sensor data: {json.dumps(sensor_data, indent=2)}")
        print()

        result = send_packet(args.url, args.key, packet, verbose=True)
        packets_sent = 1
        if result:
            packets_ok = 1
            print(f"\n  Full response analysis:")
            analysis = result.get("analysis", {})
            print(f"    Confidence: {json.dumps(analysis.get('confidence', {}), indent=4)}")
            print(f"    Stress:     {json.dumps(analysis.get('stress_analysis', {}), indent=4)}")
            print(f"    Temporal:   {json.dumps(analysis.get('temporal_prediction', {}), indent=4)}")
            print(f"    Biology:    Health Score = {analysis.get('biology_analysis', {}).get('health_score', '?')}")

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'─' * 60}")
    print(f"Summary: {packets_ok}/{packets_sent} packets accepted ({elapsed:.1f}s)")
    if packets_sent > 0:
        print(f"Success rate: {packets_ok/packets_sent*100:.1f}%")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()