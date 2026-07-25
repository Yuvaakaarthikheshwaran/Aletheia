"use client";

import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface CumulativeStress {
  heat: number;
  cold: number;
  water: number;
  humidity: number;
  root_zone: number;
  leaf_thermal: number;
  light: number;
}

interface YieldLimiter {
  factor: string;
  description: string;
  critical_stage_match: boolean;
}

interface YieldImpactRange {
  min_percent: number;
  max_percent: number;
}

interface YieldRecommendation {
  action: string;
  why: string;
  urgency: string;
  expected_benefit: string;
}

interface YieldTrendPoint {
  index: number;
  yield_potential: number;
  stress_events: string[];
  sim_time?: string;
  sim_minute?: number;
  is_current?: boolean;
}

interface YieldIntelligenceData {
  yield_potential_percent: number;
  yield_loss_risk: string;
  yield_loss_risk_score: number;
  estimated_yield_impact_range: YieldImpactRange;
  primary_yield_limiter: YieldLimiter;
  cumulative_stress: CumulativeStress;
  critical_stage: string | null;
  forecast_confidence: number;
  confidence_label: string;
  evidence_used: string[];
  missing_evidence: string[];
  absolute_yield_forecast: any;
  yield_recommendations: YieldRecommendation[];
  yield_story: string;
  yield_trend: YieldTrendPoint[];
}

interface YieldIntelligenceProps {
  data: YieldIntelligenceData | null;
  operatingMode: "simulator" | "hardware" | "replay";
  hardwareHistory: number;
}

// --- Color helpers ---
function yieldPotentialColor(score: number): string {
  if (score >= 85) return "text-green-400";
  if (score >= 70) return "text-yellow-400";
  if (score >= 50) return "text-orange-400";
  return "text-red-400";
}

function yieldPotentialBg(score: number): string {
  if (score >= 85) return "from-green-500/20 to-green-600/10 border-green-500/30";
  if (score >= 70) return "from-yellow-500/20 to-yellow-600/10 border-yellow-500/30";
  if (score >= 50) return "from-orange-500/20 to-orange-600/10 border-orange-500/30";
  return "from-red-500/20 to-red-600/10 border-red-500/30";
}

function riskBadgeColor(risk: string): string {
  switch (risk) {
    case "low": return "bg-green-500/20 text-green-400 border-green-500/50";
    case "moderate": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/50";
    case "high": return "bg-orange-500/20 text-orange-400 border-orange-500/50";
    case "critical": return "bg-red-500/20 text-red-400 border-red-500/50";
    default: return "bg-gray-500/20 text-gray-400 border-gray-500/50";
  }
}

function confidenceColor(label: string): string {
  switch (label) {
    case "high": return "text-green-400";
    case "moderate": return "text-yellow-400";
    case "low": return "text-orange-400";
    case "insufficient_history": return "text-red-400";
    default: return "text-gray-400";
  }
}

function urgencyColor(urgency: string): string {
  switch (urgency) {
    case "immediate": return "text-red-400 border-red-500/30 bg-red-500/10";
    case "soon": return "text-orange-400 border-orange-500/30 bg-orange-500/10";
    case "monitor": return "text-yellow-400 border-yellow-500/30 bg-yellow-500/10";
    case "routine": return "text-green-400 border-green-500/30 bg-green-500/10";
    default: return "text-gray-400 border-gray-500/30 bg-gray-500/10";
  }
}

function stressLabel(key: string): string {
  const labels: Record<string, string> = {
    heat: "Heat Stress",
    cold: "Cold Stress",
    water: "Water Stress",
    humidity: "Humidity Stress",
    root_zone: "Root Zone Stress",
    leaf_thermal: "Leaf Thermal Stress",
    light: "Light Stress",
  };
  return labels[key] || key;
}

function stressColor(level: number): string {
  if (level >= 60) return "text-red-400";
  if (level >= 30) return "text-orange-400";
  if (level >= 10) return "text-yellow-400";
  return "text-green-400";
}

function stressBarColor(level: number): string {
  if (level >= 60) return "bg-red-500";
  if (level >= 30) return "bg-orange-500";
  if (level >= 10) return "bg-yellow-500";
  return "bg-green-500";
}

