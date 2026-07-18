# Aletheia API Documentation

## Base URL

- **Development**: `http://127.0.0.1:5000`
- **Production**: Set via `NEXT_PUBLIC_API_URL` (e.g., Hugging Face Space URL)

## Response Format

All endpoints return JSON.

### Success Response
```json
{
    "service": "Aletheia Backend",
    "status": "running",
    ...
}
```

### Error Response
```json
{
    "error": "Description of what went wrong",
    "details": "Optional additional context"
}
```

HTTP status codes: `200` (success), `400` (bad request), `500` (server error).

---

## Core Endpoints

### `GET /` — Health Check
**Response:**
```json
{
    "service": "Aletheia Backend",
    "status": "running",
    "endpoints": {
        "health": "/",
        "search": "/search/<query>",
        "analyze": "POST /analyze"
    }
}
```

### `GET /search/<query>` — Fuzzy Plant Search
**Parameters:** `query` (URL path) — plant name to search

**Response:**
```json
{
    "query": "tomato",
    "results": ["tomato", "tomatillo", ...]
}
```

### `POST /analyze` — Unified AI Analysis
**Request Body:**
```json
{
    "plant": "Tomato",
    "stage": "Flowering",
    "phase": "day",
    "sensor_data": {
        "air_temp": 28.5,
        "humidity": 62.0,
        "soil_temp": 24.3,
        "soil_moisture": 55.0,
        "light": 18500,
        "leaf_temp": 30.1
    }
}
```

**Response:** Complete analysis with biology, stress, temporal predictions, recommendations, AI reasoning, confidence, causal chain, and decision input.

### `GET /predict/<plant>/<stage>/<phase>` — Legacy Prediction
**Parameters:** `plant`, `stage`, `phase` (URL path)

Redirects to `/analyze` with demo sensor data.

---

## Simulator Endpoints

### `GET /simulator/state` — Current Simulator State
**Response:**
```json
{
    "sim_time": "08:00",
    "day_phase": "day",
    "scenario": "normal_day",
    "running": true,
    "speed": 1.0,
    "sim_minute": 480,
    "weather": {
        "air_temp": 28.5,
        "humidity": 62.0,
        "solar_radiation": 800.0,
        "wind_speed": 2.5
    },
    "soil": {
        "soil_temp": 24.3,
        "soil_moisture": 55.0
    },
    "plant": {
        "leaf_temp": 30.1,
        "leaf_temp_delta": 1.6,
        "transpiration": 0.0042,
        "photosynthesis": 0.85,
        "vpd": 1.2
    }
}
```

### `POST /simulator/start` — Start Simulation
No request body required.

### `POST /simulator/pause` — Pause Simulation
No request body required.

### `POST /simulator/reset` — Reset Simulation
No request body required.

### `POST /simulator/step` — Manual Step
No request body required. Advances simulation by one step.

### `POST /simulator/scenario` — Set Scenario
**Request Body:**
```json
{
    "scenario": "heat_stress"
}
```

Available scenarios: `normal_day`, `heat_stress`, `cold_stress`, `drought`, `high_humidity`, `low_light`, `sunrise_transition`, `sunset_transition`, `cloud_burst`, `recovery`

### `POST /simulator/speed` — Set Simulation Speed
**Request Body:**
```json
{
    "speed": 10.0
}
```

Multiplier: `0.5`, `1.0` (real-time), `10.0`, `60.0` (1h/s), `120.0`

### `GET /simulator/history` — Simulation History
**Query Parameters:** `n` (optional) — number of steps to return

**Response:** Array of historical simulation states with sensor data.

### `POST /simulator/analyze` — Analyze Current Sim State
**Request Body:**
```json
{
    "plant": "Tomato",
    "stage": "Flowering",
    "phase": "day"
}
```

**Response:** Full pipeline analysis of current simulator state, including trajectory for temporal visualization.

---

## Temporal AI Endpoints

### `POST /simulator/temporal/verify` — Verify Predictions
**Request Body:**
```json
{
    "sim_minute": 540,
    "n_steps": 10
}
```

**Response:** Comparison of predicted vs actual values for each sensor variable.

### `GET /simulator/temporal/replay` — Replay Historical State
**Query Parameters:**
- `minute` (required) — simulation minute to replay
- `n` (optional, default: 10) — context steps before/after

**Response:**
```json
{
    "target_minute": 540,
    "state": { ... },
    "context_before": [ ... ],
    "context_after": [ ... ],
    "analysis": { ... }
}
```

