# ESP32 Hardware Integration Guide

## Overview

Aletheia supports real ESP32-based sensor hardware as a data source alongside the built-in simulator. The hardware layer feeds sensor readings into the **same AI pipeline** — no code duplication, no separate analysis path.

## Supported Hardware

| Sensor | Model | Measures | Unit |
|--------|-------|----------|------|
| Air Temperature & Humidity | SHT31 | `air_temp`, `humidity` | °C, % |
| Light Intensity | BH1750 | `light` | lux |
| Soil Moisture | Capacitive Soil Moisture Sensor v2 | `soil_moisture` | % |
| Soil Temperature | DS18B20 Waterproof | `soil_temp` | °C |
| Leaf Temperature | MLX90614 IR | `leaf_temp` | °C |

**Microcontroller**: ESP32 DevKit V1 (Wi-Fi enabled)

## Canonical JSON Payload

The ESP32 MUST send data in this exact JSON format to `POST /hardware/update`:

```json
{
    "timestamp": "2026-07-17T14:30:00Z",
    "device_id": "ESP32-001",
    "plant": "Tomato",
    "stage": "Flowering",
    "mode": "Day",
    "sensor_data": {
        "air_temp": 31.4,
        "humidity": 58.2,
        "soil_temp": 28.1,
        "soil_moisture": 46.8,
        "light": 18200,
        "leaf_temp": 33.5,
        "leaf_temp_delta": 2.1
    }
}
```

### Field Specifications

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `timestamp` | string (ISO 8601) | Yes | Valid ISO 8601 datetime |
| `device_id` | string | Yes | Non-empty identifier |
| `plant` | string | Yes | Plant name (e.g., "Tomato", "Mango", "Potato") |
| `stage` | string | Yes | Growth stage: Germination, Seedling, Vegetative, Flowering, Fruiting, Harvest |
| `mode` | string | Yes | "Day" or "Night" |
| `sensor_data.air_temp` | float | Yes | -20 to 60 °C |
| `sensor_data.humidity` | float | Yes | 0 to 100 % |
| `sensor_data.soil_temp` | float | Yes | -10 to 50 °C |
| `sensor_data.soil_moisture` | float | Yes | 0 to 100 % |
| `sensor_data.light` | float | Yes | 0 to 200000 lux |
| `sensor_data.leaf_temp` | float | Yes | -10 to 55 °C |
| `sensor_data.leaf_temp_delta` | float | No | Auto-computed if missing: `leaf_temp - air_temp` |

### Validation Rules

The hardware validator (`backend/hardware/validator.py`) enforces:

1. **JSON validity** — malformed JSON returns `400 Bad Request`
2. **Required fields** — missing `timestamp`, `device_id`, or any `sensor_data` field returns `400`
3. **Physical limits** — humidity > 100%, negative lux, impossible temperatures return `400`
4. **Jump detection** — sensor value change > threshold from previous reading generates a **warning** (not rejection)
5. **Auto-completion** — `leaf_temp_delta` is computed if not provided

## ESP32 Arduino Code Template

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_SHT31.h>
#include <BH1750.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_MLX90614.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Aletheia backend URL
const char* aletheiaUrl = "https://YOUR_HUGGINGFACE_SPACE_URL/hardware/update";

// Device identity
const char* deviceId = "ESP32-001";
const char* plantName = "Tomato";
const char* growthStage = "Flowering";

// Sensor pins
#define SOIL_MOISTURE_PIN 34
#define ONE_WIRE_BUS 4

// Sensor objects
Adafruit_SHT31 sht31 = Adafruit_SHT31();
BH1750 lightMeter;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi connected");

    Wire.begin();
    sht31.begin(0x44);
    lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
    ds18b20.begin();
    mlx.begin();
}

