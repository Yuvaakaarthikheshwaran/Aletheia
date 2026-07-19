# Aletheia Production-Readiness Test Checklist

## Pre-Deployment Verification

### 1. TypeScript Compilation
- [x] `npx tsc --noEmit` passes with zero errors
- [x] `npm run build` completes successfully (Next.js 16.2.10 + Turbopack)

### 2. Python Syntax
- [x] `backend/app.py` compiles clean
- [x] `backend/unified_pipeline.py` compiles clean
- [x] `backend/hardware/validator.py` compiles clean
- [x] `backend/hardware/store.py` compiles clean
- [x] `backend/hardware/calibration.py` compiles clean
- [x] `tools/hardware_emulator.py` compiles clean

### 3. Mode Selector (PART 1-3)
- [ ] Click "Simulator" — simulator controls appear, hardware/replay controls hidden
- [ ] Click "Real Hardware" — hardware controls appear, simulator/replay controls hidden
- [ ] Click "Replay" — replay controls appear, simulator/hardware controls hidden
- [ ] Mode switch clears irrelevant state (e.g., switching from hardware to simulator clears deviceStatus)
- [ ] Simulator Start/Pause/Reset buttons only affect simulator, not hardware
- [ ] Hardware Refresh/Disconnect buttons only affect hardware, not simulator

### 4. Temporal Confidence Fix (PART 5)
- [ ] Confidence percentages never exceed 100%
- [ ] Future confidence displays correctly (0-100 range)
- [ ] No "9988%" or similar absurd values
- [ ] Temporal confidence shows "Warming" when <5 hardware packets

### 5. AI Reasoning Console (PART 6)
- [ ] Shows "✓ OpenRouter AI" badge when AI-generated
- [ ] Shows "⚠ Partial (Truncated)" when response truncated
- [ ] Shows "⚡ Fallback (Model Offline)" when model unavailable
- [ ] Explanation, Diagnosis, and Confidence Narrative sections render

### 6. Stress Radar (PART 7)
- [ ] Radar chart renders with 6 dimensions (Heat Stress, Humidity Deficit, Leaf ΔT Risk, Root Zone, Water Stress, Light Intensity)
- [ ] PolarRadiusAxis shows 0-100 domain
- [ ] Stress prediction badge shows severity
- [ ] AI Stress Factors section lists reasons

### 7. Hardware Temporal AI Path (PART 8)
- [ ] POST /hardware/update → validates → calibrates → stores → runs unified pipeline
- [ ] sensor_stream from HardwareStore feeds into Temporal AI
- [ ] Analysis response includes temporal predictions

### 8. Sensor Status Indicators (PART 9)
- [ ] Each sensor card shows health status badge (ONLINE/OFFLINE/STALE/INVALID/UNCAL)
- [ ] Color-coded left border matches status
- [ ] Values within absolute limits show ONLINE (green)
- [ ] Values outside limits show INVALID (orange)
- [ ] Stale packets (>60s) show STALE (yellow)
- [ ] Missing values show OFFLINE (red)

### 9. Packet Age Display (PART 10)
- [ ] "Last packet: Xs ago" shows with color coding
- [ ] Green for <15s, yellow for <60s, red for >60s
- [ ] "⚠ Device may be offline" warning when age >60s

### 10. Hardware Auth (PART 11)
- [ ] POST /hardware/update without Authorization header → 401
- [ ] POST /hardware/update with wrong key → 401
- [ ] POST /hardware/update with correct Bearer token → 200
- [ ] HARDWARE_API_KEY not set → auth skipped (backward compatible)

### 11. Device ID (PART 12)
- [ ] Canonical device ID "ALETHEIA-ESP32-001" used throughout
- [ ] Device ID displayed in hardware panel
- [ ] Device ID shown in packet count footer

### 12. Hardware Emulator (PART 13)
- [ ] `python tools/hardware_emulator.py --mode single` sends one packet
- [ ] `python tools/hardware_emulator.py --mode stream` sends continuous packets
- [ ] `--auth-key` flag adds Bearer token
- [ ] Sensor drift simulation works over time
- [ ] Summary statistics display after stream

