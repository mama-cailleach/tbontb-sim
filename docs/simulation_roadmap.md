# Simulator Realism Roadmap (Phased Plan)

This roadmap outlines a step-by-step plan to enhance realism while preserving LMS rules and current simplicity. Each phase includes goals, implementation steps, acceptance criteria, test commands, metrics, risks, and rollback guidance.

---

## Goals
- Improve wicket realism and matchup dynamics without over-complicating the engine.
- Add tension and narrative (pressure, collapses, boundary shape) in a controlled, testable way.
- Keep LMS format rules intact (5-ball overs, penalty balls, retirement at 50).

---

## Phase 1 — Advanced Wicket Probability (Core)

**Intent**: Replace flat wicket rates with matchup-aware probabilities using simple skill formulas.

**Design**
- Batter skill: `bat_skill = clamp((strike_rate - 70) / 90, 0..1)`
- Bowler WPB: `bowler_wpb = wickets / (overs_bowled * balls_per_over)` (default 0.018)
- Bowler skill: `bowl_skill = clamp((bowler_wpb - 0.01) / 0.04, 0..1)`
- Wicket probability: `p_w = clamp(0.02 + 0.07*bowl_skill - 0.03*bat_skill, 0.01, 0.12)`

**Steps**
1. Implement `bowler_wpb` and `bowl_skill` in `simulate_innings()`.
2. Use the `p_w` formula for legal deliveries (skip when free hit).
3. Keep existing dismissal generation and FOW logging unchanged.

**Acceptance Criteria**
- Wicket probabilities range roughly 1–12% per legal ball.
- Strong bowlers dismiss tail or low-SR batters more often than high-SR batters.
- Economy rates do not collapse unrealistically; totals remain plausible.

**Quick Tests**
```powershell
# One-off sanity
python .\main.py --seed 123 --no-intro

# Batch validation
python .\testing\batch_test.py ENG_test.json TBO_VIII.json -n 50 --seed 123 --csv

# Score list smoke test
python .\testing\match_score_list.py ENG_test.json TBO_VIII.json -n 10 --seed 123
```

**Metrics to Track**
- Bowling: Economy (runs/over), wickets/innings, simulated bowling average.
- Batting: Simulated SR and average vs historical.

**Risks / Rollback**
- Coefficient sensitivity can skew wicket rates. If unstable, revert `p_w` to previous flat formula.
- Add a simple feature flag (constant multiplier) to dial back `bowl_skill` impact.

---

## Phase 2 — Dynamic Expectation Pressure (Tension)

**Intent**: Increase wicket chance when a batter is over-performing versus expected SR or runs so far.

**Design**
- `exp_rpb = strike_rate / 100` if available.
- `exp_runs_so_far = exp_rpb * balls_faced_so_far`.
- Pressure multiplier `press = 1.0 + w_sr*sr_exceed + w_runs*runs_exceed`, where:
  - `sr_exceed = max(0, (live_SR - hist_SR) / hist_SR)`
  - `runs_exceed = max(0, (live_runs - exp_runs_so_far) / max(1, exp_runs_so_far))`
  - Suggested weights: `w_sr = 0.20`, `w_runs = 0.15` (cap `press <= 1.35`).
- Apply: `p_w_final = clamp(p_w * press, 0.01, 0.15)`.

**Steps**
1. Track live batter runs/balls; compute live SR.
2. Compute pressure multiplier only when historical SR exists.
3. Apply multiplier to `p_w` (skip when free hit).

**Acceptance Criteria**
- "Hot" batters get slightly more dismissible; late-over collapses become plausible.
- Overall averages and SR remain within reasonable bands (no systemic suppression).

**Quick Tests**
```powershell
python .\main.py --seed 123 --no-intro
python .\testing\batch_test.py ENG_test.json TBO_VIII.json -n 50 --seed 123 --csv
```

**Metrics**
- Compare simulated SR and average deltas vs historical for top-order batters.
- Observe wicket distribution in overs 15–20 for slightly higher rates.

