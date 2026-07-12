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
  Radar,
  ReferenceLine,
  Legend,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

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

  // --- Fetch simulator state (scenario list, current state) ---
  const fetchSimState = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/simulator/state`);
      const json = await res.json();
      setSimState(json);
      if (json.available_scenarios) {
        setScenarioList(json.available_scenarios);
      }
    } catch (err) {
      // Silently ignore — simulator may not be running yet
    }
  }, []);

  // --- Core analysis: step simulator + run AI pipeline ---
  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Use /simulator/analyze to get both simulator state + AI analysis
      const res = await fetch(`${API_BASE}/simulator/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plant: selectedPlant,
          stage: growthStage,
          dt_minutes: simSpeed,
        }),
      });
      const json = await res.json();
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
    } catch (err: any) {
      setError(err.message || "Connection failed");
      console.error(err);
    }

    setLoading(false);
  }, [selectedPlant, growthStage, simSpeed]);

  // --- Simulator controls ---
  const simControl = useCallback(async (action: string, body?: any) => {
    try {
      const res = await fetch(`${API_BASE}/simulator/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await res.json();
      if (action === "start") setSimRunning(true);
      if (action === "pause" || action === "reset") setSimRunning(false);
      if (action === "scenario") setSimScenario(body?.scenario || "normal_day");
      if (action === "speed") setSimSpeed(body?.speed || 1.0);
      await fetchSimState();
    } catch (err) {
      console.error("Simulator control error:", err);
    }
  }, [fetchSimState]);

  // --- Temporal Replay: fetch state at a specific sim_minute ---
  const fetchReplay = useCallback(async (minute: number, n: number = 10) => {
    setReplayLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulator/temporal/replay?minute=${minute}&n=${n}`);
      const json = await res.json();
      setReplayData(json);
      setReplayMinute(minute);
    } catch (err) {
      console.error("Replay fetch error:", err);
    }
    setReplayLoading(false);
  }, []);

  // --- Prediction Accuracy: fetch rolling accuracy ---
  const fetchAccuracy = useCallback(async () => {
    setAccuracyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulator/temporal/accuracy`);
      const json = await res.json();
      setAccuracyData(json);
    } catch (err) {
      console.error("Accuracy fetch error:", err);
    }
    setAccuracyLoading(false);
  }, []);

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

  // Build chart data: historical trajectory + NOW marker + future prediction
  const chartData = trajectory.map((point: any) => ({
    label: point.sim_time,
    minute: point.sim_minute,
    air_temp: point.air_temp,
    humidity: point.humidity,
    soil_moisture: point.soil_moisture,
    leaf_temp_delta: point.leaf_temp_delta,
    stress: point.stress,
    growth: point.growth,
    type: "past",
  }));

  // Add current state as NOW marker if not already the last entry
  const nowEntry = {
    label: "NOW",
    minute: currentSimMinute,
    air_temp: sensor?.air_temp,
    humidity: sensor?.humidity,
    soil_moisture: sensor?.soil_moisture,
    leaf_temp_delta: sensor?.leaf_temp_delta,
    stress: simState?.plant?.stress ?? 0,
    growth: simState?.plant?.growth ?? 0,
    type: "now",
  };

  // Future prediction projection (simple linear extrapolation from last 2 points)
  const futurePrediction: any[] = [];
  if (chartData.length >= 2) {
    const last = chartData[chartData.length - 1];
    const prev = chartData[chartData.length - 2];
    const futureConfidence = temporal?.future_state?.future_confidence ?? 0.7;
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
        // Confidence band: wider as we go further into future
        ci_upper_temp: last.air_temp + (last.air_temp - prev.air_temp) * frac + (1 - futureConfidence) * 2 * (i),
        ci_lower_temp: last.air_temp + (last.air_temp - prev.air_temp) * frac - (1 - futureConfidence) * 2 * (i),
        ci_upper_humidity: last.humidity + (last.humidity - prev.humidity) * frac + (1 - futureConfidence) * 3 * (i),
        ci_lower_humidity: last.humidity + (last.humidity - prev.humidity) * frac - (1 - futureConfidence) * 3 * (i),
      });
    }
  }

  // Merge all for the full chart
  const fullChartData = [...chartData, nowEntry, ...futurePrediction];

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

        <div className="flex gap-6 mb-6">
          <div className="text-green-400">● Backend Online</div>
          <div className="text-green-400">● AI Active</div>
          <div className="text-green-400">● Biology Active</div>
          {data && <div className="text-green-400">● Pipeline Live</div>}
          {simRunning && <div className="text-blue-400">● Simulator Running</div>}
        </div>

        {/* ============================================================ */}
        {/* SIMULATOR CONTROLS */}
        {/* ============================================================ */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6 mb-8">
          <h2 className="text-2xl mb-4">Digital Twin Controls</h2>

          <div className="grid grid-cols-7 gap-4 mb-4">
            {/* Start */}
            <button
              onClick={() => simControl("start")}
              className="bg-green-600 hover:bg-green-500 rounded-xl py-3 font-bold transition"
            >
              ▶ Start
            </button>

            {/* Pause */}
            <button
              onClick={() => simControl("pause")}
              className="bg-yellow-600 hover:bg-yellow-500 rounded-xl py-3 font-bold transition"
            >
              ⏸ Pause
            </button>

            {/* Reset */}
            <button
              onClick={() => simControl("reset")}
              className="bg-red-600 hover:bg-red-500 rounded-xl py-3 font-bold transition"
            >
              ↺ Reset
            </button>

            {/* Speed */}
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

            {/* Scenario */}
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

            {/* Live Mode */}
            <button
              onClick={() => {
                if (!simRunning) simControl("start");
                setLiveMode(!liveMode);
              }}
              className={`rounded-xl py-3 font-bold transition ${
                liveMode ? "bg-red-500 hover:bg-red-400" : "bg-blue-500 hover:bg-blue-400"
              }`}
            >
              {liveMode ? "⏹ Live ON" : "▶ Live OFF"}
            </button>

            {/* Manual Step */}
            <button
              onClick={analyze}
              disabled={loading}
              className="bg-purple-600 hover:bg-purple-500 rounded-xl py-3 font-bold transition disabled:opacity-50"
            >
              {loading ? "..." : "⏭ Step"}
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
        </div>

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
            {/* TEMPORAL AI ENGINE — Historical Trajectory + Future Prediction */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-2">Temporal AI Engine</h2>
              <p className="text-gray-400 text-sm mb-6">
                Historical sensor trajectory with future prediction projection.
                Confidence bands widen as predictions extend further into the future.
              </p>

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
                    {temporal?.future_state?.future_confidence
                      ? `${(temporal.future_state.future_confidence * 100).toFixed(0)}%`
                      : "—"}
                  </p>
                </div>
              </div>

              {/* Full Trajectory Chart: Past (solid) + NOW (marker) + Future (dashed + confidence bands) */}
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
                    contentStyle={{
                      backgroundColor: "#111",
                      border: "1px solid #333",
                      borderRadius: "12px",
                    }}
                    labelStyle={{ color: "#fff" }}
                  />
                  <Legend />

                  {/* Past air_temp — solid green */}
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
                    x="NOW"
                    stroke="#ffcc00"
                    strokeWidth={2}
                    strokeDasharray="6 6"
                    label={{
                      value: "NOW",
                      position: "top",
                      fill: "#ffcc00",
                      fontSize: 12,
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

                  {/* Future predicted air_temp — dashed green */}
                  <Line
                    type="monotone"
                    dataKey="air_temp"
                    stroke="#00ff99"
                    strokeWidth={2}
                    strokeDasharray="8 4"
                    dot={{ r: 3, fill: "#00ff99" }}
                    name="Predicted Temp"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>

              {/* Explainable AI */}
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
              <h2 className="text-3xl mb-6">Live Stress Radar</h2>

              <ResponsiveContainer width="100%" height={400}>
                <RadarChart
                  data={[
                    {
                      metric: "Heat",
                      value: Math.min((sensor?.air_temp || 0) * 2, 100),
                    },
                    {
                      metric: "Humidity",
                      value: Math.min(100 - (sensor?.humidity || 0), 100),
                    },
                    {
                      metric: "Leaf",
                      value: Math.min((sensor?.leaf_temp_delta || 0) * 15, 100),
                    },
                    {
                      metric: "Root",
                      value: Math.min((sensor?.soil_temp || 0) * 2, 100),
                    },
                    {
                      metric: "Water",
                      value: Math.min(100 - (sensor?.soil_moisture || 0), 100),
                    },
                  ]}
                >
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <Radar
                    dataKey="value"
                    stroke="#00ff99"
                    fill="#00ff99"
                    fillOpacity={0.4}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* ============================================================ */}
            {/* TEMPORAL REPLAY — Navigate through historical states */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-2">Temporal Replay</h2>
              <p className="text-gray-400 text-sm mb-6">
                Navigate through the simulation history. Drag the slider to inspect
                sensor readings, plant state, and AI predictions at any past moment.
              </p>

              {/* Replay Slider */}
              <div className="mb-6">
                <label className="text-gray-400 text-sm mb-2 block">
                  Sim Minute: {replayMinute ?? currentSimMinute}
                </label>
                <input
                  type="range"
                  min={0}
                  max={currentSimMinute || 1439}
                  value={replayMinute ?? currentSimMinute ?? 0}
                  onChange={(e) => {
                    const v = parseInt(e.target.value);
                    setReplayMinute(v);
                  }}
                  onMouseUp={() => {
                    if (replayMinute !== null) fetchReplay(replayMinute);
                  }}
                  onTouchEnd={() => {
                    if (replayMinute !== null) fetchReplay(replayMinute);
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

              {/* Replay Result */}
              {replayLoading && (
                <div className="text-center text-gray-400 py-4">Loading replay state...</div>
              )}

              {replayData && !replayLoading && (
                <div className="grid grid-cols-2 gap-4">
                  {/* Target State */}
                  <div className="bg-black/20 rounded-2xl p-5">
                    <h3 className="text-green-400 mb-3">
                      State at {replayData.target?.sim_time || replayMinute}
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
                <h2 className="text-3xl mb-6">AI Reasoning Console</h2>

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
            {/* CONFIDENCE PANEL */}
            {/* ============================================================ */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Prediction Confidence</h2>

              <div className="grid grid-cols-5 gap-4">
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Sensor</p>
                  <p className="text-2xl mt-2">{confidence?.sensor_confidence}%</p>
                </div>
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">AI Model</p>
                  <p className="text-2xl mt-2">{confidence?.ai_confidence}%</p>
                </div>
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Temporal</p>
                  <p className="text-2xl mt-2">{confidence?.temporal_confidence}%</p>
                </div>
                <div className="bg-black/20 rounded-2xl p-5 text-center">
                  <p className="text-gray-400 text-sm">Biology</p>
                  <p className="text-2xl mt-2">{confidence?.biology_health_score}%</p>
                </div>
                <div className="bg-black/20 rounded-2xl p-5 text-center border border-green-500/30">
                  <p className="text-gray-400 text-sm">Overall</p>
                  <p className="text-3xl mt-2 text-green-400">{confidence?.overall}%</p>
                </div>
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
          </>
        )}
      </div>
    </main>
  );
}