### 13. Empty State (PART 14)
- [ ] Hardware mode with no device shows "Waiting for Device" panel
- [ ] JSON payload schema displayed
- [ ] Reference to hardware_emulator.py shown
- [ ] Device status grid hidden when no device connected

### 14. Start/Pause/Reset Semantics (PART 15)
- [ ] Simulator Start button shows "▶ Start" when stopped, "▶ Running" when running
- [ ] Live Mode button shows "▶ Start Live" when off, "⏹ Stop Live" when on
- [ ] Pause button disabled when not running
- [ ] Reset button always enabled

### 15. UI Units (PART 16)
- [ ] Air temp shows °C
- [ ] Humidity shows %
- [ ] Soil temp shows °C
- [ ] Soil moisture shows %
- [ ] Light shows lux
- [ ] Leaf temp shows °C
- [ ] Sampling rate shows Hz
- [ ] Confidence values show %
- [ ] Packet age shows s/m/h

### 16. API Safety (PART 17)
- [ ] safeFetch validates API_BASE before making requests
- [ ] Network errors caught and displayed
- [ ] Non-JSON responses handled gracefully
- [ ] JSON parse errors caught
- [ ] No localhost hardcoded in production

### 17. Temporal Upgrade Preservation (PART 18)
- [ ] GET /simulator/temporal/history endpoint functional
- [ ] Time navigation bar with quick-jump buttons
- [ ] LIVE/HISTORICAL indicator badge
- [ ] Return to Live button visible in historical mode
- [ ] Temporal Replay slider synced with selectedTime
- [ ] Custom tooltip with date, time, timezone, value, unit

### 18. Confidence Panel (PART 4)
- [ ] Cold-start warning banner for hardware mode with <5 packets
- [ ] 5 confidence types displayed: Sensor, AI Model, Temporal, Biology, Overall
- [ ] Color coding: green ≥80%, yellow ≥50%, red <50%
- [ ] Weight breakdown footer: "Sensor 15% · AI Model 30% · Temporal 25% · Biology 30%"
- [ ] Temporal shows "Warming" when insufficient history

## Backend-Specific Tests

### Flask Endpoints
- [ ] GET / — health check returns 200
- [ ] POST /analyze — returns unified analysis
- [ ] GET /simulator/state — returns current state
- [ ] POST /simulator/start — starts simulation
- [ ] POST /simulator/pause — pauses simulation
- [ ] POST /simulator/reset — resets simulation
- [ ] POST /simulator/scenario — changes scenario
- [ ] POST /simulator/speed — changes speed
- [ ] GET /simulator/history — returns history
- [ ] POST /simulator/analyze — analyzes current state
- [ ] POST /simulator/temporal/verify — verifies predictions
- [ ] GET /simulator/temporal/replay — replays historical state
- [ ] GET /simulator/temporal/accuracy — returns accuracy data
- [ ] GET /simulator/temporal/snapshots — returns snapshots
- [ ] GET /simulator/temporal/compare — compares prediction vs actual
- [ ] GET /simulator/temporal/history — returns temporal history
- [ ] POST /hardware/update — accepts hardware packets
- [ ] GET /hardware/status — returns device status
- [ ] GET /hardware/history — returns hardware history
- [ ] GET /hardware/calibration — returns calibration data
- [ ] POST /hardware/calibrate — sets calibration
- [ ] POST /hardware/calibrate/reset — resets calibration
- [ ] POST /session/save — saves session
- [ ] GET /session/export — exports session

## Deployment Checklist

- [ ] Frontend builds clean (`npm run build`)
- [ ] Backend Python syntax valid
- [ ] .env.example updated with HARDWARE_API_KEY
- [ ] .gitignore excludes .env files
- [ ] No hardcoded secrets in code
- [ ] README.md up to date
- [ ] API.md up to date
- [ ] Git commit with descriptive message
- [ ] Push to GitHub main branch
- [ ] Report HF Space files for deployment