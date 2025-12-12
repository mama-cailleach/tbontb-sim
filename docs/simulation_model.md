# Simulation Model Overview

This document describes the current ball-by-ball simulation logic in `simulation_engine.py` for analyst and design review. It focuses on how per-ball outcomes are generated, what inputs drive them, and where dynamic adjustments occur.

## Key Inputs
- **Match config**: `balls_per_over`, `balls_per_innings` (TBONTB defaults: 5-ball overs, 100 balls).
- **Batter stats** (per player): `strike_rate`, `bat_avg`, `runs`, `balls_faced`, `fours`, `sixes`.
- **Bowler stats** (per player): `economy`, `bowl_avg`, `wickets`, `overs_bowled`, `runs_conceded`.
- **Derived indices**: `SHORT_ID_INDEX` from `data_loader.py` for player lookup (not used in per-ball math).

## Expectations (per innings, per player)
At innings start:
- For each batter:
  - `exp_rpb`: expected runs per ball from historical strike rate (`SR/100`) if SR exists, else None.
  - `exp_runs_inn`: expected runs for the innings from batting average if present, else None.
- For each bowler:
  - `exp_wpb`: expected wickets per ball from historical wickets and overs (if available), else None.
- Statless/blank players (no SR/avg and zeroed counters) produce None expectations.

## Per-Ball Flow (summary)
1) Select bowler by over rotation (up to 8 bowlers chosen from team; preference to those with `overs_bowled > 0`).
2) Identify striker/non-striker; last-batter mode disables odd runs and strike swaps.
3) Compute batter run potential (RPB) and bowling pressure.
4) Compute wicket probability and roll for wicket; else roll for runs.
5) Update totals, strikes, per-over FOW log, ball-by-ball log, and stop early on target chase.

## Batter Run Potential (RPB)
- Base RPB: `strike_rate/100` if present; else `runs/balls_faced` fallback; default 0.8 if no history.
- Skill features:
  - `quality_sr = clamp((SR - 80)/120, 0..1)`
  - `quality_avg = clamp((bat_avg - 15)/35, 0..1)`
  - `bat_skill = 0.5*quality_sr + 0.5*quality_avg`
  - `statless_batter` flag if all key batting stats are missing/zero.
- Uplift/dampen:
  - If `bat_avg` exists: multiply by `(1 + bat_avg/420)` (capped at 100/420).
  - Scale by `(0.35 + 0.55*bat_skill)`; additional 0.80x if `statless_batter`.
  - Clamp: if `exp_rpb` exists and current RPB exceeds `1.5 * exp_rpb`, cap to `1.5 * exp_rpb`.

## Wicket Probability
- Batting advantage: `ba = batsman_rpb / (batsman_rpb + bowler_rpb)`; `bowler_rpb = economy / balls_per_over` or fallback from `runs_conceded/overs_bowled`.
- Base wicket rate: `0.0105 + (1 - ba) * 0.068`.
- Batter protection: `bat_protect = 1 - bat_avg/600` (clamped 0..1).
- Bowler boost: starts at 1.0; adds impact from low `bowl_avg` and wicket volume; capped at **1.00**.
- Economy adjust: `econ_adjust` in **[0.90, 1.10]** via `10 / bowler_econ` with clamps.
- Expectation pressure (dynamic, per ball):
  - Uses `hist_avg`, `hist_sr`, `exp_rpb`, `exp_runs_inn`, and live runs/balls.
  - Adds pressure when batter exceeds historical avg, historical SR, expected runs-so-far (`exp_rpb * balls`), or expected innings runs.
  - Pressure multiplier is additive to wicket_prob (values >1 increase chances of dismissal).
- Final wicket probability: `base * bat_protect * bowl_boost * econ_adjust * pressure`.
  - Statless bowler: no extra damp (multiplier 1.0).
  - Clamped to **[0.012, 0.14]**.
  - **Per-over safeguard**: none yet; dismissals rely on the above pressure plus base floor.

## Run Outcome Distribution
- Uses batter skill and historical boundary rates.
- Boundary priors:
  - Four floor: `max(0.020, four_rate*1.02) * (0.26 + 0.90*bat_skill) + 0.0008`
  - Six floor: `max(0.008, six_rate*1.02) * (0.22 + 1.00*bat_skill) + 0.0006`
- Remaining mass allocated to `[0,1,2,3]` via `base_split = [0.38 - 0.06*skill, 0.34 + 0.05*skill, 0.19 + 0.02*skill, 0.09 + 0.02*skill]` then renormalized.
- Advantage boost: if `ba > 0.5`, boundaries get a small uplift scaled by skill (current small coefficients).
- Last-batter mode: odd runs redirected to 0/2; no strike swaps.

## Logging & Output
- Ball-by-ball events stored when `OutputConfig.ball_by_ball` is true: `over.ball - bowler - to - batter - outcome`.
- Over summaries: per-over score, bowler figures, batters, and FOW list.
- Scorecard: innings totals, batter lines, bowler lines.

## Neutral/Blank Players
- Supplied via `blank_players_summary.json` and `Neutral_Blank` team.
- Statless players yield None expectations, low base RPB scaled by skill floor, no special wicket damp.

## Known Issues / Tuning Targets
- Alpha bowlers remain too stingy (econ ~4–5) vs blanks; wicket floor and boosts still produce low run rates against strong attacks.
- Some batters still above historical averages/SR; expectation clamps and pressure may need further tightening (lower RPB cap factor, higher wicket pressure for SR spikes).
- No per-over escalating wicket pressure yet; could add a small multiplier when an over ends wicketless.
- Economy realism: consider raising econ_adjust range and lowering bowl_boost further for strong bowlers.

## Change Levers (for designers/analysts)
- **Wicket shape**: adjust `base_wicket_prob` intercept/slope, `bat_protect` divisor, caps/floors.
- **Pressure weights**: increase contributions from `over_run_ratio`, SR exceedance, or add per-over wicketless multiplier.
- **Bowler dominance**: lower `bowl_boost` cap, widen `econ_adjust` range to let runs through.
- **Boundary floors**: tweak p4/p6 floors and advantage boosts to move economy and SR.
- **RPB clamps**: lower `1.5 * exp_rpb` cap to reduce runaway hitters.
- **Last batter rules**: currently even-only scoring; can be relaxed if desired.

## Files
- Core logic: `simulation_engine.py`
- Config presets: `match_config.py`
- Output: `output_formatter.py`
- Batch testing: `testing/batch_test.py`
- Player tracker: `Testing/player_performance_tracker.py`
- Data loading: `data_loader.py`

This document should help statisticians and designers identify which parameters to adjust to match target averages, strike rates, wicket frequencies, and economies.