export default function YieldIntelligence({
  data,
  operatingMode,
  hardwareHistory: hwHistoryLen,
}: YieldIntelligenceProps) {
  // --- Cold-start / no data state ---
  if (!data) {
    return (
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl text-amber-300">🌾 Yield Intelligence</h2>
          <span className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-gray-500/20 text-gray-400 border border-gray-500/50">
            ◌ Awaiting Data
          </span>
        </div>
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">Yield Intelligence awaiting analysis data.</p>
          <p className="text-sm">
            Run an analysis to compute yield potential, loss risk, and recommendations.
          </p>
        </div>
      </div>
    );
  }

  const yp = data.yield_potential_percent ?? 0;
  const risk = data.yield_loss_risk ?? "unknown";
  const riskScore = data.yield_loss_risk_score ?? 0;
  const impact = data.estimated_yield_impact_range ?? { min_percent: 0, max_percent: 0 };
  const limiter = data.primary_yield_limiter;
  const cumStress = data.cumulative_stress;
  const fc = data.forecast_confidence ?? 0;
  const confLabel = data.confidence_label ?? "unknown";
  const evidenceUsed = data.evidence_used ?? [];
  const missingEvidence = data.missing_evidence ?? [];
  const absYield = data.absolute_yield_forecast;
  const yieldRecs = data.yield_recommendations ?? [];
  const yieldStory = data.yield_story ?? "";
  const yieldTrend = data.yield_trend ?? [];

  // Cold-start: insufficient history
  const isColdStart =
    confLabel === "insufficient_history" ||
    (operatingMode === "hardware" && hwHistoryLen < 5);

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 mb-8">
      {/* ---- Header ---- */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-3xl text-amber-300">🌾 Yield Intelligence</h2>
          <span
            className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${riskBadgeColor(risk)}`}
          >
            {risk === "low"
              ? "✓ Low Risk"
              : risk === "moderate"
              ? "⚠ Moderate Risk"
              : risk === "high"
              ? "▲ High Risk"
              : risk === "critical"
              ? "✕ Critical Risk"
              : "— Unknown"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold uppercase ${confidenceColor(confLabel)}`}>
            {confLabel === "insufficient_history"
              ? "⏳ Insufficient History"
              : confLabel === "low"
              ? "◈ Low Confidence"
              : confLabel === "moderate"
              ? "◆ Moderate Confidence"
              : "◆ High Confidence"}
          </span>
          <span className="text-gray-500 text-xs">({(fc * 100).toFixed(0)}%)</span>
        </div>
      </div>

      {/* ---- Cold-Start Warning ---- */}
      {isColdStart && (
        <div className="mb-6 bg-yellow-500/10 border border-yellow-500/20 rounded-2xl p-4 flex items-center gap-3">
          <span className="text-yellow-400 text-xl">⏳</span>
          <div>
            <p className="text-yellow-300 font-bold">Yield Intelligence Warming Up</p>
            <p className="text-yellow-400/70 text-sm">
              {operatingMode === "hardware" && hwHistoryLen === 0
                ? "No sensor data received yet. Yield potential estimates require historical data to compute cumulative stress exposure."
                : `Only ${hwHistoryLen} data point(s) available. Yield intelligence needs sufficient history to compute cumulative stress exposure accurately.`}
            </p>
          </div>
        </div>
      )}

      {/* ---- Hero Row: Yield Potential + Loss Risk + Impact ---- */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Yield Potential Gauge */}
        <div
          className={`bg-gradient-to-br ${yieldPotentialBg(yp)} rounded-3xl p-6 text-center border`}
        >
          <p className="text-gray-400 text-sm mb-2">Yield Potential</p>
          <div className="relative inline-flex items-center justify-center">
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120">
              <circle
                cx="60" cy="60" r="52"
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="8"
              />
              <circle
                cx="60" cy="60" r="52"
                fill="none"
                stroke={
                  yp >= 85 ? "#4ade80" :
                  yp >= 70 ? "#facc15" :
                  yp >= 50 ? "#fb923c" : "#f87171"
                }
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(yp / 100) * 327} 327`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-4xl font-bold ${yieldPotentialColor(yp)}`}>
                {yp.toFixed(0)}
              </span>
              <span className="text-gray-500 text-xs">/ 100</span>
            </div>
          </div>
          <p className="text-gray-500 text-xs mt-2">
            Retained biological yield potential
          </p>
        </div>

        {/* Yield Loss Risk + Impact */}
        <div className="col-span-2 grid grid-cols-1 gap-4">
          {/* Risk Score Bar */}
          <div className="bg-black/20 rounded-2xl p-5">
            <div className="flex justify-between mb-2">
              <span className="text-gray-400 text-sm">Yield Loss Risk</span>
              <span className={`text-sm font-bold ${riskBadgeColor(risk).split(" ")[1]}`}>
                {riskScore.toFixed(0)}/100
              </span>
            </div>
            <div className="w-full h-4 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  riskScore >= 75 ? "bg-red-500" :
                  riskScore >= 50 ? "bg-orange-500" :
                  riskScore >= 25 ? "bg-yellow-500" : "bg-green-500"
                }`}
                style={{ width: `${Math.min(riskScore, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-gray-500 mt-1">
              <span>Low</span>
              <span>Moderate</span>
              <span>High</span>
              <span>Critical</span>
            </div>
          </div>

          {/* Estimated Yield Impact */}
          <div className="bg-black/20 rounded-2xl p-5">
            <span className="text-gray-400 text-sm block mb-3">
              Estimated Yield Impact Range
            </span>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Min Loss</span>
                  <span>Max Loss</span>
                </div>
                <div className="relative h-3 bg-gray-800 rounded-full">
                  <div
                    className="absolute h-3 bg-gradient-to-r from-yellow-500 to-red-500 rounded-full opacity-70"
                    style={{
                      left: `${impact.min_percent}%`,
                      width: `${impact.max_percent - impact.min_percent}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs mt-1">
                  <span className="text-yellow-400">{impact.min_percent?.toFixed(1)}%</span>
                  <span className="text-red-400">{impact.max_percent?.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ---- Primary Yield Limiter ---- */}
      {limiter && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6 border-l-4 border-red-500/50">
          <div className="flex items-start gap-3">
            <span className="text-red-400 text-xl mt-0.5">⚠</span>
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wider">
                Primary Yield-Limiting Factor
              </p>
              <p className="text-white text-lg font-bold capitalize">
                {limiter.factor?.replaceAll("_", " ")}
              </p>
              <p className="text-gray-400 text-sm mt-1">{limiter.description}</p>
              {limiter.critical_stage_match && (
                <p className="text-yellow-400 text-xs mt-2">
                  ⚡ This factor is critical during the current growth stage
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---- Cumulative Stress Exposure ---- */}
      {cumStress && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6">
          <h3 className="text-sm text-gray-400 mb-4">Cumulative Stress Exposure</h3>
          <div className="space-y-3">
            {Object.entries(cumStress)
              .filter(([_, v]) => typeof v === "number")
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([key, value]) => {
                const v = value as number;
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className={`w-28 text-xs ${stressColor(v)}`}>
                      {stressLabel(key)}
                    </span>
                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${stressBarColor(v)}`}
                        style={{ width: `${Math.min(v, 100)}%` }}
                      />
                    </div>
                    <span className={`w-10 text-right text-xs font-mono ${stressColor(v)}`}>
                      {v.toFixed(0)}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* ---- Yield Trend Chart ---- */}
      {yieldTrend.length > 1 && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6">
          <h3 className="text-gray-300 text-sm mb-4">Yield Potential Trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={yieldTrend}>
              <CartesianGrid stroke="#333" strokeDasharray="3 3" />
              <XAxis
                dataKey="index"
                tick={{ fill: "#666", fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#666", fontSize: 10 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const pt = payload[0]?.payload;
                  return (
                    <div className="bg-[#111] border border-[#333] rounded-xl p-3 text-xs">
                      <p className="text-gray-400">
                        {pt?.sim_time ? `Time: ${pt.sim_time}` : `Point: ${pt?.index}`}
                      </p>
                      <p className="text-amber-300 font-bold">
                        Yield Potential: {pt?.yield_potential?.toFixed(0)}%
                      </p>
                      {pt?.stress_events?.length > 0 && (
                        <p className="text-red-400 mt-1">
                          Stress: {pt.stress_events.map((s: string) => stressLabel(s)).join(", ")}
                        </p>
                      )}
                      {pt?.is_current && (
                        <p className="text-green-400 mt-1 font-bold">● Current</p>
                      )}
                    </div>
                  );
                }}
              />
              <ReferenceLine
                y={90}
                stroke="#4ade80"
                strokeDasharray="4 4"
                strokeOpacity={0.3}
              />
              <ReferenceLine
                y={70}
                stroke="#facc15"
                strokeDasharray="4 4"
                strokeOpacity={0.3}
              />
              <Line
                type="monotone"
                dataKey="yield_potential"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                name="Yield Potential %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ---- Yield Story ---- */}
      {yieldStory && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6">
          <h3 className="text-gray-300 text-sm mb-3">Yield Story</h3>
          <p className="text-gray-400 text-sm leading-relaxed">{yieldStory}</p>
        </div>
      )}

      {/* ---- Yield Maximization Recommendations ---- */}
      {yieldRecs.length > 0 && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6">
          <h3 className="text-gray-300 text-sm mb-4">
            🌱 Yield Maximization Recommendations
          </h3>
          <div className="space-y-3">
            {yieldRecs.map((rec, idx) => (
              <div
                key={idx}
                className={`rounded-xl p-4 border ${urgencyColor(rec.urgency)}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-white font-bold text-sm">{rec.action}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          rec.urgency === "immediate"
                            ? "bg-red-500/20 text-red-400"
                            : rec.urgency === "soon"
                            ? "bg-orange-500/20 text-orange-400"
                            : rec.urgency === "monitor"
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-green-500/20 text-green-400"
                        }`}
                      >
                        {rec.urgency}
                      </span>
                    </div>
                    <p className="text-gray-400 text-xs">{rec.why}</p>
                    {rec.expected_benefit && (
                      <p className="text-green-400/70 text-xs mt-1">
                        Expected benefit: {rec.expected_benefit}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Absolute Yield Forecast ---- */}
      {absYield && absYield.status !== "insufficient_data" && (
        <div className="bg-black/20 rounded-2xl p-5 mb-6">
          <h3 className="text-gray-300 text-sm mb-3">Projected Final Yield</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-gray-500 text-xs">Estimated Yield</p>
              <p className="text-2xl text-amber-300 font-bold mt-1">
                {absYield.estimated_yield ?? "—"}
              </p>
              <p className="text-gray-500 text-[10px]">{absYield.unit ?? ""}</p>
            </div>
            <div className="text-center">
              <p className="text-gray-500 text-xs">Confidence Range</p>
              <p className="text-lg text-gray-300 mt-1">
                {absYield.range_low ?? "—"} – {absYield.range_high ?? "—"}
              </p>
              <p className="text-gray-500 text-[10px]">{absYield.unit ?? ""}</p>
            </div>
            <div className="text-center">
              <p className="text-gray-500 text-xs">Basis</p>
              <p className="text-sm text-gray-400 mt-1">{absYield.basis ?? "—"}</p>
            </div>
          </div>
        </div>
      )}

      {/* ---- Evidence Report ---- */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-black/20 rounded-2xl p-4">
          <h3 className="text-green-400 text-xs font-bold mb-2">Evidence Used</h3>
          {evidenceUsed.length > 0 ? (
            <ul className="space-y-1">
              {evidenceUsed.map((e, idx) => (
                <li key={idx} className="text-gray-400 text-xs flex items-start gap-1">
                  <span className="text-green-500 mt-0.5">✓</span>
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-xs">No evidence available</p>
          )}
        </div>
        <div className="bg-black/20 rounded-2xl p-4">
          <p className="text-yellow-400 text-xs font-bold mb-2">Missing Evidence</p>
          {missingEvidence.length > 0 ? (
            <ul className="space-y-1">
              {missingEvidence.map((e, idx) => (
                <li key={idx} className="text-gray-400 text-xs flex items-start gap-1">
                  <span className="text-yellow-500 mt-0.5">○</span>
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-green-400 text-xs">All evidence sources available</p>
          )}
        </div>
      </div>
    </div>
  );
}