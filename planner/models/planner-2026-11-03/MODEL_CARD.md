# CropPlannerNet model card

**Adopted:** it beats the climatology oracle (B0) on pinball loss and NDCG@3.

- **Task:** rainfed relative yield (p10/p50/p90), P(relative yield >= 0.6), irrigation
  need and stress days for 8 crops: maize, common_bean, sorghum, soybean, groundnut, cotton, tomato, potato.
- **Labels:** an oracle of published FAO models (FAO-56 water balance, FAO-33 Ky,
  ECOCROP ranges) run on NASA POWER weather, 1981-2025 (planner/README.md §6).
- **Not calibrated against real yields.** The EVA check below is the only comparison
  with reality; the crop parameters have not been reviewed by an agronomist.
- **ONNX parity:** max |PyTorch - ONNX Runtime| = 1.34e-05.

## Test split (2018-2025)

| Model | rel_yield_pinball | rel_yield_mae | rel_yield_coverage_p10_p90 | success_brier | success_ece | irrigation_mae_mm | ndcg_at_3 |
|---|---|---|---|---|---|---|---|
| network | 0.02091 | 0.06187 | 0.74 | 0.0562 | 0.03129 | 48.07 | 0.98433 |
| b0_climatology | 0.03419 | 0.06838 | 0.2367 | 0.09373 | 0.09373 | 56.47 | 0.9771 |
| b1_history | 0.02454 | 0.07312 | 0.6887 | 0.07261 | 0.03914 | 57.0 | 0.97493 |

## Spatial holdout (Huila never seen in training)

| Model | rel_yield_pinball | rel_yield_mae | rel_yield_coverage_p10_p90 | success_brier | success_ece | irrigation_mae_mm | ndcg_at_3 |
|---|---|---|---|---|---|---|---|
| network | 0.02763 | 0.08394 | 0.657 | 0.0876 | 0.05222 | 65.18 | 0.98412 |
| b0_climatology | 0.03943 | 0.07885 | 0.0791 | 0.11331 | 0.11331 | 69.13 | 0.98569 |
| b1_history | 0.09261 | 0.21425 | 0.1591 | 0.22386 | 0.21089 | 93.74 | 0.90871 |

## Spearman with EVA municipal yield anomalies (test years)

{
 "maize": 0.04,
 "common_bean": -0.038,
 "sorghum": 0.033,
 "soybean": -0.02,
 "groundnut": -0.109,
 "cotton": 0.202,
 "tomato": 0.219,
 "potato": 0.104
}
