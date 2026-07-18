---
title: Aletheia
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Aletheia — AI-Powered Digital Twin for Intelligent Agriculture

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Aletheia is a production-grade AI platform that combines **Random Forest anomaly detection**, **Temporal AI forecasting**, **Biology Engine simulation**, and **LLM-powered reasoning** to create a complete Digital Twin for greenhouse agriculture. It supports both simulated environments and real ESP32 hardware sensor integration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                       │
│  Digital Twin Dashboard • Temporal Graphs • Replay Mode     │
│  Hardware Device Panel • Calibration • Comparison Mode      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND (Flask + Gunicorn)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Unified Pipeline                         │   │
│  │  Plant Lookup → Tavily Search → Parser →             │   │
│  │  Temporal AI → Biology Engine → Decision Engine →    │   │
│  │  OpenRouter AI Reasoning → Unified JSON Response     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Simulator   │  │  Hardware    │  │  Session     │      │
│  │  (Digital    │  │  Integration │  │  Export      │      │
│  │   Twin)      │  │  (ESP32)     │  │  (JSON/Rpt)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     AI MODELS (joblib)                       │
│  Random Forest • Temporal AI v5.1 • Decision Engine         │
│  Sensor Guard • Anomaly Detector • Biology Engine           │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  EXTERNAL SERVICES                           │
│  Tavily (Web Search) • OpenRouter (LLM Reasoning)           │
│  Plant Cache (JSON) • AI Reasoning Cache (JSON)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-org/Aletheia.git
cd Aletheia

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example backend/.env
# Edit backend/.env with your API keys

# Run backend
cd backend
python app.py
# Backend runs at http://127.0.0.1:5000
```

### Frontend Setup

```bash
cd frontend
npm install

# Configure API URL
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://127.0.0.1:5000

npm run dev
# Frontend runs at http://localhost:3000
```

---

## Deployment

### Hugging Face Spaces (Backend)

1. Create a new Space at https://huggingface.co/spaces
2. Choose **Docker** SDK
3. Upload the repository
4. Set environment variables in Space Settings:
   - `TAVILY_API_KEY_1`
   - `TAVILY_API_KEY_BE`
   - `TAVILY_API_KEY`
   - `OPENROUTER_API_KEY`
5. The `Dockerfile` and `Procfile` are pre-configured

### Vercel (Frontend)

1. Connect your GitHub repository to Vercel
2. Set root directory to `frontend/`
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL` = your Hugging Face Space URL (e.g., `https://your-space.hf.space`)

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `TAVILY_API_KEY_1` | Yes | Primary Tavily search API key |
| `TAVILY_API_KEY_BE` | Yes | Backup Tavily search API key |
| `TAVILY_API_KEY` | Yes | Fallback Tavily search API key |
| `OPENROUTER_API_KEY` | Yes | OpenRouter LLM API key for synthetic data conversion |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated allowed origins (default: `*`) |
| `NEXT_PUBLIC_API_URL` | Yes (Frontend) | Backend API URL for frontend |

See [`.env.example`](.env.example) for the complete template.

---

## Hardware Integration (ESP32)

### Supported Sensors

| Sensor | Measures | Unit |
|--------|----------|------|
| SHT31 | Air Temperature, Humidity | °C, % |
| BH1750 | Light Intensity | lux |
| Capacitive Soil Moisture v2 | Soil Moisture | % |
| DS18B20 Waterproof | Soil Temperature | °C |
| MLX90614 | Leaf Temperature | °C |

### Canonical JSON Payload

Send to `POST /hardware/update`:

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

The endpoint validates, calibrates, stores, and feeds the AI pipeline — returning a complete analysis response.

