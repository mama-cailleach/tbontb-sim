## Calibration
First test using OCYG Willems stats and simulation with the same number of innings.

OCYG because he has the most ammount of innings, so better numbers to check accuracy.

For now just tested runs and wickets, for a quick overview.

Random Seed: 999


### Calibration Summary

Metric | Real Data (N=146/152) | Simulated Data (N=146/152) | Difference | SE (Real vs Sim) | Test Result
Runs | Mean = 22.0, SD = 17.5 | Mean = 19.7, SD = 19.4 | –2.3 | 1.5 vs 1.6 | t = 1.04, p = 0.298 → No evidence of difference
Wickets | Mean = 0.816, SD = 0.902 | Mean = 0.928, SD = 0.957 | +0.112 | 0.073 vs 0.078 | t = –1.05, p = 0.295 → No evidence of difference


### Quick Interpretation

- Means: Both batting and bowling averages are statistically consistent with the real player data (p‑values ≫ 0.05).
- Spread (SD): Simulator produces similar variability to real performances.
- Precision (SE): SEs are nearly identical, showing the averages are estimated with similar stability.
- Overall: Strong evidence that the simulator is well‑calibrated, differences are within expected noise.