**Risks / Rollback**
- Over-aggressive pressure may over-suppress high-quality batters.
- Keep caps on `press` and consider a minimal floor (`press >= 1.0`).
- Gate with a feature flag to disable pressure quickly.

---

## Phase 3 — Batting Advantage in Run Distribution (Matchup Flavour)

**Intent**: Boost boundary probabilities when the batter advantage is clear (good batter vs weak bowler).

**Design**
- Batting advantage: `ba = batter_rpb / (batter_rpb + bowler_rpb)`.
- If `ba > 0.5`, uplift: `p4 += k4*(ba - 0.5)`, `p6 += k6*(ba - 0.5)`.
  - Suggested: `k4 = 0.01`, `k6 = 0.006`, caps: `p4 <= 0.25`, `p6 <= 0.15`.
- Renormalize remaining mass for `[0,1,2,3]`.

**Steps**
1. Compute batter_rpb from SR (fallbacks as needed); bowler_rpb from economy proxy or existing WPB.
2. Apply small boosts only when advantage is meaningful.
3. Preserve last-batter mode (odd runs suppressed, no strike swap).

**Acceptance Criteria**
- Good batter vs weak bowler yields more 4s/6s; economy shifts mildly.
- Totals remain balanced; tails still struggle to hit boundaries.

**Quick Tests**
```powershell
python .\testing\match_score_list.py ENG_test.json TBO_VIII.json -n 10 --seed 123
python .\testing\batch_test.py ENG_test.json TBO_VIII.json -n 50 --seed 123 --csv
```

**Metrics**
- Boundary counts per batter vs historical priors.
- Economy changes; ensure no runaway totals.

**Risks / Rollback**
- Excessive boosts can inflate SR unrealistically.
- Cap boosts and add a feature flag to disable boundary uplift.

---

## Phase 4 — Calibration & Edge Cases (Polish)

**Intent**: Make the simulator robust with incomplete data and tune coefficients using batch outputs.

**Design & Steps**
- Statless handling: define neutral floors for players without SR/avg.
- Avoid divide-by-zero with safe denominators.
- Iteratively tune coefficients from Phases 1–3 based on batch outputs.

**Acceptance Criteria**
- Simulator remains stable with squads missing data.
- Batch stats fall within plausible T20/LMS bands (Avg ~25–35, SR ~120–150, Econ ~7–10).

**Quick Tests**
```powershell
python .\testing\batch_test.py ENG_test.json TBO_VIII.json -n 100 --seed 123 --csv
```

**Metrics**
- Global distributions: batting avg/SR and bowling avg/econ across many sims.
- Identify outliers and adjust caps/coefficients.

**Risks / Rollback**
- Over-tuning can reduce variability; prefer gentle adjustments.
- Keep a baseline configuration for easy reset.

---

## Validation Matrix

Track these KPIs per phase:
- Batting: Avg, SR, boundaries per innings.
- Bowling: Econ, wickets/innings, simulated average.
- Over-time: wicket frequency in overs 15–20 (pressure effect).

Use `testing/batch_test.py` CSV exports to review trends.

---

## Feature Flags (Recommended)
- `ENABLE_ADV_WICKET` (Phase 1)
- `ENABLE_PRESSURE` (Phase 2)
- `ENABLE_BOUNDARY_ADV` (Phase 3)

Implement as module-level constants in `simulation_engine.py` to toggle behaviour during tests.

---

## Milestones
- M1: Phase 1 merged; batch sanity within plausible bands.
- M2: Phase 2 merged; late-over tension evident; averages still stable.
- M3: Phase 3 merged; boundary patterns feel more authentic in matchups.
- M4: Phase 4 tuning complete; documentation and defaults updated.

---

## Rollback Strategy
- Keep prior constants and simple wicket formula available behind flags.
- If any phase destabilizes results, disable the flag and revert coefficients.

---

## Notes
- All phases preserve LMS rules (5-ball overs, penalty balls, retirement at 50, free hits).
- Focus on small, testable increments; avoid sweeping refactors.