See [`docs/ESP32_INTEGRATION.md`](docs/ESP32_INTEGRATION.md) for full wiring diagrams and Arduino code.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Health check |
| `GET` | `/search/<query>` | Fuzzy plant search |
| `POST` | `/analyze` | Unified AI analysis |
| `GET` | `/predict/<plant>/<stage>/<phase>` | Legacy prediction |
| `GET` | `/simulator/state` | Simulator current state |
| `POST` | `/simulator/start` | Start simulation |
| `POST` | `/simulator/pause` | Pause simulation |
| `POST` | `/simulator/reset` | Reset simulation |
| `POST` | `/simulator/step` | Manual step |
| `POST` | `/simulator/scenario` | Set scenario |
| `POST` | `/simulator/speed` | Set simulation speed |
| `GET` | `/simulator/history` | Simulation history |
| `POST` | `/simulator/analyze` | Analyze current sim state |
| `POST` | `/simulator/temporal/verify` | Verify temporal predictions |
| `GET` | `/simulator/temporal/replay` | Replay historical state |
| `GET` | `/simulator/temporal/accuracy` | Prediction accuracy stats |
| `GET` | `/simulator/temporal/snapshots` | Historical snapshots |
| `GET` | `/simulator/temporal/compare` | Compare prediction vs actual |
| `POST` | `/hardware/update` | Submit hardware sensor data |
| `GET` | `/hardware/status` | Device connection status |
| `GET` | `/hardware/history` | Hardware packet history |
| `GET` | `/hardware/calibration` | Sensor calibration status |
| `POST` | `/hardware/calibrate` | Set sensor calibration |
| `POST` | `/hardware/calibrate/reset` | Reset sensor calibration |
| `POST` | `/session/save` | Export session (JSON + report) |
| `GET` | `/session/export` | Quick session export |

Full API documentation: [`docs/API.md`](docs/API.md)

---

## Folder Structure

```
Aletheia/
├── ai/                     # AI models (Random Forest, Decision Engine, etc.)
│   ├── aletheia_model_v3.pkl
│   ├── decision_engine.py
│   ├── sensor_guard.py
│   ├── unified_engine.py
│   └── anomaly_detector.py
├── backend/                # Flask backend
│   ├── app.py              # Main Flask application
│   ├── unified_pipeline.py # Production pipeline
│   ├── biology_engine.py   # Plant biology evaluation
│   ├── tavily_search.py    # Tavily web search with key rotation
│   ├── openrouter_extractor.py  # OpenRouter LLM integration
│   ├── ai_reasoning_cache.py    # AI reasoning response cache
│   ├── plant_cache.py      # Plant profile cache
│   ├── plant_pipeline.py   # Plant data pipeline
│   ├── parser_extractor.py # Tavily result parser
│   ├── fuzzy_search.py     # Fuzzy plant name search
│   ├── plant_profile_schema.py  # Default plant profile
│   ├── simulator/          # Digital Twin simulator
│   │   ├── engine.py       # Weather, Soil, Plant, VirtualSensors
│   │   └── scenarios.py    # 10 deterministic scenarios
│   └── hardware/           # ESP32 hardware integration
│       ├── validator.py    # Packet validation
│       ├── store.py        # Hardware data persistence
│       └── calibration.py  # Sensor calibration
├── frontend/               # Next.js frontend
│   └── app/
│       ├── page.tsx        # Main dashboard
│       ├── layout.tsx      # Root layout
│       └── globals.css     # Global styles
├── docs/                   # Documentation
│   ├── API.md              # API reference
│   └── ESP32_INTEGRATION.md # Hardware integration guide
├── .env.example            # Environment variable template
├── Dockerfile              # Hugging Face Spaces deployment
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## Troubleshooting

### Backend won't start
- Check `backend/.env` has valid API keys
- Verify Python 3.10+ is installed
- Run `pip install -r requirements.txt` again

### Frontend shows blank dashboard
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check backend is running and accessible
- Open browser console for CORS errors

### OpenRouter returns 402 errors
- This means API credits are exhausted
- The system falls back to cached AI reasoning (24h expiry)
- Add credits at https://openrouter.ai

### Tavily returns no results
- All keys may be exhausted
- The system falls back to cached plant profiles
- Add new keys at https://tavily.com

### ESP32 not connecting
- Verify JSON payload matches canonical schema exactly
- Check WiFi connectivity on ESP32
- Verify backend URL is correct in ESP32 firmware

---

## License

MIT License — see LICENSE file for details.
