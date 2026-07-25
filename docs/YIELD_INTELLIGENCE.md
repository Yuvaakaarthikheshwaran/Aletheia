# Aletheia Yield Intelligence — Technical Documentation

## Overview

The Yield Intelligence Engine is a post-processing layer that consumes existing Aletheia pipeline outputs to produce scientifically defensible yield potential estimates, loss risk assessments, and yield-maximization recommendations.

**Core Principle:** The goal is NOT to display the most impressive yield number. The goal is to produce the MOST ACCURATE AND SCIENTIFICALLY DEFENSIBLE yield estimate that Aletheia's available evidence can support. If the system does not have enough information for an accurate absolute yield forecast, it MUST say so.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   UNIFIED PIPELINE                          │
│                                                             │
│  Step 1: Sensor Validation & Repair                         │
│  Step 2: Plant Profile Resolution (Cache → Tavily → Parser) │
│  Step 3: Biology Engine Evaluation                          │
│  Step 4: Random Forest Stress Classification                │
│  Step 5: Temporal AI Prediction                             │
│  Step 6: Confidence Aggregation                             │
│  Step 7: AI Reasoning (OpenRouter / Local Fallback)         │
│  Step 8: Recommendations                                    │
│  Step 9: YIELD INTELLIGENCE ← THIS ENGINE                   │
│  Step 10: Timestamp                                         │
└─────────────────────────────────────────────────────────────┘
```

The Yield Intelligence Engine does NOT duplicate the AI pipeline. It runs as a post-processing layer after the unified pipeline produces its analysis.

## Scientific Basis

### Yield Potential Formula

```
Yield Potential = Biology Health Score - Σ(Cumulative Stress × Stress Impact × Stage Sensitivity)
```

Where:
- **Biology Health Score** (0-100): From the Biology Engine's evaluation of sensor data against optimal ranges
- **Cumulative Stress**: Duration-weighted stress exposure for each of 7 stress types
- **Stress Impact Coefficient**: How severely each stress type affects yield (e.g., water_stress = 0.90)
- **Stage Sensitivity**: How vulnerable the current growth stage is to stress (e.g., flowering = 0.90)

### Cumulative Stress Computation

Cumulative stress is NOT a single-point reading. It tracks stress exposure over time with duration weighting:

```
Cumulative Stress = Σ(Stress Level at each observation × Duration Weight)
```

- 1 minute of stress ≠ 6 hours of stress
- Duration weighting prevents single bad readings from causing huge yield predictions
- Stress accumulation is capped at 100 per type

### Growth Stage Sensitivity Coefficients

| Stage       | Sensitivity | Rationale |
|-------------|-------------|-----------|
| Germination | 0.35        | Affects stand establishment but plants can be replanted |
| Seedling    | 0.50        | Vulnerable but can recover with good conditions |
| Vegetative  | 0.55        | Moderate impact — affects biomass accumulation |
| Flowering   | 0.90        | CRITICAL — directly determines fruit set |
| Fruiting    | 0.80        | High impact — affects fruit development and quality |
| Harvest     | 0.30        | Low impact — most yield already determined |

Source: FAO Irrigation and Drainage Paper 33 (yield response factors), USDA-ARS research.

### Stress Type Impact Coefficients

| Stress Type      | Impact | Rationale |
|------------------|--------|-----------|
| water_stress     | 0.90   | Most critical — directly limits photosynthesis |
| heat_stress      | 0.85   | Damages reproductive structures, accelerates development |
| leaf_thermal     | 0.75   | Indicates transpiration failure, stomatal closure |
| root_zone_stress | 0.65   | Affects nutrient and water uptake |
| humidity_stress  | 0.50   | Affects transpiration and disease pressure |
| cold_stress      | 0.60   | Slows metabolism, can damage tissues |
| light_stress     | 0.40   | Affects photosynthesis rate |

## Outputs

### 1. Yield Potential (0-100%)
Retained biological yield potential. 100% = no stress impact, optimal conditions. Lower values indicate cumulative stress has reduced potential yield.

### 2. Yield Loss Risk
- **low** (0-25): Minimal yield impact expected
- **moderate** (25-50): Some yield loss possible
- **high** (50-75): Significant yield loss likely
- **critical** (75-100): Severe yield loss imminent

### 3. Estimated Yield Impact Range
Min/max percent range of expected yield loss. Conservative estimates with uncertainty bands.

### 4. Primary Yield-Limiting Factor
The dominant stress factor currently limiting yield, with description and critical stage match indicator.

### 5. Cumulative Stress Exposure
Per-type stress accumulation values (0-100 scale) showing which stressors have been most impactful.

### 6. Yield Forecast Confidence
Separate from temporal confidence. Based on 6 evidence factors:
- Plant identification quality
- Growth stage certainty
- Historical data duration
- Sensor confidence
- Crop-specific baseline availability
- Temporal prediction quality

### 7. Evidence Report
- **evidence_used**: What data sources contributed to the yield estimate
- **missing_evidence**: What's needed for a more accurate estimate

### 8. Absolute Yield Forecast
Only provided when sufficient evidence exists (cultivar, plant density, fruit count, etc.). Returns "insufficient_data" otherwise.

### 9. Yield Maximization Recommendations
Yield-focused recommendations with:
- **action**: What to do
- **why**: Yield consequence if not addressed
- **urgency**: immediate / soon / monitor / routine
- **expected_benefit**: Estimated yield improvement

### 10. Yield Story
Narrative explanation of the current yield situation, generated from actual system data.

### 11. Yield Trend
Historical yield potential data points for visualization. Computed with sliding window to prevent future-data leakage.

## Crop-Specific Knowledge

The engine includes built-in yield knowledge for:
- **Tomato**: 3-5 kg/plant, flowering critical, heat-sensitive
- **Potato**: 1-2 kg/plant, tuber initiation critical, heat-sensitive
- **Mango**: 50-200 kg/tree, flowering critical, cold-sensitive

Unknown plants use generic fallback knowledge with conservative estimates.

## Cold-Start Behavior

When insufficient historical data exists:
- `confidence_label` = "insufficient_history"
- `forecast_confidence` < 0.3
- `yield_story` explains that more data is needed
- UI shows "Yield Intelligence Warming Up" banner

## No Future-Data Leakage

In replay/historical mode, yield trend computation uses a sliding window approach — at each historical point, only data available up to that moment is used. This ensures the yield trend reflects what the system would have known at that time.

## Sources

- FAO Irrigation and Drainage Paper 33: Yield Response to Water
- FAO Irrigation and Drainage Paper 56: Crop Evapotranspiration
- USDA-ARS Plant Stress Physiology Research
- University of California ANR Extension Publications
- Peer-reviewed agronomy: Heat stress effects on crop yield

## Files

| File | Purpose |
|------|---------|
| `backend/yield_intelligence.py` | Core Yield Intelligence Engine (~1380 lines) |
| `backend/unified_pipeline.py` | Step 9 integration |
| `backend/app.py` | `/yield` endpoint + analysis snapshot integration |
| `backend/hardware/store.py` | Hardware data persistence with yield snapshots |
| `backend/plant_profile_schema.py` | Default profile with yield_knowledge section |
| `frontend/app/components/YieldIntelligence.tsx` | React UI component |
| `frontend/app/page.tsx` | Dashboard integration |

## Design Decisions

1. **No AI model duplication**: The engine consumes existing pipeline outputs rather than running its own models
2. **Conservative estimates**: When in doubt, the engine errs on the side of lower confidence
3. **Duration-weighted stress**: Prevents single-point readings from dominating yield estimates
4. **Cache-first plant knowledge**: Uses cached plant profiles before falling back to generic knowledge
5. **Separate confidence**: Yield confidence is computed independently from temporal confidence
6. **No fabrication**: Returns "insufficient_data" when evidence is lacking