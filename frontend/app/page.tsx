"use client";

import { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ReferenceLine,
  Legend,
} from "recharts";

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
// Normalize: strip trailing slash so we never produce double-slashes like //analyze
const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

/**
 * Safe fetch wrapper that:
 *  - Validates the API_BASE is configured
 *  - Checks response.ok before parsing JSON
 *  - Verifies Content-Type is JSON before calling .json()
 *  - Returns a structured error instead of throwing JSON.parse on HTML
 */
async function safeFetch(
  path: string,
  options?: RequestInit
): Promise<{ ok: boolean; data: any; error?: string; status: number; contentType: string }> {
  if (!API_BASE) {
    return {
      ok: false,
      data: null,
      status: 0,
      contentType: "",
      error: "Backend URL not configured. Set NEXT_PUBLIC_API_URL in Vercel environment variables.",
    };
  }

  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (fetchErr: any) {
    return {
      ok: false,
      data: null,
      status: 0,
      contentType: "",
      error: `Network error: ${fetchErr.message || "Failed to reach backend at " + url}`,
    };
  }

  const contentType = res.headers.get("content-type") || "";
  const status = res.status;

  // Read as text first — never blindly call .json()
  let rawText = "";
  try {
    rawText = await res.text();
  } catch (textErr: any) {
    return {
      ok: false,
      data: null,
      status,
      contentType,
      error: `Failed to read response body: ${textErr.message}`,
    };
  }

  // If the response is not JSON, return the raw text as error context
  if (!contentType.includes("application/json")) {
    const preview = rawText.substring(0, 200).replace(/\n/g, " ");
    return {
      ok: false,
      data: null,
      status,
      contentType,
      error: `Backend returned non-JSON response (HTTP ${status}, Content-Type: ${contentType || "unknown"}). Preview: ${preview}...`,
    };
  }

  // Try to parse JSON
  let json: any;
  try {
    json = JSON.parse(rawText);
  } catch (parseErr: any) {
    return {
      ok: false,
      data: null,
      status,
      contentType,
      error: `Failed to parse JSON response (HTTP ${status}): ${parseErr.message}`,
    };
  }

  return { ok: res.ok, data: json, status, contentType };
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [selectedPlant, setSelectedPlant] = useState("tomato");
  const [growthStage, setGrowthStage] = useState("flowering");
  const [phase, setPhase] = useState("day");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Simulator State ---
  const [simRunning, setSimRunning] = useState(false);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [simScenario, setSimScenario] = useState("normal_day");
  const [simState, setSimState] = useState<any>(null);
  const [scenarioList, setScenarioList] = useState<Record<string, any>>({});
  const [liveMode, setLiveMode] = useState(false);

  // --- Temporal Replay State ---
  const [replayMinute, setReplayMinute] = useState<number | null>(null);
  const [replayData, setReplayData] = useState<any>(null);
  const [replayLoading, setReplayLoading] = useState(false);

  // --- Prediction Accuracy State ---
  const [accuracyData, setAccuracyData] = useState<any>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(false);

  // --- Comparison Mode State ---
  const [snapshotList, setSnapshotList] = useState<any[]>([]);
  const [snapshotMinute, setSnapshotMinute] = useState<number | null>(null);
  const [compareMinute, setCompareMinute] = useState<number | null>(null);
  const [compareData, setCompareData] = useState<any>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // --- Operating Mode State ---
  // "simulator" = digital twin simulation (default)
  // "hardware"  = real ESP32-S3 hardware (requires device connection)
  // "replay"    = historical replay / temporal navigation
  const [operatingMode, setOperatingMode] = useState<"simulator" | "hardware" | "replay">("simulator");

  // --- Hardware Integration State ---
  const [deviceStatus, setDeviceStatus] = useState<any>(null);
  const [hardwareHistory, setHardwareHistory] = useState<any[]>([]);
  const [calibrationData, setCalibrationData] = useState<any>(null);
  const [sessionExportLoading, setSessionExportLoading] = useState(false);
  const [hardwarePacketStatus, setHardwarePacketStatus] = useState<string | null>(null);

  // --- Temporal Navigation State (NEW) ---
  // selectedTime: null = LIVE/NOW; number = viewing a specific sim_minute
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  // temporalRange: the time window being viewed
  const [temporalRange, setTemporalRange] = useState<string>("24h");
  // temporalSeries: per-variable historical data from the backend
  const [temporalSeries, setTemporalSeries] = useState<Record<string, any[]> | null>(null);
  // temporalSeriesLoading: loading state for historical data fetch
  const [temporalSeriesLoading, setTemporalSeriesLoading] = useState(false);
  // temporalViewMode: "live" | "historical" | "forecast"
  const temporalViewMode: "live" | "historical" | "forecast" =
    selectedTime === null ? "live" : "historical";

  // --- Fetch simulator state (scenario list, current state) ---
  const fetchSimState = useCallback(async () => {
    const result = await safeFetch("/simulator/state");
    if (result.ok && result.data) {
      setSimState(result.data);
      if (result.data.available_scenarios) {
        setScenarioList(result.data.available_scenarios);
      }
    }
    // Silently ignore errors — simulator may not be running yet
  }, []);

  // --- Core analysis: step simulator + run AI pipeline ---
  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);

    const result = await safeFetch("/simulator/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plant: selectedPlant,
        stage: growthStage,
        dt_minutes: simSpeed,
      }),
    });

    if (!result.ok) {
      setError(result.error || `Backend returned HTTP ${result.status}`);
      console.error("Analyze error:", result.error, "status:", result.status, "contentType:", result.contentType);
      setLoading(false);
      return;
    }

    const json = result.data;
    if (json.error) {
      setError(json.message || json.error);
    } else {
      // Merge simulator state + analysis
      setData({
        ...json.analysis,
        _simulator: json.simulator,
      });
      setSimState((prev: any) => ({
        ...prev,
        ...json.simulator,
      }));
    }

    setLoading(false);
  }, [selectedPlant, growthStage, simSpeed]);

  // --- Simulator controls ---
  const simControl = useCallback(async (action: string, body?: any) => {
    const result = await safeFetch(`/simulator/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (result.ok && result.data) {
      if (action === "start") setSimRunning(true);
      if (action === "pause" || action === "reset") setSimRunning(false);
      if (action === "scenario") setSimScenario(body?.scenario || "normal_day");
      if (action === "speed") setSimSpeed(body?.speed || 1.0);
      await fetchSimState();
    } else {
      console.error("Simulator control error:", result.error);
    }
  }, [fetchSimState]);

  // --- Temporal Replay: fetch state at a specific sim_minute ---
  const fetchReplay = useCallback(async (minute: number, n: number = 10) => {
    setReplayLoading(true);
    const result = await safeFetch(`/simulator/temporal/replay?minute=${minute}&n=${n}`);
    if (result.ok && result.data) {
      setReplayData(result.data);
      setReplayMinute(minute);
    } else {
      console.error("Replay fetch error:", result.error);
    }
    setReplayLoading(false);
  }, []);

  // --- Prediction Accuracy: fetch rolling accuracy ---
  const fetchAccuracy = useCallback(async () => {
    setAccuracyLoading(true);
    const result = await safeFetch("/simulator/temporal/accuracy");
    if (result.ok && result.data) {
      setAccuracyData(result.data);
    } else {
      console.error("Accuracy fetch error:", result.error);
    }
    setAccuracyLoading(false);
  }, []);

  // --- Comparison Mode: fetch available snapshots ---
  const fetchSnapshots = useCallback(async () => {
    const result = await safeFetch("/simulator/temporal/snapshots?limit=100");
    if (result.ok && result.data) {
      setSnapshotList(result.data.snapshots || []);
    } else {
      console.error("Snapshots fetch error:", result.error);
    }
  }, []);

  // --- Comparison Mode: compare prediction vs actual ---
  const fetchCompare = useCallback(async (snapMin: number, cmpMin: number) => {
    setCompareLoading(true);
    const result = await safeFetch(
      `/simulator/temporal/compare?snapshot_minute=${snapMin}&compare_minute=${cmpMin}`
    );
    if (result.ok && result.data) {
      setCompareData(result.data);
    } else {
      console.error("Compare fetch error:", result.error);
    }
    setCompareLoading(false);
  }, []);

  // --- Temporal Navigation: fetch historical data for a time range ---
  const fetchTemporalHistory = useCallback(async (range: string = "24h") => {
    setTemporalSeriesLoading(true);
    const result = await safeFetch(
      `/simulator/temporal/history?range=${range}&variables=air_temp,humidity,soil_moisture,leaf_temp_delta,light,soil_temp,stress,growth`
    );
    if (result.ok && result.data) {
      setTemporalSeries(result.data.series || {});
      setTemporalRange(range);
    } else {
      console.error("Temporal history fetch error:", result.error);
    }
    setTemporalSeriesLoading(false);
  }, []);

  // --- Temporal Navigation: jump to a specific sim_minute ---
  const jumpToTime = useCallback((minute: number | null) => {
    setSelectedTime(minute);
    if (minute !== null) {
      // Also trigger replay fetch for detailed state at that minute
      fetchReplay(minute);
    }
  }, [fetchReplay]);

  // --- Temporal Navigation: return to LIVE/NOW ---
  const returnToLive = useCallback(() => {
    setSelectedTime(null);
    setReplayMinute(null);
    setReplayData(null);
    setTemporalRange("24h");
    // Re-fetch current state
    fetchSimState();
  }, [fetchSimState]);

  // --- Hardware: fetch device status ---
  const fetchDeviceStatus = useCallback(async () => {
    const result = await safeFetch("/hardware/status");
    if (result.ok && result.data) {
      setDeviceStatus(result.data);
    } else {
      console.error("Device status fetch error:", result.error);
    }
  }, []);

  // --- Hardware: fetch history ---
  const fetchHardwareHistory = useCallback(async (n: number = 60) => {
    const result = await safeFetch(`/hardware/history?n=${n}`);
    if (result.ok && result.data) {
      setHardwareHistory(result.data.history || []);
      return result.data;
    } else {
      console.error("Hardware history fetch error:", result.error);
      return null;
    }
  }, []);

  // --- Hardware: fetch calibration ---
  const fetchCalibration = useCallback(async (deviceId: string = "ALETHEIA-ESP32-001") => {
    const result = await safeFetch(`/hardware/calibration?device_id=${deviceId}`);
    if (result.ok && result.data) {
      setCalibrationData(result.data);
    } else {
      console.error("Calibration fetch error:", result.error);
    }
  }, []);

  // --- Hardware: send a simulated hardware packet (for testing without ESP32) ---
  const sendHardwarePacket = useCallback(async () => {
    setLoading(true);
    setHardwarePacketStatus(null);
    const now = new Date().toISOString();
    const result = await safeFetch("/hardware/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        timestamp: now,
        device_id: "ALETHEIA-ESP32-001",
        plant: selectedPlant,
        stage: growthStage,
        mode: phase,
        firmware_version: "1.0.0",
        sensor_data: {
          air_temp: 31.4 + Math.random() * 2 - 1,
          humidity: 58.2 + Math.random() * 4 - 2,
          soil_temp: 28.1 + Math.random() * 1 - 0.5,
          soil_moisture: 46.8 + Math.random() * 3 - 1.5,
          light: 18200 + Math.random() * 1000 - 500,
          leaf_temp: 33.5 + Math.random() * 2 - 1,
        },
      }),
    });

    if (!result.ok) {
      setHardwarePacketStatus(`Error: ${result.error}`);
      setError(result.error ?? null);
      console.error("Hardware packet error:", result.error, "status:", result.status);
      setLoading(false);
      return;
    }

    const json = result.data;
    if (json.error) {
      setHardwarePacketStatus(`Rejected: ${json.message}`);
      setError(json.message);
    } else {
      setHardwarePacketStatus(`Accepted — ${json.device_id}`);
      // Merge analysis into data display
      setData({
        ...json.analysis,
        _source: "hardware",
        _device_id: json.device_id,
      });
      // Refresh device status and history
      fetchDeviceStatus();
      fetchHardwareHistory();
    }
    setLoading(false);
  }, [selectedPlant, growthStage, phase, fetchDeviceStatus, fetchHardwareHistory]);

  // --- Session: save/export ---
  const saveSession = useCallback(async (source: string = "simulator", format: string = "both") => {
    setSessionExportLoading(true);
    const result = await safeFetch("/session/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, format, include_replay: true }),
    });

    if (!result.ok) {
      setError(result.error || `Session save failed (HTTP ${result.status})`);
      console.error("Session save error:", result.error);
      setSessionExportLoading(false);
      return;
    }

    const json = result.data;
    if (json.error) {
      setError(json.error);
    } else {
      // Trigger download of the JSON
      if (json.json) {
        const blob = new Blob([JSON.stringify(json.json, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `aletheia-session-${source}-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
      // Trigger download of the report
      if (json.report) {
        const blob = new Blob([json.report], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `aletheia-report-${source}-${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
      }
      setHardwarePacketStatus(`Session exported (${source})`);
    }
    setSessionExportLoading(false);
  }, []);

  // --- Hardware: set calibration ---
  const setCalibration = useCallback(async (deviceId: string, sensor: string, offset: number, scaleFactor: number) => {
    const result = await safeFetch("/hardware/calibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId, sensor, offset, scale_factor: scaleFactor }),
    });
    if (result.ok && result.data) {
      if (result.data.status === "calibrated") {
        fetchCalibration(deviceId);
      }
      return result.data;
    } else {
      console.error("Calibration set error:", result.error);
      return null;
    }
  }, [fetchCalibration]);

  // --- Hardware: reset calibration ---
  const resetCalibration = useCallback(async (deviceId: string, sensor?: string) => {
    const result = await safeFetch("/hardware/calibrate/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId, sensor: sensor || undefined }),
    });
    if (result.ok) {
      await fetchCalibration(deviceId);
    } else {
      console.error("Calibration reset error:", result.error);
    }
  }, [fetchCalibration]);

  // Initial load
  useEffect(() => {
    fetchSimState();
    analyze();
  }, []);

  // Live polling: step simulator + analyze
  useEffect(() => {
    if (!liveMode || !simRunning) return;
    const interval = setInterval(() => {
      analyze();
    }, 3000);
    return () => clearInterval(interval);
  }, [liveMode, simRunning, analyze]);

  // Hardware polling: fetch device status when in hardware mode
  useEffect(() => {
    if (operatingMode !== "hardware") return;
    fetchDeviceStatus();
    fetchHardwareHistory();
    fetchCalibration();
    const interval = setInterval(() => {
      fetchDeviceStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, [operatingMode, fetchDeviceStatus, fetchHardwareHistory, fetchCalibration]);

  // Hardware live stream: auto-send packets when in hardware live mode
  useEffect(() => {
    if (operatingMode !== "hardware" || !liveMode) return;
    const interval = setInterval(() => {
      sendHardwarePacket();
    }, 3000);
    return () => clearInterval(interval);
  }, [operatingMode, liveMode, sendHardwarePacket]);

  // Temporal history: fetch when range changes or on initial load (live mode)
  useEffect(() => {
    if (operatingMode === "hardware" && temporalViewMode === "live") {
      fetchTemporalHistory(temporalRange);
    }
  }, [temporalRange, operatingMode, fetchTemporalHistory]);

  // --- Data extraction from unified response ---
  const sensor = data?.sensor_validation?.repaired_data || data?._simulator?.sensor_data;
  const plantProfile = data?.plant_profile;
  const stageProfile = plantProfile?.growth_stages?.[growthStage];
  const temporal = data?.temporal_prediction;
  const biology = data?.biology_analysis;
  const stress = data?.stress_analysis;
  const aiReasoning = data?.ai_reasoning;
  const confidence = data?.confidence;
  const recommendations = data?.recommendations;
  const simulator = data?._simulator;
  const causalChain = simulator?.causal_chain || simState?.causal_chain || [];

  // Build trajectory data from simulator history + future prediction projection
  const trajectory: any[] = simulator?.trajectory || [];
  const currentSimMinute = simulator?.sim_minute ?? simState?.sim_minute ?? 0;
  const currentSimTime = simulator?.sim_time ?? simState?.sim_time ?? "12:00";

  // ---- NEW: Temporal-state-aware chart data building ----
  // Priority: temporalSeries (from dedicated history endpoint) > trajectory (from /analyze)
  // This gives us properly downsampled, type-labeled historical data

  // Build PAST data from temporalSeries if available, otherwise fall back to trajectory
  const buildPastData = (): any[] => {
    if (temporalSeries && Object.keys(temporalSeries).length > 0) {
      // Use the dedicated temporal history endpoint data
      // Merge all variables into unified data points keyed by sim_minute
      const pointMap = new Map<number, any>();
      for (const [varName, points] of Object.entries(temporalSeries)) {
        for (const p of points) {
          if (!pointMap.has(p.sim_minute)) {
            pointMap.set(p.sim_minute, {
              label: p.sim_time,
              minute: p.sim_minute,
              type: "past",
              _dataType: p.data_type || "observed",
            });
          }
          const entry = pointMap.get(p.sim_minute)!;
          entry[varName] = p.value;
        }
      }
      // Convert to sorted array
      return Array.from(pointMap.values()).sort((a, b) => a.minute - b.minute);
    }
    // Fallback: use trajectory from /analyze response
    return trajectory.map((point: any) => ({
      label: point.sim_time,
      minute: point.sim_minute,
      air_temp: point.air_temp,
      humidity: point.humidity,
      soil_moisture: point.soil_moisture,
      leaf_temp_delta: point.leaf_temp_delta,
      stress: point.stress,
      growth: point.growth,
      type: "past",
      _dataType: "observed",
    }));
  };

  const chartData = buildPastData();

  // Determine the effective "now" minute based on temporal view mode
  const effectiveNowMinute = selectedTime !== null ? selectedTime : currentSimMinute;
  const effectiveNowTime = selectedTime !== null
    ? (replayData?.target?.sim_time || chartData.find(p => p.minute === selectedTime)?.label || `Min ${selectedTime}`)
    : currentSimTime;

  // Add current/live state as NOW marker
  const nowSensorData = selectedTime !== null && replayData?.target?.sensor_data
    ? replayData.target.sensor_data
    : sensor;
  const nowPlantData = selectedTime !== null && replayData?.target?.plant
    ? replayData.target.plant
    : simState?.plant;

  const nowEntry = {
    label: selectedTime !== null ? `● ${effectiveNowTime}` : "● NOW",
    minute: effectiveNowMinute,
    air_temp: nowSensorData?.air_temp,
    humidity: nowSensorData?.humidity,
    soil_moisture: nowSensorData?.soil_moisture,
    leaf_temp_delta: nowSensorData?.leaf_temp_delta,
    stress: nowPlantData?.stress ?? 0,
    growth: nowPlantData?.growth ?? 0,
    type: "now",
    _dataType: "observed",
  };

  // Future prediction projection — only show when in LIVE mode
  // Uses Temporal AI model output when available, falls back to linear extrapolation
  const futurePrediction: any[] = [];
  if (temporalViewMode === "live" && chartData.length >= 2) {
    const last = chartData[chartData.length - 1];
    const prev = chartData[chartData.length - 2];
    // future_confidence is 0-100 from backend; normalize to 0-1 for CI band math
    const futureConfidenceRaw = temporal?.future_state?.future_confidence ?? 70;
    const futureConfidence = Math.min(1, Math.max(0, futureConfidenceRaw / 100));
    const futureLabel = temporal?.future_state?.future_prediction ?? "stable";

    for (let i = 1; i <= 5; i++) {
      const frac = i / 5;
      futurePrediction.push({
        label: `+${i * 10}m`,
        minute: last.minute + i * 10,
        air_temp: last.air_temp + (last.air_temp - prev.air_temp) * frac,
        humidity: last.humidity + (last.humidity - prev.humidity) * frac,
        soil_moisture: last.soil_moisture + (last.soil_moisture - prev.soil_moisture) * frac,
        leaf_temp_delta: last.leaf_temp_delta + (last.leaf_temp_delta - prev.leaf_temp_delta) * frac,
        stress: last.stress,
        growth: last.growth,
        type: "future",
        _dataType: "forecast",
        // Confidence band: wider as we go further into future
        ci_upper_temp: last.air_temp + (last.air_temp - prev.air_temp) * frac + (1 - futureConfidence) * 2 * (i),
        ci_lower_temp: last.air_temp + (last.air_temp - prev.air_temp) * frac - (1 - futureConfidence) * 2 * (i),
        ci_upper_humidity: last.humidity + (last.humidity - prev.humidity) * frac + (1 - futureConfidence) * 3 * (i),
        ci_lower_humidity: last.humidity + (last.humidity - prev.humidity) * frac - (1 - futureConfidence) * 3 * (i),
      });
    }
  }

  // Merge all for the full chart — past data up to effectiveNowMinute, then NOW, then future
  const pastUpToNow = chartData.filter(p => p.minute <= effectiveNowMinute);
  const pastAfterNow = chartData.filter(p => p.minute > effectiveNowMinute);
  // When viewing historical time, data after selectedTime becomes "future from that perspective"
  const pastAfterNowLabeled = pastAfterNow.map(p => ({ ...p, type: "future", _dataType: "observed" }));

  const fullChartData = [...pastUpToNow, nowEntry, ...pastAfterNowLabeled, ...futurePrediction];

  // Stat card values from trajectory
  const pastTrend = chartData.length >= 2
    ? `${chartData[chartData.length - 2]?.air_temp?.toFixed(1)} → ${chartData[chartData.length - 1]?.air_temp?.toFixed(1)} → ${sensor?.air_temp?.toFixed(1) || "—"}`
    : "—";
  const tempVelocity = sensor?.air_temp_rate ?? (
    chartData.length >= 2
      ? (chartData[chartData.length - 1]?.air_temp - chartData[chartData.length - 2]?.air_temp)
      : 0
  );

  function metricName(name: string) {
    return name.replaceAll("_", " ").toUpperCase();
  }

  function healthColor(score: number) {
    if (score >= 80) return "from-green-400 to-green-600";
    if (score >= 50) return "from-yellow-400 to-orange-500";
    return "from-red-500 to-red-700";
  }

  return (
    <main className="min-h-screen bg-black text-white overflow-hidden px-8 py-6">
      <div className="absolute inset-0 bg-gradient-to-br from-black via-[#071226] to-[#020617]" />
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-green-500/10 blur-[150px] rounded-full" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-blue-500/10 blur-[150px] rounded-full" />

      <div className="relative z-10">
        <h1 className="text-7xl font-bold bg-gradient-to-r from-green-300 to-blue-400 bg-clip-text text-transparent">
          Aletheia
        </h1>

        <p className="text-gray-400 text-lg mb-6">
          Autonomous Plant Intelligence System — Digital Twin
        </p>

        <div className="flex gap-6 mb-6 flex-wrap">
          <div className="text-green-400">● Backend Online</div>
          <div className="text-green-400">● AI Active</div>
          <div className="text-green-400">● Biology Active</div>
          {data && <div className="text-green-400">● Pipeline Live</div>}
          {operatingMode === "simulator" && simRunning && <div className="text-blue-400">● Simulator Running</div>}
          {operatingMode === "simulator" && !simRunning && <div className="text-yellow-400">● Simulator Paused</div>}
          {operatingMode === "hardware" && <div className="text-purple-400">● Hardware Mode</div>}
          {operatingMode === "replay" && <div className="text-yellow-400">● Replay Mode</div>}
          {operatingMode === "hardware" && deviceStatus && (
            <div className={deviceStatus.online ? "text-green-400" : "text-red-400"}>
              ● Device {deviceStatus.online ? "Online" : "Offline"}
            </div>
          )}
          {hardwarePacketStatus && (
            <div className="text-yellow-400 text-sm">● {hardwarePacketStatus}</div>
          )}
        </div>

        {/* ============================================================ */}
        {/* OPERATING MODE SELECTOR + MODE-SPECIFIC CONTROLS */}
        {/* ============================================================ */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6 mb-8">
          {/* ---- 3-Mode Segmented Selector ---- */}
          <div className="flex items-center gap-2 mb-6">
            <h2 className="text-2xl mr-4">Operating Mode</h2>
            <div className="flex bg-black/40 rounded-xl p-1 border border-white/10">
              <button
                onClick={() => {
                  setOperatingMode("simulator");
                  setSelectedTime(null); // exit replay
                }}
                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
                  operatingMode === "simulator"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <span>🖥</span> Simulator
              </button>
              <button
                onClick={() => {
                  setOperatingMode("hardware");
                  setSelectedTime(null); // exit replay
                  fetchDeviceStatus();
                  fetchHardwareHistory();
                  fetchCalibration();
                }}
                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
                  operatingMode === "hardware"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-600/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <span>🔌</span> Hardware
              </button>
              <button
                onClick={() => {
                  setOperatingMode("replay");
                  if (temporalSeries === null) fetchTemporalHistory("24h");
                }}
                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
                  operatingMode === "replay"
                    ? "bg-yellow-600 text-white shadow-lg shadow-yellow-600/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <span>◷</span> Replay
              </button>
            </div>

            {/* Save Session — always available */}
            <button
              onClick={() => saveSession(operatingMode === "hardware" ? "hardware" : "simulator", "both")}
              disabled={sessionExportLoading}
              className="ml-auto bg-indigo-600 hover:bg-indigo-500 rounded-xl px-5 py-2.5 font-bold transition disabled:opacity-50 text-sm"
            >
              {sessionExportLoading ? "..." : "💾 Save"}
            </button>
          </div>

          {/* ---- SIMULATOR MODE CONTROLS ---- */}
          {operatingMode === "simulator" && (
            <>
              <div className="grid grid-cols-6 gap-4 mb-4">
                <button
                  onClick={() => simControl("start")}
                  disabled={simRunning}
                  className="bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl py-3 font-bold transition"
                >
                  ▶ {simRunning ? "Running" : "Start"}
                </button>
                <button
                  onClick={() => simControl("pause")}
                  disabled={!simRunning}
                  className="bg-yellow-600 hover:bg-yellow-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl py-3 font-bold transition"
                >
                  ⏸ Pause
                </button>
                <button
                  onClick={() => simControl("reset")}
                  className="bg-red-600 hover:bg-red-500 rounded-xl py-3 font-bold transition"
                >
                  ↺ Reset
                </button>
                <select
                  value={simSpeed}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setSimSpeed(v);
                    simControl("speed", { speed: v });
                  }}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3"
                >
                  <option value={0.5}>0.5x Speed</option>
                  <option value={1.0}>1x (Real-time)</option>
                  <option value={10.0}>10x Speed</option>
                  <option value={60.0}>60x (1h/s)</option>
                  <option value={120.0}>120x Speed</option>
                </select>
                <select
                  value={simScenario}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSimScenario(v);
                    simControl("scenario", { scenario: v });
                  }}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3"
                >
                  {Object.entries(scenarioList).map(([key, cfg]: any) => (
                    <option key={key} value={key}>
                      {cfg.label || key}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => {
                    if (!simRunning) simControl("start");
                    setLiveMode(!liveMode);
                  }}
                  className={`rounded-xl py-3 font-bold transition ${
                    liveMode ? "bg-red-500 hover:bg-red-400" : "bg-blue-500 hover:bg-blue-400"
                  }`}
                >
                  {liveMode ? "⏹ Stop Live" : "▶ Start Live"}
                </button>
              </div>

              {/* Simulator Status Bar */}
              <div className="grid grid-cols-6 gap-4 text-sm">
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Status</span>
                  <p className={simRunning ? "text-green-400" : "text-yellow-400"}>
                    {simRunning ? "Running" : "Paused"}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Sim Time</span>
                  <p className="text-white">{simState?.sim_time || simState?.simTime || "12:00"}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Day Phase</span>
                  <p className="text-white">{simState?.day_phase || simState?.dayPhase || "day"}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Scenario</span>
                  <p className="text-blue-300">{simState?.scenario || simScenario}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Temperature</span>
                  <p className="text-white">{simState?.weather?.air_temp?.toFixed(1) || "—"}°C</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Humidity</span>
                  <p className="text-white">{simState?.weather?.humidity?.toFixed(1) || "—"}%</p>
                </div>
              </div>
            </>
          )}

          {/* ---- HARDWARE MODE CONTROLS ---- */}
          {operatingMode === "hardware" && (
            <>
              <div className="grid grid-cols-4 gap-4 mb-4">
                <button
                  onClick={() => { fetchDeviceStatus(); fetchHardwareHistory(); fetchCalibration(); }}
                  className="bg-purple-600 hover:bg-purple-500 rounded-xl py-3 font-bold transition flex items-center justify-center gap-2"
                >
                  🔄 Refresh Device
                </button>
                <button
                  onClick={() => sendHardwarePacket()}
                  className="bg-green-600 hover:bg-green-500 rounded-xl py-3 font-bold transition flex items-center justify-center gap-2"
                >
                  📡 Send Test Packet
                </button>
                <button
                  onClick={() => {
                    setOperatingMode("simulator");
                    setDeviceStatus(null);
                    setHardwareHistory([]);
                    setCalibrationData(null);
                    setHardwarePacketStatus(null);
                  }}
                  className="bg-red-600/50 hover:bg-red-500 rounded-xl py-3 font-bold transition flex items-center justify-center gap-2"
                >
                  ⏏ Disconnect
                </button>
                <button
                  onClick={() => { fetchHardwareHistory(1440); }}
                  className="bg-indigo-600 hover:bg-indigo-500 rounded-xl py-3 font-bold transition flex items-center justify-center gap-2"
                >
                  📊 Full History
                </button>
              </div>

              {/* Hardware Status Bar */}
              <div className="grid grid-cols-6 gap-4 text-sm">
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Device</span>
                  <p className={deviceStatus?.online ? "text-green-400" : "text-red-400"}>
                    {deviceStatus?.online ? "● Online" : "● Offline"}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Last Packet</span>
                  <p className="text-white">{deviceStatus?.last_packet_time || "—"}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Packet Age</span>
                  <p className={deviceStatus?.online ? "text-green-400" : "text-red-400"}>
                    {deviceStatus?.packet_age_seconds != null ? `${deviceStatus.packet_age_seconds}s` : "—"}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Packets</span>
                  <p className="text-white">{hardwareHistory.length}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Sampling</span>
                  <p className="text-white">{deviceStatus?.sampling_rate_hz?.toFixed(2) || "—"} Hz</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Firmware</span>
                  <p className="text-white font-mono text-xs">{deviceStatus?.firmware_version || "—"}</p>
                </div>
              </div>
            </>
          )}

          {/* ---- REPLAY MODE CONTROLS ---- */}
          {operatingMode === "replay" && (
            <>
              <div className="flex flex-wrap items-center gap-2 mb-4 p-4 bg-black/30 rounded-2xl border border-white/5">
                <select
                  value={temporalRange}
                  onChange={(e) => {
                    setTemporalRange(e.target.value);
                    fetchTemporalHistory(e.target.value);
                  }}
                  className="bg-black/40 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white"
                >
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="all">All History</option>
                </select>

                <div className="h-6 w-px bg-gray-700 mx-1" />

                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 1440))}
                  disabled={effectiveNowMinute < 1440}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  ◀◀ 24H
                </button>
                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 120))}
                  disabled={effectiveNowMinute < 120}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  ◀ 2H
                </button>
                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 30))}
                  disabled={effectiveNowMinute < 30}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  ◀ 30m
                </button>

                <button
                  onClick={returnToLive}
                  className={`px-4 py-1.5 text-xs font-bold rounded-lg transition ${
                    temporalViewMode === "live"
                      ? "bg-green-600 text-white cursor-default"
                      : "bg-yellow-600 hover:bg-yellow-500 text-white"
                  }`}
                >
                  ● NOW
                </button>

                <button
                  onClick={() => jumpToTime(Math.min(currentSimMinute, effectiveNowMinute + 30))}
                  disabled={effectiveNowMinute >= currentSimMinute}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  30m ▶
                </button>
                <button
                  onClick={() => jumpToTime(Math.min(currentSimMinute, effectiveNowMinute + 120))}
                  disabled={effectiveNowMinute >= currentSimMinute}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  2H ▶
                </button>

                {temporalViewMode !== "live" && (
                  <button
                    onClick={returnToLive}
                    className="ml-auto px-5 py-2 text-sm font-bold bg-green-600 hover:bg-green-500 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-green-600/20"
                  >
                    <span>⟳</span> Return to Live
                  </button>
                )}
              </div>

              {/* Replay Status Bar */}
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">View Mode</span>
                  <p className={temporalViewMode === "live" ? "text-green-400" : "text-yellow-400"}>
                    {temporalViewMode === "live" ? "● LIVE" : "◷ HISTORICAL"}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Viewing Time (IST)</span>
                  <p className="text-white font-mono">
                    {selectedTime !== null
                      ? (replayData?.target?.sim_time || `Min ${selectedTime}`)
                      : currentSimTime}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Data Points</span>
                  <p className="text-white">{fullChartData.length}</p>
                </div>
                <div className="bg-black/20 rounded-xl p-3">
                  <span className="text-gray-400">Range</span>
                  <p className="text-white">{temporalRange}</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ============================================================ */}
        {/* HARDWARE DEVICE STATUS PANEL */}
        {/* ============================================================ */}
        {operatingMode === "hardware" && (
          <div className="bg-white/5 backdrop-blur-xl border border-purple-500/20 rounded-3xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl text-purple-300">🔌 Hardware Device Panel</h2>
              <div className="flex gap-3">
                <button
                  onClick={() => { fetchDeviceStatus(); fetchHardwareHistory(); fetchCalibration(); }}
                  className="bg-white/10 hover:bg-white/20 rounded-xl px-4 py-2 text-sm transition"
                >
                  🔄 Refresh
                </button>
                <button
                  onClick={() => {
                    setOperatingMode("simulator");
                    setDeviceStatus(null);
                    setHardwareHistory([]);
                    setCalibrationData(null);
                    setHardwarePacketStatus(null);
                  }}
                  className="bg-red-600/50 hover:bg-red-500 rounded-xl px-4 py-2 text-sm transition"
                >
                  ⏏ Disconnect
                </button>
              </div>
            </div>

            {/* Empty state: no device has ever connected */}
            {!deviceStatus && hardwareHistory.length === 0 && (
              <div className="bg-black/20 rounded-2xl p-10 text-center border border-dashed border-purple-500/30">
                <div className="text-5xl mb-4">📡</div>
                <h3 className="text-xl text-purple-300 mb-2">Waiting for Device</h3>
                <p className="text-gray-400 max-w-md mx-auto mb-6">
                  No ESP32 device has connected yet. The dashboard is listening for
                  incoming sensor packets on <code className="text-purple-400 bg-black/30 px-1.5 py-0.5 rounded text-xs">POST /hardware/update</code>.
                </p>
                <div className="bg-black/30 rounded-xl p-4 max-w-lg mx-auto text-left text-xs font-mono text-gray-400 space-y-1">
                  <p className="text-purple-400 mb-2">Expected JSON payload:</p>
                  <p>{'{'}</p>
                  <p className="pl-4"><span className="text-green-400">"device_id"</span>: <span className="text-yellow-300">"ALETHEIA-ESP32-001"</span>,</p>
                  <p className="pl-4"><span className="text-green-400">"timestamp"</span>: <span className="text-yellow-300">"2026-07-18T17:00:00Z"</span>,</p>
                  <p className="pl-4"><span className="text-green-400">"firmware_version"</span>: <span className="text-yellow-300">"1.0.0"</span>,</p>
                  <p className="pl-4"><span className="text-green-400">"sensor_data"</span>: {'{'}</p>
                  <p className="pl-8"><span className="text-green-400">"air_temp"</span>: <span className="text-yellow-300">28.5</span>,</p>
                  <p className="pl-8"><span className="text-green-400">"humidity"</span>: <span className="text-yellow-300">65.2</span>,</p>
                  <p className="pl-8"><span className="text-green-400">"soil_temp"</span>: <span className="text-yellow-300">24.1</span>,</p>
                  <p className="pl-8"><span className="text-green-400">"soil_moisture"</span>: <span className="text-yellow-300">48.7</span>,</p>
                  <p className="pl-8"><span className="text-green-400">"light"</span>: <span className="text-yellow-300">32000</span>,</p>
                  <p className="pl-8"><span className="text-green-400">"leaf_temp"</span>: <span className="text-yellow-300">26.8</span></p>
                  <p className="pl-4">{'}'}</p>
                  <p>{'}'}</p>
                </div>
                <p className="text-gray-500 text-xs mt-4">
                  Use <code className="text-purple-400 bg-black/20 px-1 rounded">python tools/hardware_emulator.py</code> to test with simulated hardware.
                </p>
              </div>
            )}

            {/* Device status grid — only shown when device has connected */}
            {(deviceStatus || hardwareHistory.length > 0) && (<>
            <div className="grid grid-cols-6 gap-4 mb-4">
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Device ID</span>
                <p className="text-white font-mono">{deviceStatus?.device_id || "ALETHEIA-ESP32-001"}</p>
              </div>
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Connection</span>
                <p className={deviceStatus?.online ? "text-green-400" : "text-red-400"}>
                  {deviceStatus?.online ? "● Online" : "● Offline"}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Last Packet</span>
                <p className="text-white">{deviceStatus?.last_packet_time || "—"}</p>
              </div>
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Packet Age</span>
                <p className={deviceStatus?.online ? "text-green-400" : "text-red-400"}>
                  {deviceStatus?.packet_age_seconds != null ? `${deviceStatus.packet_age_seconds}s` : "—"}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Sampling Rate</span>
                <p className="text-white">{deviceStatus?.sampling_rate_hz?.toFixed(2) || "—"} Hz</p>
              </div>
              <div className="bg-black/20 rounded-xl p-3">
                <span className="text-gray-400 text-xs">Firmware</span>
                <p className="text-white font-mono">{deviceStatus?.firmware_version || "—"}</p>
              </div>
            </div>

            {/* Live Sensor Readings — with per-sensor health status */}
            {hardwareHistory.length > 0 && (
              <>
                {/* Packet age indicator */}
                {(() => {
                  const last = hardwareHistory[hardwareHistory.length - 1];
                  const lastTs = last?.timestamp;
                  let age: number | null = null;
                  let ageDisplay = "—";
                  if (lastTs) {
                    try {
                      const parsed = new Date(lastTs.replace("Z", "+00:00") || lastTs);
                      age = (Date.now() - parsed.getTime()) / 1000;
                      if (age < 60) ageDisplay = `${Math.round(age)}s ago`;
                      else if (age < 3600) ageDisplay = `${Math.round(age / 60)}m ago`;
                      else ageDisplay = `${Math.round(age / 3600)}h ago`;
                    } catch { /* keep — */ }
                  }
                  const ageColor = age === null ? "text-gray-500" :
                    age < 15 ? "text-green-400" :
                    age < 60 ? "text-yellow-400" : "text-red-400";
                  return (
                    <div className="flex items-center gap-2 mb-3 text-xs">
                      <span className="text-gray-500">Last packet:</span>
                      <span className={`font-mono ${ageColor}`}>{ageDisplay}</span>
                      {age !== null && age > 60 && (
                        <span className="text-red-400/70">⚠ Device may be offline</span>
                      )}
                    </div>
                  );
                })()}

                <div className="grid grid-cols-6 gap-4">
                  {(() => {
                    const last = hardwareHistory[hardwareHistory.length - 1];
                    const sd = last?.sensor_data || {};
                    const lastTs = last?.timestamp;
                    let packetAge: number | null = null;
                    if (lastTs) {
                      try {
                        const parsed = new Date(lastTs.replace("Z", "+00:00") || lastTs);
                        packetAge = (Date.now() - parsed.getTime()) / 1000;
                      } catch { /* ignore */ }
                    }

                    // Absolute limits from validator.py
                    const limits: Record<string, [number, number]> = {
                      air_temp: [-20, 70], humidity: [0, 100], soil_temp: [-10, 60],
                      soil_moisture: [0, 100], light: [0, 200000], leaf_temp: [-20, 75],
                    };
                    const sensorLabels: Record<string, string> = {
                      air_temp: "Air Temp", humidity: "Humidity", soil_temp: "Soil Temp",
                      soil_moisture: "Soil Moisture", light: "Light", leaf_temp: "Leaf Temp",
                    };
                    const sensorUnits: Record<string, string> = {
                      air_temp: "°C", humidity: "%", soil_temp: "°C",
                      soil_moisture: "%", light: " lux", leaf_temp: "°C",
                    };
                    const sensorDecimals: Record<string, number> = {
                      air_temp: 1, humidity: 1, soil_temp: 1,
                      soil_moisture: 1, light: 0, leaf_temp: 1,
                    };

                    const getSensorStatus = (key: string, value: any): { status: string; color: string; label: string } => {
                      if (value === null || value === undefined) {
                        return { status: "offline", color: "text-red-400", label: "OFFLINE" };
                      }
                      const [low, high] = limits[key] || [-Infinity, Infinity];
                      if (value < low || value > high) {
                        return { status: "invalid", color: "text-orange-400", label: "INVALID" };
                      }
                      if (packetAge !== null && packetAge > 60) {
                        return { status: "stale", color: "text-yellow-400", label: "STALE" };
                      }
                      // Check calibration status
                      const cal = calibrationData?.sensors?.[key];
                      if (cal && cal.status !== "calibrated") {
                        return { status: "uncalibrated", color: "text-blue-400", label: "UNCAL" };
                      }
                      return { status: "online", color: "text-green-400", label: "ONLINE" };
                    };

                    return Object.entries(sensorLabels).map(([key, label]) => {
                      const value = sd[key];
                      const { status, color, label: statusLabel } = getSensorStatus(key, value);
                      const decimals = sensorDecimals[key] ?? 1;
                      const unit = sensorUnits[key] || "";
                      const displayValue = value != null ? `${value.toFixed(decimals)}${unit}` : "—";

                      return (
                        <div key={key} className={`bg-black/20 rounded-xl p-3 border-l-2 ${
                          status === "online" ? "border-green-500/50" :
                          status === "stale" ? "border-yellow-500/50" :
                          status === "invalid" ? "border-orange-500/50" :
                          status === "uncalibrated" ? "border-blue-500/50" :
                          "border-red-500/50"
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-gray-400 text-xs">{label}</span>
                            <span className={`text-[10px] font-bold uppercase ${color}`}>
                              {statusLabel}
                            </span>
                          </div>
                          <p className={`text-white ${status === "offline" ? "text-gray-600" : ""}`}>
                            {displayValue}
                          </p>
                        </div>
                      );
                    });
                  })()}
                </div>
              </>
            )}

            {/* Packet Count + Device ID */}
            <div className="mt-4 flex items-center justify-between text-gray-500 text-xs">
              <span>
                Total packets: {hardwareHistory.length}
                {deviceStatus?.packet_count != null && ` (server: ${deviceStatus.packet_count})`}
              </span>
              {deviceStatus?.device_id && (
                <span className="font-mono text-purple-400">
                  🆔 {deviceStatus.device_id}
                </span>
              )}
            </div>
            </>)}
          </div>
        )}

        {/* ============================================================ */}
        {/* HARDWARE CALIBRATION PANEL */}
        {/* ============================================================ */}
        {operatingMode === "hardware" && calibrationData && (
          <div className="bg-white/5 backdrop-blur-xl border border-purple-500/20 rounded-3xl p-6 mb-8">
            <h2 className="text-2xl text-purple-300 mb-4">📐 Sensor Calibration</h2>
            <div className="grid grid-cols-6 gap-4">
              {["air_temp", "humidity", "soil_temp", "soil_moisture", "light", "leaf_temp"].map((sensor) => {
                const cal = calibrationData?.sensors?.[sensor] || { offset: 0, scale_factor: 1, status: "none" };
                const sensorLabels: Record<string, string> = {
                  air_temp: "Air Temp", humidity: "Humidity", soil_temp: "Soil Temp",
                  soil_moisture: "Soil Moisture", light: "Light", leaf_temp: "Leaf Temp"
                };
                const sensorUnits: Record<string, string> = {
                  air_temp: "°C", humidity: "%", soil_temp: "°C",
                  soil_moisture: "%", light: "lux", leaf_temp: "°C"
                };
                return (
                  <div key={sensor} className="bg-black/20 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-400 text-xs">{sensorLabels[sensor]}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        cal.status === "calibrated" ? "bg-green-500/20 text-green-400" :
                        cal.status === "none" ? "bg-gray-500/20 text-gray-400" : "bg-yellow-500/20 text-yellow-400"
                      }`}>
                        {cal.status || "none"}
                      </span>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Offset</span>
                        <span className="text-white">{cal.offset?.toFixed(2) || "0.00"} {sensorUnits[sensor]}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Scale</span>
                        <span className="text-white">{cal.scale_factor?.toFixed(3) || "1.000"}×</span>
                      </div>
                      {cal.calibrated_at && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Calibrated</span>
                          <span className="text-white text-[10px]">{cal.calibrated_at}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 mt-2">
                      <button
                        onClick={() => {
                          const offset = parseFloat(prompt(`Offset for ${sensorLabels[sensor]} (${sensorUnits[sensor]}):`, "0") || "0");
                          const scale = parseFloat(prompt(`Scale factor for ${sensorLabels[sensor]}:`, "1") || "1");
                          if (!isNaN(offset) && !isNaN(scale)) {
                            setCalibration("ALETHEIA-ESP32-001", sensor, offset, scale);
                          }
                        }}
                        className="bg-purple-600/50 hover:bg-purple-500 text-xs rounded-lg px-2 py-1 transition flex-1"
                      >
                        Set
                      </button>
                      <button
                        onClick={() => resetCalibration("ALETHEIA-ESP32-001", sensor)}
                        className="bg-red-600/30 hover:bg-red-500/50 text-xs rounded-lg px-2 py-1 transition"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* PLANT SELECTION */}
        {/* ============================================================ */}
        <div className="grid grid-cols-5 gap-4 mb-8">
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedPlant(e.target.value);
            }}
            placeholder="Search plant..."
            className="bg-white/5 border border-white/10 rounded-xl px-4 py-3"
          />

          <select
            value={growthStage}
            onChange={(e) => setGrowthStage(e.target.value)}
            className="bg-white/5 rounded-xl px-4 py-3"
          >
            <option>germination</option>
            <option>seedling</option>
            <option>vegetative</option>
            <option>flowering</option>
            <option>fruiting</option>
          </select>

          <select
            value={phase}
            onChange={(e) => setPhase(e.target.value)}
            className="bg-white/5 rounded-xl px-4 py-3"
          >
            <option>day</option>
            <option>night</option>
          </select>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 mb-8">
            <p className="text-red-400">Error: {error}</p>
          </div>
        )}

        {data && (
          <>
            {/* ============================================================ */}
            {/* HERO — Digital Twin Core */}
            {/* ============================================================ */}
            <div className="grid grid-cols-12 gap-6 mb-8">
              <div className="col-span-3 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
                <h2 className="text-2xl mb-4">Plant Intelligence</h2>
                <p className="mb-2">Plant: {data.plant}</p>
                <p className="mb-2">Stage: {data.stage}</p>
                <p className="mb-2">Phase: {data.phase}</p>
                <p className="text-green-400 mt-4">
                  System Status: Operational
                </p>
              </div>

              <div className="col-span-6 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 flex flex-col items-center">
                <h2 className="text-3xl mb-6">Digital Twin Core</h2>

                <div className="relative flex items-center justify-center">
                  <div className="absolute w-[350px] h-[350px] rounded-full border border-green-500/20 animate-spin" />
                  <div className="absolute w-[300px] h-[300px] rounded-full border border-blue-500/20 animate-pulse" />

                  <div
                    className={`w-72 h-72 rounded-full bg-gradient-to-br ${healthColor(
                      biology?.health_score || 0
                    )} animate-pulse flex items-center justify-center shadow-2xl`}
                  >
                    <div className="w-56 h-56 rounded-full bg-black/80 flex flex-col items-center justify-center">
                      <p className="text-gray-400">Health Score</p>
                      <p className="text-7xl font-bold">
                        {biology?.health_score}
                      </p>
                    </div>
                  </div>
                </div>

                <p className="mt-8 text-3xl font-bold capitalize">
                  {stress?.prediction || "Analyzing..."}
                </p>
              </div>

              <div className="col-span-3 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
                <h2 className="text-2xl mb-4">AI Brain</h2>

                <div className="space-y-4">
                  <div>
                    <p className="text-gray-400">Confidence</p>
                    <p className="text-2xl">{confidence?.overall}%</p>
                  </div>

                  <div>
                    <p className="text-gray-400">Risk State</p>
                    <p className="text-2xl text-yellow-400">
                      {stress?.risk_state}
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-400">Severity</p>
                    <p className="text-2xl text-red-400">
                      {stress?.severity}
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-400">Future Prediction</p>
                    <p className="text-lg text-red-300">
                      {temporal?.future_state?.future_prediction || "N/A"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* CAUSAL CHAIN — Explainability */}
            {/* ============================================================ */}
            {causalChain.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
                <h2 className="text-3xl mb-6">Causal Chain — Why This Prediction?</h2>
                <p className="text-gray-400 mb-4">
                  Each step shows how one variable influenced another, forming the chain
                  that led to the current AI prediction.
                </p>

                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {causalChain.map((link: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-black/20 rounded-xl p-3 flex items-center gap-3"
                    >
                      <span className="text-gray-500 w-8 text-right">{idx + 1}.</span>
                      <span className="text-blue-300 w-32 truncate">{link.from}</span>
                      <span className="text-gray-500">→</span>
                      <span className="text-green-300 w-32 truncate">{link.to}</span>
                      <span
                        className={`ml-auto font-mono text-sm ${
                          link.direction === "increase" ? "text-red-300" :
                          link.direction === "decrease" ? "text-blue-300" :
                          "text-gray-500"
                        }`}
                      >
                        {link.direction === "increase" ? "+" :
                         link.direction === "decrease" ? "" : ""}{link.delta}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ============================================================ */}
            {/* SENSOR INTELLIGENCE */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Sensor Intelligence</h2>

              <div className="grid grid-cols-2 gap-6">
                {sensor &&
                  Object.entries(sensor)
                    .filter(([key]) =>
                      ["air_temp", "humidity", "light", "leaf_temp", "soil_moisture", "soil_temp", "air_temp_rate", "humidity_rate", "leaf_temp_rate", "leaf_temp_delta"].includes(key)
                    )
                    .map(([key, value]: any) => (
                      <div key={key} className="bg-black/20 rounded-2xl p-5">
                        <div className="flex justify-between mb-3">
                          <span>{metricName(key)}</span>
                          <span>{typeof value === "number" ? value.toFixed(1) : value}</span>
                        </div>

                        <div className="w-full h-3 bg-gray-800 rounded-full">
                          <div
                            className="h-3 bg-green-400 rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(Math.abs(value) * 2, 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
              </div>
            </div>

            {/* ============================================================ */}
            {/* TEMPORAL AI ENGINE — Time-Navigable Historical + Future View */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              {/* ---- Temporal Indicator Bar ---- */}
              <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4">
                  <h2 className="text-3xl">Temporal AI Engine</h2>
                  {/* LIVE / HISTORICAL / FORECAST badge */}
                  <span
                    className={`px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider ${
                      temporalViewMode === "live"
                        ? "bg-green-500/20 text-green-400 border border-green-500/50 animate-pulse"
                        : temporalViewMode === "historical"
                        ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/50"
                        : "bg-purple-500/20 text-purple-400 border border-purple-500/50"
                    }`}
                  >
                    {temporalViewMode === "live" && "● LIVE"}
                    {temporalViewMode === "historical" && "◷ HISTORICAL"}
                  </span>
                </div>

                {/* Current displayed time with timezone */}
                <div className="text-right">
                  <p className="text-gray-400 text-xs uppercase tracking-wider">Viewing Time (IST)</p>
                  <p className="text-xl font-mono text-white">
                    {selectedTime !== null
                      ? (replayData?.target?.sim_time || `Min ${selectedTime}`)
                      : currentSimTime}
                    <span className="text-gray-500 text-sm ml-1">IST</span>
                  </p>
                  {selectedTime !== null && (
                    <p className="text-xs text-yellow-400 mt-1">
                      Viewing historical state — data shown as it was at this moment
                    </p>
                  )}
                </div>
              </div>

              {/* ---- Time Navigation Bar ---- */}
              <div className="flex flex-wrap items-center gap-2 mb-6 p-4 bg-black/30 rounded-2xl border border-white/5">
                {/* Time range selector */}
                <select
                  value={temporalRange}
                  onChange={(e) => {
                    setTemporalRange(e.target.value);
                    if (temporalViewMode === "live") {
                      fetchTemporalHistory(e.target.value);
                    }
                  }}
                  className="bg-black/40 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white"
                >
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="all">All History</option>
                </select>

                <div className="h-6 w-px bg-gray-700 mx-1" />

                {/* Quick-jump buttons */}
                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 1440))}
                  disabled={effectiveNowMinute < 1440}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                  title="Jump back 24 hours"
                >
                  ◀◀ 24H
                </button>
                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 120))}
                  disabled={effectiveNowMinute < 120}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                  title="Jump back 2 hours"
                >
                  ◀ 2H
                </button>
                <button
                  onClick={() => jumpToTime(Math.max(0, effectiveNowMinute - 30))}
                  disabled={effectiveNowMinute < 30}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                  title="Jump back 30 minutes"
                >
                  ◀ 30m
                </button>

                {/* NOW button */}
                <button
                  onClick={returnToLive}
                  className={`px-4 py-1.5 text-xs font-bold rounded-lg transition ${
                    temporalViewMode === "live"
                      ? "bg-green-600 text-white cursor-default"
                      : "bg-yellow-600 hover:bg-yellow-500 text-white"
                  }`}
                  title="Return to live / current time"
                >
                  ● NOW
                </button>

                <button
                  onClick={() => jumpToTime(Math.min(currentSimMinute, effectiveNowMinute + 30))}
                  disabled={effectiveNowMinute >= currentSimMinute}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                  title="Jump forward 30 minutes"
                >
                  30m ▶
                </button>
                <button
                  onClick={() => jumpToTime(Math.min(currentSimMinute, effectiveNowMinute + 120))}
                  disabled={effectiveNowMinute >= currentSimMinute}
                  className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/50 hover:bg-gray-600 text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition"
                  title="Jump forward 2 hours"
                >
                  2H ▶
                </button>

                {/* Return to Live — prominent when viewing history */}
                {temporalViewMode !== "live" && (
                  <button
                    onClick={returnToLive}
                    className="ml-auto px-5 py-2 text-sm font-bold bg-green-600 hover:bg-green-500 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-green-600/20"
                  >
                    <span>⟳</span> Return to Live
                  </button>
                )}
              </div>

              {/* ---- Stat Cards ---- */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400 text-sm">Past → Now Trend</p>
                  <p className="text-lg mt-2 font-mono text-green-300">
                    {pastTrend}
                  </p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400 text-sm">Velocity</p>
                  <p className="text-3xl mt-2 text-yellow-400">
                    {typeof tempVelocity === "number"
                      ? `${tempVelocity > 0 ? "+" : ""}${tempVelocity.toFixed(2)}°C/min`
                      : tempVelocity}
                  </p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400 text-sm">Future Risk</p>
                  <p className="text-lg mt-2 text-red-300">
                    {temporal?.future_state?.future_prediction || "N/A"}
                  </p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400 text-sm">Temporal Confidence</p>
                  <p className="text-3xl mt-2 text-blue-300">
                    {temporal?.future_state?.future_confidence != null
                      ? `${Number(temporal.future_state.future_confidence).toFixed(0)}%`
                      : "—"}
                  </p>
                </div>
              </div>

              {/* ---- Data availability notice ---- */}
              {temporalSeries && (
                <div className="text-xs text-gray-500 mb-4 flex items-center gap-2">
                  <span>●</span>
                  <span>
                    Showing {fullChartData.filter(d => d.type === "past").length} historical points
                    {temporalViewMode === "live" && futurePrediction.length > 0 && (
                      <> + {futurePrediction.length} forecast points</>
                    )}
                    {temporalViewMode === "historical" && pastAfterNow.length > 0 && (
                      <> (data after selected time shown for context)</>
                    )}
                  </span>
                </div>
              )}

              {/* ---- Full Trajectory Chart: Past (solid) + NOW (marker) + Future (dashed + confidence bands) ---- */}
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={fullChartData}>
                  <CartesianGrid stroke="#333" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "#888", fontSize: 11 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fill: "#888", fontSize: 11 }} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const dataPoint = payload[0]?.payload;
                      const dataType = dataPoint?._dataType || "observed";
                      const dataTypeLabel =
                        dataType === "observed" ? "Observed" :
                        dataType === "forecast" ? "AI Forecast" :
                        dataType === "estimated" ? "Estimated" : dataType;
                      const dataTypeColor =
                        dataType === "observed" ? "#00ff99" :
                        dataType === "forecast" ? "#ff6600" :
                        dataType === "estimated" ? "#ffcc00" : "#888";
                      return (
                        <div
                          style={{
                            backgroundColor: "#111",
                            border: "1px solid #333",
                            borderRadius: "12px",
                            padding: "12px 16px",
                            minWidth: "200px",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ color: "#fff", fontWeight: "bold", fontSize: "14px" }}>
                              {label}
                            </span>
                            <span style={{ color: dataTypeColor, fontSize: "11px", fontWeight: "bold" }}>
                              {dataTypeLabel}
                            </span>
                          </div>
                          <div style={{ color: "#888", fontSize: "11px", marginBottom: "6px" }}>
                            Sim Minute: {dataPoint?.minute} · IST (UTC+5:30)
                          </div>
                          {payload.map((entry: any, idx: number) => (
                            <div
                              key={idx}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                color: entry.color || "#fff",
                                fontSize: "13px",
                                padding: "2px 0",
                              }}
                            >
                              <span>{entry.name}</span>
                              <span style={{ fontWeight: "bold" }}>
                                {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      );
                    }}
                  />
                  <Legend />

                  {/* Past air_temp — solid green (observed data) */}
                  <Line
                    type="monotone"
                    dataKey="air_temp"
                    stroke="#00ff99"
                    strokeWidth={2}
                    dot={false}
                    name="Air Temp (°C)"
                    connectNulls
                  />

                  {/* Past humidity — solid blue */}
                  <Line
                    type="monotone"
                    dataKey="humidity"
                    stroke="#3399ff"
                    strokeWidth={2}
                    dot={false}
                    name="Humidity (%)"
                    connectNulls
                  />

                  {/* NOW marker — vertical reference line */}
                  <ReferenceLine
                    x={nowEntry.label}
                    stroke="#ffcc00"
                    strokeWidth={2}
                    strokeDasharray="6 6"
                    label={{
                      value: selectedTime !== null ? "VIEWING" : "NOW",
                      position: "top",
                      fill: "#ffcc00",
                      fontSize: 12,
                      fontWeight: "bold",
                    }}
                  />

                  {/* Future confidence band upper (air_temp) — dashed orange */}
                  <Line
                    type="monotone"
                    dataKey="ci_upper_temp"
                    stroke="#ff6600"
                    strokeWidth={1}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Temp Upper CI"
                    connectNulls
                  />

                  {/* Future confidence band lower (air_temp) — dashed orange */}
                  <Line
                    type="monotone"
                    dataKey="ci_lower_temp"
                    stroke="#ff6600"
                    strokeWidth={1}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Temp Lower CI"
                    connectNulls
                  />

                  {/* Soil moisture — solid amber */}
                  <Line
                    type="monotone"
                    dataKey="soil_moisture"
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    dot={false}
                    name="Soil Moisture (%)"
                    connectNulls
                  />

                  {/* Leaf temp delta — solid cyan */}
                  <Line
                    type="monotone"
                    dataKey="leaf_temp_delta"
                    stroke="#06b6d4"
                    strokeWidth={1.5}
                    dot={false}
                    name="Leaf ΔT (°C)"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>

              {/* ---- Explainable AI ---- */}
              <div className="mt-6 bg-black/20 rounded-2xl p-6">
                <h3 className="text-xl mb-4">AI Reasoning</h3>

                {stress?.reasons?.map((reason: string, idx: number) => (
                  <p key={idx} className="text-yellow-300 mb-2">
                    • {reason}
                  </p>
                ))}
              </div>
            </div>

            {/* ============================================================ */}
            {/* BIOLOGY ENGINE */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Biology Deviation Engine</h2>

              <div className="grid grid-cols-2 gap-6">
                {biology?.analysis &&
                  Object.entries(biology.analysis).map(([key, value]: any) => {
                    const low = value.optimal_range[0];
                    const high = value.optimal_range[1];
                    const deviation =
                      value.value < low
                        ? low - value.value
                        : value.value > high
                        ? value.value - high
                        : 0;

                    return (
                      <div key={key} className="bg-black/20 rounded-2xl p-6">
                        <h3 className="text-xl mb-4">{metricName(key)}</h3>

                        <div className="w-full h-3 bg-gray-800 rounded-full mb-4">
                          <div
                            className={`h-3 rounded-full transition-all duration-500 ${
                              value.status === "optimal"
                                ? "bg-green-500"
                                : "bg-red-500"
                            }`}
                            style={{
                              width: `${Math.min(
                                (value.value / (high + 20)) * 100,
                                100
                              )}%`,
                            }}
                          />
                        </div>

                        <p>Current: {value.value}</p>
                        <p>
                          Optimal: {low} — {high}
                        </p>

                        <p
                          className={
                            value.status === "optimal"
                              ? "text-green-400 mt-3"
                              : "text-red-400 mt-3"
                          }
                        >
                          Status: {value.status}
                        </p>

                        <p className="text-yellow-400 mt-2">
                          Deviation: {deviation}
                        </p>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* ============================================================ */}
            {/* GROWTH + DAY/NIGHT */}
            {/* ============================================================ */}
            <div className="grid grid-cols-2 gap-6 mb-8">
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8">
                <h2 className="text-3xl mb-6">Growth Intelligence</h2>

                {stageProfile &&
                  Object.entries(stageProfile).map(([key, value]: any) => (
                    <div key={key} className="mb-4 bg-black/20 rounded-xl p-4">
                      <span className="font-semibold">{metricName(key)}</span>
                      <p>
                        {value[0]} — {value[1]}
                      </p>
                    </div>
                  ))}
              </div>

              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8">
                <h2 className="text-3xl mb-6">Day vs Night Biology</h2>

                <div className="mb-6">
                  <h3 className="text-yellow-400 mb-3">Day Profile</h3>
                  {plantProfile?.day_profile &&
                    Object.entries(plantProfile.day_profile)
                      .slice(0, 4)
                      .map(([key, value]: any) => (
                        <div key={key} className="mb-2">
                          {metricName(key)}: {value[0]} — {value[1]}
                        </div>
                      ))}
                </div>

                <div>
                  <h3 className="text-blue-400 mb-3">Night Profile</h3>
                  {plantProfile?.night_profile &&
                    Object.entries(plantProfile.night_profile)
                      .slice(0, 4)
                      .map(([key, value]: any) => (
                        <div key={key} className="mb-2">
                          {metricName(key)}: {value[0]} — {value[1]}
                        </div>
                      ))}
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* LIVE STRESS RADAR */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-3xl">Live Stress Radar</h2>
                <span className={`px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider ${
                  stress?.risk_state === "healthy" ? "bg-green-500/20 text-green-400 border border-green-500/50" :
                  stress?.risk_state === "early_warning" ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/50" :
                  stress?.risk_state === "stress" ? "bg-orange-500/20 text-orange-400 border border-orange-500/50" :
                  "bg-red-500/20 text-red-400 border border-red-500/50"
                }`}>
                  {stress?.prediction || "Analyzing"} · Severity {stress?.severity || "—"}/100
                </span>
              </div>

              <ResponsiveContainer width="100%" height={400}>
                <RadarChart
                  data={[
                    {
                      metric: "Heat Stress",
                      value: Math.min(Math.max(
                        ((sensor?.air_temp || 25) - 20) / 20 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                    {
                      metric: "Humidity Deficit",
                      value: Math.min(Math.max(
                        (70 - (sensor?.humidity || 60)) / 50 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                    {
                      metric: "Leaf ΔT Risk",
                      value: Math.min(Math.max(
                        (sensor?.leaf_temp_delta || 2) / 8 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                    {
                      metric: "Root Zone",
                      value: Math.min(Math.max(
                        ((sensor?.soil_temp || 22) - 18) / 20 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                    {
                      metric: "Water Stress",
                      value: Math.min(Math.max(
                        (60 - (sensor?.soil_moisture || 50)) / 40 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                    {
                      metric: "Light Intensity",
                      value: Math.min(Math.max(
                        ((sensor?.light || 30000) - 5000) / 80000 * 100, 0
                      ), 100),
                      fullMark: 100,
                    },
                  ]}
                >
                  <PolarGrid stroke="#333" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fill: "#888", fontSize: 11 }}
                  />
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 100]}
                    tick={{ fill: "#555", fontSize: 9 }}
                  />
                  <Radar
                    dataKey="value"
                    stroke="#00ff99"
                    fill="#00ff99"
                    fillOpacity={0.35}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>

              {/* Stress reasons from AI */}
              {stress?.reasons && stress.reasons.length > 0 && (
                <div className="mt-6 bg-black/20 rounded-2xl p-5">
                  <h3 className="text-sm text-gray-400 mb-3">AI Stress Factors</h3>
                  <div className="space-y-2">
                    {stress.reasons.map((reason: string, idx: number) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className="text-yellow-400 mt-0.5">•</span>
                        <span className="text-gray-300">{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ============================================================ */}
            {/* TEMPORAL REPLAY — Navigate through historical states */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-2">Temporal Replay</h2>
              <p className="text-gray-400 text-sm mb-6">
                Navigate through the simulation history. Drag the slider to inspect
                sensor readings, plant state, and AI predictions at any past moment.
                The Temporal AI graph above will sync to the selected time.
              </p>

              {/* Replay Slider — synced with selectedTime */}
              <div className="mb-6">
                <label className="text-gray-400 text-sm mb-2 block">
                  Sim Minute: {selectedTime ?? currentSimMinute}
                  {selectedTime !== null && (
                    <span className="text-yellow-400 ml-2">(Historical View)</span>
                  )}
                </label>
                <input
                  type="range"
                  min={0}
                  max={currentSimMinute || 1439}
                  value={selectedTime ?? currentSimMinute ?? 0}
                  onChange={(e) => {
                    const v = parseInt(e.target.value);
                    setReplayMinute(v);
                  }}
                  onMouseUp={() => {
                    if (replayMinute !== null) {
                      jumpToTime(replayMinute);
                    }
                  }}
                  onTouchEnd={() => {
                    if (replayMinute !== null) {
                      jumpToTime(replayMinute);
                    }
                  }}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                    accent-green-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>00:00</span>
                  <span>{simState?.sim_time || "12:00"}</span>
                  <span>23:59</span>
                </div>
              </div>

              {/* Return to Live button for replay section */}
              {selectedTime !== null && (
                <div className="mb-6">
                  <button
                    onClick={returnToLive}
                    className="px-5 py-2 text-sm font-bold bg-green-600 hover:bg-green-500 rounded-xl transition-all flex items-center gap-2"
                  >
                    <span>⟳</span> Return to Live
                  </button>
                </div>
              )}

              {/* Replay Result */}
              {replayLoading && (
                <div className="text-center text-gray-400 py-4">Loading replay state...</div>
              )}

              {replayData && !replayLoading && (
                <div className="grid grid-cols-2 gap-4">
                  {/* Target State */}
                  <div className="bg-black/20 rounded-2xl p-5">
                    <h3 className="text-green-400 mb-3">
                      State at {replayData.target?.sim_time || selectedTime}
                    </h3>
                    <div className="space-y-2 text-sm">
                      <p>Air Temp: {replayData.target?.sensor_data?.air_temp?.toFixed(1) || "—"}°C</p>
                      <p>Humidity: {replayData.target?.sensor_data?.humidity?.toFixed(1) || "—"}%</p>
                      <p>Soil Moisture: {replayData.target?.sensor_data?.soil_moisture?.toFixed(1) || "—"}%</p>
                      <p>Leaf ΔT: {replayData.target?.sensor_data?.leaf_temp_delta?.toFixed(1) || "—"}°C</p>
                      <p>Stress: {replayData.target?.plant?.stress?.toFixed(1) || "—"}</p>
                      <p>Growth: {replayData.target?.plant?.growth?.toFixed(3) || "—"}</p>
                    </div>
                  </div>

                  {/* Context Timeline */}
                  <div className="bg-black/20 rounded-2xl p-5">
                    <h3 className="text-blue-400 mb-3">Context (±{replayData.context_window} steps)</h3>
                    <div className="space-y-1 max-h-48 overflow-y-auto text-xs">
                      {replayData.context_before?.map((ctx: any, idx: number) => (
                        <div key={idx} className="text-gray-500 flex justify-between">
                          <span>{ctx.sim_time}</span>
                          <span>{ctx.sensor_data?.air_temp?.toFixed(1)}°C</span>
                        </div>
                      ))}
                      <div className="text-green-400 flex justify-between font-bold py-1 border-y border-green-500/30">
                        <span>{replayData.target?.sim_time} ◀</span>
                        <span>{replayData.target?.sensor_data?.air_temp?.toFixed(1)}°C</span>
                      </div>
                      {replayData.context_after?.map((ctx: any, idx: number) => (
                        <div key={idx} className="text-gray-500 flex justify-between">
                          <span>{ctx.sim_time}</span>
                          <span>{ctx.sensor_data?.air_temp?.toFixed(1)}°C</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {!replayData && !replayLoading && (
                <div className="text-center text-gray-500 py-4 text-sm">
                  Drag the slider and release to load a historical state
                </div>
              )}
            </div>

            {/* ============================================================ */}
            {/* AI REASONING CONSOLE */}
            {/* ============================================================ */}
            {aiReasoning && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-3xl">AI Reasoning Console</h2>
                  {/* Source badge: AI-generated vs Fallback */}
                  <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                    aiReasoning._fallback || aiReasoning._partial
                      ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/50"
                      : "bg-green-500/20 text-green-400 border border-green-500/50"
                  }`}>
                    {aiReasoning._fallback
                      ? "⚡ Fallback (Model Offline)"
                      : aiReasoning._partial
                      ? "⚠ Partial (Truncated)"
                      : "✓ OpenRouter AI"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-black/20 rounded-2xl p-6">
                    <h3 className="text-xl text-green-400 mb-3">Explanation</h3>
                    <p className="text-gray-300">{aiReasoning.explanation}</p>
                  </div>

                  <div className="bg-black/20 rounded-2xl p-6">
                    <h3 className="text-xl text-yellow-400 mb-3">Diagnosis</h3>
                    <p className="text-gray-300">{aiReasoning.diagnosis}</p>
                  </div>

                  <div className="bg-black/20 rounded-2xl p-6 col-span-2">
                    <h3 className="text-xl text-blue-400 mb-3">
                      Confidence Narrative
                    </h3>
                    <p className="text-gray-300">
                      {aiReasoning.confidence_narrative}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ============================================================ */}
            {/* WARNINGS + RECOMMENDATIONS */}
            {/* ============================================================ */}
            <div className="grid grid-cols-2 gap-6 mb-8">
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8">
                <h2 className="text-3xl mb-6">Stress Intelligence</h2>

                {biology?.warnings?.length > 0 ? (
                  biology.warnings.map((warning: string, idx: number) => (
                    <div
                      key={idx}
                      className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-3"
                    >
                      <p className="text-red-300">⚠ {warning}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-green-400">No warnings detected</p>
                )}
              </div>

              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8">
                <h2 className="text-3xl mb-6">Live Recommendations</h2>

                {recommendations?.length > 0 ? (
                  recommendations.map((rec: string, idx: number) => (
                    <div
                      key={idx}
                      className="bg-black/20 rounded-2xl p-4 mb-3"
                    >
                      <p className="text-green-300">
                        {idx + 1}. {rec}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="bg-black/20 rounded-2xl p-6">
                    <p className="text-gray-400">No recommendations available</p>
                  </div>
                )}
              </div>
            </div>

            {/* ============================================================ */}
            {/* CONFIDENCE PANEL — with cold-start awareness */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Prediction Confidence</h2>

              {/* Cold-start warning for hardware mode with insufficient history */}
              {operatingMode === "hardware" && hardwareHistory.length < 5 && (
                <div className="mb-6 bg-yellow-500/10 border border-yellow-500/20 rounded-2xl p-4 flex items-center gap-3">
                  <span className="text-yellow-400 text-xl">⏳</span>
                  <div>
                    <p className="text-yellow-300 font-bold">Temporal AI Warming Up</p>
                    <p className="text-yellow-400/70 text-sm">
                      {hardwareHistory.length === 0
                        ? "No hardware packets received yet. Temporal confidence unavailable until data arrives."
                        : `Only ${hardwareHistory.length} packet(s) received. Need ≥5 for reliable temporal predictions.`}
                    </p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-5 gap-4">
                {/* Sensor Confidence */}
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Sensor</p>
                  <p className={`text-2xl mt-2 ${
                    (confidence?.sensor_confidence ?? 0) >= 80 ? "text-green-400" :
                    (confidence?.sensor_confidence ?? 0) >= 50 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {confidence?.sensor_confidence != null ? `${Number(confidence.sensor_confidence).toFixed(0)}%` : "—"}
                  </p>
                  <p className="text-gray-500 text-[10px] mt-1">HW Validation</p>
                </div>

                {/* AI Model Confidence */}
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">AI Model</p>
                  <p className={`text-2xl mt-2 ${
                    (confidence?.ai_confidence ?? 0) >= 80 ? "text-green-400" :
                    (confidence?.ai_confidence ?? 0) >= 50 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {confidence?.ai_confidence != null ? `${Number(confidence.ai_confidence).toFixed(0)}%` : "—"}
                  </p>
                  <p className="text-gray-500 text-[10px] mt-1">Decision Engine</p>
                </div>

                {/* Temporal Confidence — with cold-start indicator */}
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Temporal</p>
                  <p className={`text-2xl mt-2 ${
                    operatingMode === "hardware" && hardwareHistory.length < 5
                      ? "text-yellow-400"
                      : (confidence?.temporal_confidence ?? 0) >= 80 ? "text-green-400"
                      : (confidence?.temporal_confidence ?? 0) >= 50 ? "text-yellow-400"
                      : "text-red-400"
                  }`}>
                    {operatingMode === "hardware" && hardwareHistory.length < 5
                      ? "Warming"
                      : confidence?.temporal_confidence != null
                      ? `${Number(confidence.temporal_confidence).toFixed(0)}%`
                      : "—"}
                  </p>
                  <p className="text-gray-500 text-[10px] mt-1">
                    {operatingMode === "hardware" && hardwareHistory.length < 5
                      ? "Need ≥5 packets"
                      : "Future Prediction"}
                  </p>
                </div>

                {/* Biology Health Score */}
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Biology</p>
                  <p className={`text-2xl mt-2 ${
                    (confidence?.biology_health_score ?? 0) >= 80 ? "text-green-400" :
                    (confidence?.biology_health_score ?? 0) >= 50 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {confidence?.biology_health_score != null ? `${Number(confidence.biology_health_score).toFixed(0)}%` : "—"}
                  </p>
                  <p className="text-gray-500 text-[10px] mt-1">Plant Health</p>
                </div>

                {/* Overall Confidence */}
                <div className={`bg-black/20 rounded-2xl p-5 text-center border ${
                  (confidence?.overall ?? 0) >= 80 ? "border-green-500/30" :
                  (confidence?.overall ?? 0) >= 50 ? "border-yellow-500/30" : "border-red-500/30"
                }`}>
                  <p className="text-gray-400 text-sm">Overall</p>
                  <p className={`text-3xl mt-2 ${
                    (confidence?.overall ?? 0) >= 80 ? "text-green-400" :
                    (confidence?.overall ?? 0) >= 50 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {confidence?.overall != null ? `${Number(confidence.overall).toFixed(0)}%` : "—"}
                  </p>
                  <p className="text-gray-500 text-[10px] mt-1">Weighted Avg</p>
                </div>
              </div>

              {/* Confidence breakdown weights */}
              <div className="mt-4 text-xs text-gray-500 text-center">
                Weights: Sensor 15% · AI Model 30% · Temporal 25% · Biology 30%
              </div>
            </div>

            {/* ============================================================ */}
            {/* PREDICTION ACCURACY — Rolling accuracy & verification */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-2">Prediction Accuracy</h2>
              <p className="text-gray-400 text-sm mb-6">
                Rolling accuracy of temporal predictions vs actual measurements.
                Each step verifies how well the predicted trajectory matched reality.
              </p>

              {/* Fetch button */}
              {!accuracyData && !accuracyLoading && (
                <button
                  onClick={fetchAccuracy}
                  className="bg-blue-600 hover:bg-blue-500 rounded-xl px-6 py-3 font-bold transition mb-6"
                >
                  Compute Prediction Accuracy
                </button>
              )}

              {accuracyLoading && (
                <div className="text-center text-gray-400 py-4">Computing accuracy across simulation history...</div>
              )}

              {accuracyData && (
                <>
                  {/* Summary Stats */}
                  <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-black/20 rounded-2xl p-5 text-center">
                      <p className="text-gray-400 text-sm">Overall Accuracy</p>
                      <p className={`text-3xl mt-2 ${
                        accuracyData.overall_accuracy >= 90 ? "text-green-400" :
                        accuracyData.overall_accuracy >= 70 ? "text-yellow-400" :
                        "text-red-400"
                      }`}>
                        {accuracyData.overall_accuracy?.toFixed(1)}%
                      </p>
                    </div>
                    <div className="bg-black/20 rounded-2xl p-5 text-center">
                      <p className="text-gray-400 text-sm">Total Verified</p>
                      <p className="text-3xl mt-2 text-blue-300">
                        {accuracyData.total_verified}
                      </p>
                    </div>
                    <div className="bg-black/20 rounded-2xl p-5 text-center">
                      <p className="text-gray-400 text-sm">Window Size</p>
                      <p className="text-3xl mt-2 text-purple-300">
                        {accuracyData.window_size}
                      </p>
                    </div>
                    <div className="bg-black/20 rounded-2xl p-5 text-center">
                      <p className="text-gray-400 text-sm">Method</p>
                      <p className="text-lg mt-2 text-gray-300">
                        Linear Extrapolation
                      </p>
                    </div>
                  </div>

                  {/* Rolling Accuracy Chart */}
                  {accuracyData.rolling_accuracy?.length > 0 && (
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={accuracyData.rolling_accuracy.map((r: any) => ({
                        step: r.step,
                        accuracy: r.accuracy,
                      }))}>
                        <CartesianGrid stroke="#333" strokeDasharray="3 3" />
                        <XAxis dataKey="step" tick={{ fill: "#888", fontSize: 10 }} />
                        <YAxis domain={[0, 100]} tick={{ fill: "#888", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#111",
                            border: "1px solid #333",
                            borderRadius: "12px",
                          }}
                        />
                        <ReferenceLine y={90} stroke="#00ff99" strokeDasharray="4 4" label={{ value: "90%", fill: "#00ff99", fontSize: 10 }} />
                        <ReferenceLine y={70} stroke="#ffcc00" strokeDasharray="4 4" label={{ value: "70%", fill: "#ffcc00", fontSize: 10 }} />
                        <Line
                          type="monotone"
                          dataKey="accuracy"
                          stroke="#3399ff"
                          strokeWidth={2}
                          dot={false}
                          name="Accuracy %"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  )}

                  {/* Verification Details Table */}
                  {accuracyData.verification_details?.length > 0 && (
                    <div className="mt-6 max-h-64 overflow-y-auto">
                      <h3 className="text-lg text-gray-400 mb-3">Verification Details</h3>
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-gray-500 border-b border-gray-700">
                            <th className="text-left py-2">Step</th>
                            <th className="text-left py-2">Variable</th>
                            <th className="text-right py-2">Predicted</th>
                            <th className="text-right py-2">Actual</th>
                            <th className="text-right py-2">Error %</th>
                            <th className="text-right py-2">Accuracy</th>
                          </tr>
                        </thead>
                        <tbody>
                          {accuracyData.verification_details.slice(-20).map((v: any, idx: number) => (
                            <tr key={idx} className="border-b border-gray-800">
                              <td className="py-1 text-gray-500">{v.step}</td>
                              <td className="py-1 text-gray-300">{v.variable}</td>
                              <td className="py-1 text-right text-blue-300">{v.predicted?.toFixed(2)}</td>
                              <td className="py-1 text-right text-green-300">{v.actual?.toFixed(2)}</td>
                              <td className={`py-1 text-right ${
                                v.error_pct > 10 ? "text-red-400" :
                                v.error_pct > 5 ? "text-yellow-400" :
                                "text-green-400"
                              }`}>
                                {v.error_pct?.toFixed(1)}%
                              </td>
                              <td className={`py-1 text-right font-bold ${
                                v.accuracy >= 90 ? "text-green-400" :
                                v.accuracy >= 70 ? "text-yellow-400" :
                                "text-red-400"
                              }`}>
                                {v.accuracy?.toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* ============================================================ */}
            {/* COMPARISON MODE — Prediction vs Actual at any historical point */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-2">Comparison Mode</h2>
              <p className="text-gray-400 text-sm mb-6">
                Select any historical prediction snapshot and compare what Aletheia
                predicted with what actually happened at that future time.
                <br />
                <span className="text-green-400">
                  Prediction → Actual → Error → Reason
                </span>
              </p>

              {/* Load Snapshots Button */}
              {snapshotList.length === 0 && (
                <button
                  onClick={fetchSnapshots}
                  className="bg-purple-600 hover:bg-purple-500 rounded-xl px-6 py-3 font-bold transition mb-6"
                >
                  Load Historical Snapshots
                </button>
              )}

              {/* Snapshot Selector */}
              {snapshotList.length > 0 && (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">
                        Prediction Snapshot (when Aletheia made the prediction)
                      </label>
                      <select
                        value={snapshotMinute ?? ""}
                        onChange={(e) => {
                          const v = parseInt(e.target.value);
                          setSnapshotMinute(v);
                          // Auto-set compare minute to snapshot + 30
                          setCompareMinute(v + 30);
                        }}
                        className="w-full bg-black/30 border border-gray-600 rounded-xl px-4 py-3 text-white"
                      >
                        <option value="">Select a snapshot...</option>
                        {snapshotList.map((s: any) => (
                          <option key={s.sim_minute} value={s.sim_minute}>
                            {s.sim_time} (min {s.sim_minute}) — Temporal:{" "}
                            {s.temporal_prediction?.future_state?.future_prediction || "N/A"}
                            {" | "}Stress: {s.stress_analysis?.prediction || "N/A"}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-gray-400 text-sm mb-2 block">
                        Compare Against (when to check what actually happened)
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={compareMinute ?? ""}
                          onChange={(e) => setCompareMinute(parseInt(e.target.value) || null)}
                          className="flex-1 bg-black/30 border border-gray-600 rounded-xl px-4 py-3 text-white"
                          placeholder="e.g. 755"
                        />
                        <button
                          onClick={() => {
                            if (snapshotMinute !== null && compareMinute !== null) {
                              fetchCompare(snapshotMinute, compareMinute);
                            }
                          }}
                          disabled={snapshotMinute === null || compareMinute === null || compareLoading}
                          className="bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl px-6 py-3 font-bold transition"
                        >
                          {compareLoading ? "Comparing..." : "Compare"}
                        </button>
                      </div>
                      {/* Quick offset buttons */}
                      <div className="flex gap-2 mt-2">
                        {[5, 10, 15, 20, 30, 60].map((offset) => (
                          <button
                            key={offset}
                            onClick={() => {
                              if (snapshotMinute !== null) {
                                const cmp = snapshotMinute + offset;
                                setCompareMinute(cmp);
                                fetchCompare(snapshotMinute, cmp);
                              }
                            }}
                            disabled={snapshotMinute === null}
                            className="bg-black/30 hover:bg-purple-600/50 border border-gray-600 rounded-lg px-3 py-1 text-xs text-gray-300 transition"
                          >
                            +{offset}m
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Comparison Results */}
                  {compareData && !compareLoading && (
                    <div className="space-y-6">
                      {/* Verdict Banner */}
                      <div
                        className={`rounded-2xl p-6 text-center ${
                          compareData.comparison?.prediction_correct
                            ? "bg-green-500/10 border border-green-500/30"
                            : "bg-red-500/10 border border-red-500/30"
                        }`}
                      >
                        <p className="text-2xl font-bold">
                          {compareData.comparison?.prediction_correct ? (
                            <span className="text-green-400">✓ Prediction CORRECT</span>
                          ) : (
                            <span className="text-red-400">✗ Prediction INCORRECT</span>
                          )}
                        </p>
                        <p className="text-gray-400 mt-2">
                          At {compareData.snapshot?.sim_time}, Aletheia predicted{" "}
                          <span className="text-blue-300 font-bold">
                            {compareData.comparison?.predicted_label}
                          </span>
                          {" → "}
                          At {compareData.actual?.sim_time} (
                          {compareData.comparison?.time_delta_minutes}m later), reality was{" "}
                          <span className="text-yellow-300 font-bold">
                            {compareData.comparison?.actual_label}
                          </span>
                        </p>
                        <p className="text-3xl mt-3 font-bold">
                          Overall Accuracy:{" "}
                          <span
                            className={
                              (compareData.comparison?.overall_accuracy ?? 0) >= 90
                                ? "text-green-400"
                                : (compareData.comparison?.overall_accuracy ?? 0) >= 70
                                ? "text-yellow-400"
                                : "text-red-400"
                            }
                          >
                            {compareData.comparison?.overall_accuracy?.toFixed(1)}%
                          </span>
                        </p>
                      </div>

                      {/* Per-Variable Comparison Table */}
                      <div className="bg-black/20 rounded-2xl p-6">
                        <h3 className="text-lg text-gray-300 mb-4">
                          Variable-by-Variable Comparison
                        </h3>
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-gray-500 border-b border-gray-700">
                              <th className="text-left py-2">Variable</th>
                              <th className="text-right py-2">Predicted</th>
                              <th className="text-right py-2">Actual</th>
                              <th className="text-right py-2">Error</th>
                              <th className="text-right py-2">Error %</th>
                              <th className="text-right py-2">Accuracy</th>
                            </tr>
                          </thead>
                          <tbody>
                            {compareData.comparison?.variables?.map((v: any, idx: number) => (
                              <tr key={idx} className="border-b border-gray-800">
                                <td className="py-2 text-gray-300 font-medium">
                                  {v.variable.replaceAll("_", " ").toUpperCase()}
                                </td>
                                <td className="py-2 text-right text-blue-300">
                                  {v.predicted?.toFixed(2)}
                                </td>
                                <td className="py-2 text-right text-green-300">
                                  {v.actual?.toFixed(2)}
                                </td>
                                <td className="py-2 text-right text-gray-400">
                                  {v.error?.toFixed(2)}
                                </td>
                                <td
                                  className={`py-2 text-right ${
                                    v.error_pct > 10
                                      ? "text-red-400"
                                      : v.error_pct > 5
                                      ? "text-yellow-400"
                                      : "text-green-400"
                                  }`}
                                >
                                  {v.error_pct?.toFixed(1)}%
                                </td>
                                <td
                                  className={`py-2 text-right font-bold ${
                                    v.accuracy >= 90
                                      ? "text-green-400"
                                      : v.accuracy >= 70
                                      ? "text-yellow-400"
                                      : "text-red-400"
                                  }`}
                                >
                                  {v.accuracy?.toFixed(1)}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Snapshot Context */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-black/20 rounded-2xl p-5">
                          <h3 className="text-blue-400 mb-3">
                            Snapshot at {compareData.snapshot?.sim_time}
                          </h3>
                          <div className="space-y-1 text-xs text-gray-400">
                            <p>
                              Temporal:{" "}
                              <span className="text-blue-300">
                                {compareData.snapshot?.temporal_prediction?.future_state?.future_prediction || "N/A"}
                              </span>
                            </p>
                            <p>
                              Stress:{" "}
                              <span className="text-red-300">
                                {compareData.snapshot?.stress_analysis?.prediction || "N/A"}
                              </span>
                            </p>
                            <p>
                              Confidence:{" "}
                              {compareData.snapshot?.stress_analysis?.confidence || "N/A"}%
                            </p>
                            <p>
                              Recommendations:{" "}
                              {compareData.snapshot?.recommendations?.length || 0} items
                            </p>
                          </div>
                        </div>
                        <div className="bg-black/20 rounded-2xl p-5">
                          <h3 className="text-green-400 mb-3">
                            Actual at {compareData.actual?.sim_time}
                          </h3>
                          <div className="space-y-1 text-xs text-gray-400">
                            <p>
                              Air Temp:{" "}
                              <span className="text-white">
                                {compareData.actual?.sensor_data?.air_temp?.toFixed(1)}°C
                              </span>
                            </p>
                            <p>
                              Humidity:{" "}
                              <span className="text-white">
                                {compareData.actual?.sensor_data?.humidity?.toFixed(1)}%
                              </span>
                            </p>
                            <p>
                              Soil Moisture:{" "}
                              <span className="text-white">
                                {compareData.actual?.sensor_data?.soil_moisture?.toFixed(1)}%
                              </span>
                            </p>
                            <p>
                              Leaf ΔT:{" "}
                              <span className="text-white">
                                {compareData.actual?.sensor_data?.leaf_temp_delta?.toFixed(2)}°C
                              </span>
                            </p>
                            <p>
                              Plant Stress:{" "}
                              <span className="text-white">
                                {compareData.actual?.plant?.stress?.toFixed(2)}
                              </span>
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {!compareData && !compareLoading && snapshotMinute !== null && (
                    <div className="text-center text-gray-500 py-4 text-sm">
                      Select a compare time and click "Compare" to see prediction vs actual
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