### `GET /simulator/temporal/accuracy` — Prediction Accuracy
**Response:**
```json
{
    "rolling_accuracy": [
        {"sim_minute": 540, "accuracy": 0.85, ...}
    ],
    "overall_accuracy": 0.82,
    "verification_details": [ ... ]
}
```

### `GET /simulator/temporal/snapshots` — Historical Snapshots
**Response:** Array of all stored snapshots with sim_minute, timestamp, and analysis summary.

### `GET /simulator/temporal/compare` — Compare Prediction vs Actual
**Query Parameters:**
- `snap_minute` (required) — snapshot to compare from
- `cmp_minute` (required) — minute to compare against

**Response:**
```json
{
    "snapshot_minute": 540,
    "comparison_minute": 550,
    "comparison": {
        "prediction_correct": true,
        "variables": [
            {
                "name": "air_temp",
                "predicted": 29.1,
                "actual": 29.3,
                "error": 0.2,
                "error_pct": 0.68,
                "within_tolerance": true
            }
        ]
    }
}
```

---

## Hardware Endpoints

### `POST /hardware/update` — Submit Sensor Data
**Request Body (Canonical Schema):**
```json
{
    "timestamp": "2026-07-17T13:00:00Z",
    "device_id": "ESP32-001",
    "plant": "Tomato",
    "stage": "Flowering",
    "mode": "Day",
    "sensor_data": {
        "air_temp": 28.5,
        "humidity": 62.0,
        "soil_temp": 24.3,
        "soil_moisture": 55.0,
        "light": 18500,
        "leaf_temp": 30.1
    }
}
```

**Validation Rules:**
- `humidity`: 0–100% (rejected if >100%)
- `light`: ≥0 lux (rejected if negative)
- `air_temp`: -20 to 70°C
- `soil_temp`: -10 to 60°C
- `leaf_temp`: -20 to 75°C
- `timestamp`: ISO 8601 format required
- All 6 sensor fields required
- Jump detection: warns but does not reject

**Response:** Full pipeline analysis with `hardware_meta` containing device_id, calibration info, and validation warnings.

### `GET /hardware/status` — Device Connection Status
**Response:**
```json
{
    "device_id": "ESP32-001",
    "online": true,
    "last_packet_time": "2026-07-17T13:00:00Z",
    "packet_age_seconds": 5.2,
    "sampling_rate_hz": 0.33,
    "firmware_version": "1.0.0",
    "packet_count": 142
}
```

Device is considered "online" if last packet was within 60 seconds.

### `GET /hardware/history` — Hardware Packet History
**Query Parameters:** `n` (optional) — number of packets to return

**Response:** Array of stored hardware packets with analysis snapshots and sensor_stream for Temporal AI.

### `GET /hardware/calibration` — Calibration Status
**Query Parameters:** `device_id` (optional, default: "ESP32-001")

**Response:**
```json
{
    "device_id": "ESP32-001",
    "sensors": {
        "air_temp": {
            "offset": 0.5,
            "scale_factor": 1.02,
            "calibrated_at": "2026-07-17T12:00:00Z",
            "status": "calibrated"
        },
        "humidity": {
            "offset": 0.0,
            "scale_factor": 1.0,
            "status": "none"
        }
    }
}
```

### `POST /hardware/calibrate` — Set Calibration
**Request Body:**
```json
{
    "device_id": "ESP32-001",
    "sensor": "air_temp",
    "offset": 0.5,
    "scale_factor": 1.02
}
```

Calibration formula: `calibrated_value = (raw_value × scale_factor) + offset`

### `POST /hardware/calibrate/reset` — Reset Calibration
**Request Body:**
```json
{
    "device_id": "ESP32-001",
    "sensor": "air_temp"
}
```

Resets to identity: offset=0, scale_factor=1, status="none".

---

## Session Endpoints

### `POST /session/save` — Export Session
**Request Body:**
```json
{
    "source": "simulator",
    "format": "json"
}
```

- `source`: `"simulator"` or `"hardware"`
- `format`: `"json"`, `"report"`, or `"both"`

**Response:**
```json
{
    "json_data": { ... },
    "report": "Human-readable report text...",
    "source": "simulator",
    "timestamp": "2026-07-17T13:00:00Z"
}
```

### `GET /session/export` — Quick Export
Same as `POST /session/save` with `source=simulator, format=both`.

---

## Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request — invalid input, validation failure |
| 404 | Not found — endpoint or resource doesn't exist |
| 500 | Internal server error — pipeline or dependency failure |

All error responses include an `error` field with a human-readable description.