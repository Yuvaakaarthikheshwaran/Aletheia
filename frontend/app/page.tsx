
"use client";

import { useEffect, useState } from "react";
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
  Radar
} from "recharts";

export default function Home() {
  const [query, setQuery] = useState("");
  const [selectedPlant, setSelectedPlant] = useState("tomato");
  const [growthStage, setGrowthStage] = useState("flowering");
  const [phase, setPhase] = useState("day");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  async function analyze() {
    setLoading(true);

    try {
      const res = await fetch(
        `http://127.0.0.1:5000/predict/${selectedPlant}/${growthStage}/${phase}`
      );
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  }

  useEffect(() => {
    analyze();
  }, []);

  useEffect(() => {
    if (!demoMode) return;

    const interval = setInterval(() => {
      analyze();
    }, 2500);

    return () => clearInterval(interval);
  }, [demoMode, selectedPlant, growthStage, phase]);

  const sensor = data?.sensor_data;
  const ai = data?.ai_result?.current_state;
  const future = data?.ai_result?.future_state;
  const biology = data?.biology_result;
  const profile = data?.plant_profile;
  const stageProfile = profile?.growth_stages?.[growthStage];

  const trendData = [
    { time: "T-3", temp: 30, humidity: 76, leaf: 3 },
    { time: "T-2", temp: 34, humidity: 74, leaf: 4 },
    {
      time: "NOW",
      temp: sensor?.air_temp || 39,
      humidity: sensor?.humidity || 71,
      leaf: sensor?.leaf_temp_delta || 5
    }
  ];

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
          Autonomous Plant Intelligence System
        </p>

        <div className="flex gap-6 mb-6">
          <div className="text-green-400">● Backend Online</div>
          <div className="text-green-400">● AI Active</div>
          <div className="text-green-400">● Biology Active</div>
        </div>

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

          <button
            onClick={analyze}
            className="bg-green-500 rounded-xl font-bold"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>

          <button
            onClick={() => setDemoMode(!demoMode)}
            className={`rounded-xl font-bold ${
              demoMode ? "bg-red-500" : "bg-blue-500"
            }`}
          >
            {demoMode ? "Demo ON" : "Demo OFF"}
          </button>
        </div>

        {data && (
          <>

            {/* HERO */}
            <div className="grid grid-cols-12 gap-6 mb-8">
              <div className="col-span-3 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
                <h2 className="text-2xl mb-4">Plant Intelligence</h2>
                <p className="mb-2">Plant: {selectedPlant}</p>
                <p className="mb-2">Stage: {growthStage}</p>
                <p className="mb-2">Phase: {phase}</p>
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
                  {ai?.prediction}
                </p>
              </div>

              <div className="col-span-3 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
                <h2 className="text-2xl mb-4">AI Brain</h2>

                <div className="space-y-4">
                  <div>
                    <p className="text-gray-400">Confidence</p>
                    <p className="text-2xl">{ai?.confidence}%</p>
                  </div>

                  <div>
                    <p className="text-gray-400">Risk State</p>
                    <p className="text-2xl text-yellow-400">
                      {ai?.risk_state}
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-400">Severity</p>
                    <p className="text-2xl text-red-400">
                      {ai?.severity}
                    </p>
                  </div>

                  <div>
                    <p className="text-gray-400">Future Prediction</p>
                    <p className="text-lg text-red-300">
                      {future?.future_prediction}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* SENSOR INTELLIGENCE */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Sensor Intelligence</h2>

              <div className="grid grid-cols-2 gap-6">
                {sensor &&
                  Object.entries(sensor).map(([key, value]: any) => (
                    <div key={key} className="bg-black/20 rounded-2xl p-5">
                      <div className="flex justify-between mb-3">
                        <span>{metricName(key)}</span>
                        <span>{value}</span>
                      </div>

                      <div className="w-full h-3 bg-gray-800 rounded-full">
                        <div
                          className="h-3 bg-green-400 rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(Math.abs(value) * 2, 100)}%`
                          }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            {/* TEMPORAL AI ENGINE */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Temporal AI Engine</h2>

              {/* 4 Core Questions */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400">Past Trend</p>
                  <p className="text-xl mt-3">30 → 34 → {sensor?.air_temp}</p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400">Velocity</p>
                  <p className="text-3xl mt-3 text-yellow-400">
                    +{sensor?.air_temp_rate}°C
                  </p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400">Future Risk</p>
                  <p className="text-lg mt-3 text-red-300">
                    {future?.future_prediction}
                  </p>
                </div>

                <div className="bg-black/20 rounded-2xl p-5">
                  <p className="text-gray-400">Leaf Delta</p>
                  <p className="text-3xl mt-3 text-orange-300">
                    {sensor?.leaf_temp_delta}°C
                  </p>
                </div>
              </div>

              {/* Trend Visualization */}
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={trendData}>
                  <CartesianGrid stroke="#333" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="temp"
                    stroke="#00ff99"
                    fill="#00ff99"
                    fillOpacity={0.25}
                  />
                  <Area
                    type="monotone"
                    dataKey="humidity"
                    stroke="#3399ff"
                    fill="#3399ff"
                    fillOpacity={0.15}
                  />
                </AreaChart>
              </ResponsiveContainer>

              {/* Explainable AI */}
              <div className="mt-6 bg-black/20 rounded-2xl p-6">
                <h3 className="text-xl mb-4">AI Reasoning</h3>

                {ai?.reasons?.map((reason: string, idx: number) => (
                  <p key={idx} className="text-yellow-300 mb-2">
                    • {reason}
                  </p>
                ))}
              </div>
            </div>

            {/* BIOLOGY ENGINE */}
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
                              )}%`
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

            {/* GROWTH + DAY/NIGHT */}
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
                  {profile?.day_profile &&
                    Object.entries(profile.day_profile)
                      .slice(0, 4)
                      .map(([key, value]: any) => (
                        <div key={key} className="mb-2">
                          {metricName(key)}: {value[0]} — {value[1]}
                        </div>
                      ))}
                </div>

                <div>
                  <h3 className="text-blue-400 mb-3">Night Profile</h3>
                  {profile?.night_profile &&
                    Object.entries(profile.night_profile)
                      .slice(0, 4)
                      .map(([key, value]: any) => (
                        <div key={key} className="mb-2">
                          {metricName(key)}: {value[0]} — {value[1]}
                        </div>
                      ))}
                </div>
              </div>
            </div>

            {/* LIVE STRESS RADAR */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">Live Stress Radar</h2>

              <ResponsiveContainer width="100%" height={400}>
                <RadarChart
                  data={[
                    {
                      metric: "Heat",
                      value: Math.min((sensor?.air_temp || 0) * 2, 100)
                    },
                    {
                      metric: "Humidity",
                      value: Math.min(100 - (sensor?.humidity || 0), 100)
                    },
                    {
                      metric: "Leaf",
                      value: Math.min((sensor?.leaf_temp_delta || 0) * 15, 100)
                    },
                    {
                      metric: "Root",
                      value: Math.min((sensor?.soil_temp || 0) * 2, 100)
                    },
                    {
                      metric: "Water",
                      value: Math.min(100 - (sensor?.soil_moisture || 0), 100)
                    }
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

            {/* AI TIMELINE */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
              <h2 className="text-3xl mb-6">AI Timeline</h2>

              <div className="space-y-4">
                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-green-300">T-3</p>
                  <p>System monitoring environment</p>
                </div>

                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-yellow-300">T-2</p>
                  <p>Environmental shift detected</p>
                </div>

                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-orange-300">T-1</p>
                  <p>Stress signals increasing</p>
                </div>

                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-red-300">NOW</p>
                  <p>{ai?.prediction}</p>
                </div>
              </div>
            </div>

            {/* WARNINGS + RECOMMENDATION */}
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
                <h2 className="text-3xl mb-6">Recommendation Engine</h2>

                <div className="bg-black/20 rounded-2xl p-6">
                  <p className="text-red-300 mb-3">Priority: Immediate</p>
                  <p className="text-2xl">{ai?.recommendation}</p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