void loop() {
    // Read SHT31 (air temperature + humidity)
    float airTemp = sht31.readTemperature();
    float humidity = sht31.readHumidity();

    // Read BH1750 (light)
    float light = lightMeter.readLightLevel();

    // Read DS18B20 (soil temperature)
    ds18b20.requestTemperatures();
    float soilTemp = ds18b20.getTempCByIndex(0);

    // Read capacitive soil moisture (0-100%)
    int rawMoisture = analogRead(SOIL_MOISTURE_PIN);
    float soilMoisture = map(rawMoisture, 0, 4095, 100, 0);
    soilMoisture = constrain(soilMoisture, 0, 100);

    // Read MLX90614 (leaf temperature)
    float leafTemp = mlx.readObjectTempC();
    float leafTempDelta = leafTemp - airTemp;

    // Determine day/night mode
    String mode = (light > 1000) ? "Day" : "Night";

    // Build JSON payload
    StaticJsonDocument<512> doc;
    doc["timestamp"] = getISO8601Timestamp();
    doc["device_id"] = deviceId;
    doc["plant"] = plantName;
    doc["stage"] = growthStage;
    doc["mode"] = mode;

    JsonObject sensorData = doc.createNestedObject("sensor_data");
    sensorData["air_temp"] = round2(airTemp);
    sensorData["humidity"] = round2(humidity);
    sensorData["soil_temp"] = round2(soilTemp);
    sensorData["soil_moisture"] = round2(soilMoisture);
    sensorData["light"] = round2(light);
    sensorData["leaf_temp"] = round2(leafTemp);
    sensorData["leaf_temp_delta"] = round2(leafTempDelta);

    // Send to Aletheia
    String jsonString;
    serializeJson(doc, jsonString);

    HTTPClient http;
    http.begin(aletheiaUrl);
    http.addHeader("Content-Type", "application/json");

    int httpCode = http.POST(jsonString);
    if (httpCode == 200) {
        String response = http.getString();
        Serial.println("✓ Data sent successfully");
        // Parse AI response for recommendations
        StaticJsonDocument<1024> responseDoc;
        deserializeJson(responseDoc, response);
        const char* prediction = responseDoc["stress_analysis"]["prediction"];
        Serial.print("AI Prediction: ");
        Serial.println(prediction);
    } else {
        Serial.print("✗ HTTP Error: ");
        Serial.println(httpCode);
    }
    http.end();

    delay(300000); // Send every 5 minutes
}

float round2(float value) {
    return round(value * 100.0) / 100.0;
}

String getISO8601Timestamp() {
    // Configure NTP time sync in setup() for real timestamps
    // For demo: return a formatted string
    time_t now;
    time(&now);
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", gmtime(&now));
    return String(buf);
}
```

## API Endpoints for Hardware

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/hardware/update` | Send sensor packet → validate → calibrate → pipeline → AI response |
| `GET` | `/hardware/status` | Device connection status, last packet time, sampling rate |
| `GET` | `/hardware/history` | Retrieve stored hardware packets |
| `GET` | `/hardware/calibration` | Get calibration profiles for all sensors |
| `POST` | `/hardware/calibrate` | Set calibration (offset + scale factor) for a sensor |
| `POST` | `/hardware/calibrate/reset` | Reset calibration for a sensor |

### POST /hardware/update Response

```json
{
    "status": "ok",
    "device_id": "ESP32-001",
    "packet_id": 42,
    "analysis": {
        "stress_analysis": {
            "prediction": "Heat Stress",
            "severity": 0.72,
            "risk_state": "Warning",
            "reasons": ["Leaf temperature 5.2°C above optimal range"]
        },
        "biology_analysis": {
            "health_score": 0.65,
            "warnings": ["Transpiration rate elevated"],
            "analysis": { ... }
        },
        "temporal_prediction": {
            "future_state": {
                "future_prediction": "Heat Stress",
                "future_confidence": 0.68
            }
        },
        "recommendations": [
            "Increase ventilation to reduce leaf temperature",
            "Consider shade cloth during peak sunlight hours"
        ],
        "confidence": {
            "overall": 0.71,
            "sensor_confidence": 0.95,
            "ai_confidence": 0.72,
            "temporal_confidence": 0.68,
            "biology_health_score": 0.65
        },
        "ai_reasoning": {
            "explanation": "Leaf temperature exceeds optimal range...",
            "diagnosis": "Early-stage heat stress detected",
            "recommendations": [ ... ]
        }
    }
}
```

## Calibration

Each sensor can be calibrated per-device with an offset and scale factor:

```
calibrated_value = (raw_value × scale_factor) + offset
```

### Set Calibration

```bash
curl -X POST http://127.0.0.1:5000/hardware/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32-001",
    "sensor": "air_temp",
    "offset": -0.5,
    "scale_factor": 1.02
  }'
```

### Reset Calibration

```bash
curl -X POST http://127.0.0.1:5000/hardware/calibrate/reset \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32-001",
    "sensor": "air_temp"
  }'
```

## Modes of Operation

The frontend supports three modes:

| Mode | Description | Button |
|------|-------------|--------|
| **Simulator** | Built-in physics-based greenhouse simulation | 🖥 Sim Mode |
| **Live Hardware** | Real ESP32 sensor data stream | 🔌 HW Mode |
| **Replay** | Navigate historical data from either source | Temporal Replay slider |

Switching to Hardware Mode:
1. Click the 🔌 HW Mode button in the dashboard
2. The Device Status Panel appears showing connection status
3. Live sensor readings update every 3 seconds
4. All graphs, stress analysis, and AI reasoning update automatically

## Failover Behavior

If the hardware disconnects:
- A warning banner appears: "⚠ Hardware disconnected"
- Historical data remains visible
- One-click switch back to Simulator mode
- The backend never crashes — it gracefully handles missing hardware data

## Data Storage

Every hardware packet is stored in `backend/hardware/hardware_history.json` with:
- Raw sensor values
- Calibrated sensor values
- Full AI pipeline analysis snapshot
- Timestamp and device metadata

Maximum stored entries: 1440 (24 hours at 1-minute intervals). Older entries are automatically pruned.