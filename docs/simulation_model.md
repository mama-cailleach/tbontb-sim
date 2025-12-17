# Simulation Model Overview

This document describes the current ball-by-ball simulation logic in `simulation_engine.py` for analyst and design review. It focuses on how per-ball outcomes are generated, what inputs drive them, and where dynamic adjustments occur.

## Key Inputs
- **Match config**: `balls_per_over`, `balls_per_innings` (LMS defaults: 5-ball overs, 100 balls, retirement_threshold=50).
- **Batter stats** (per player): `strike_rate`, `bat_avg`, `fours`, `sixes`, `balls_faced`.
- **Bowler stats** (per player): `wickets`, `overs_bowled`.
- **Team config**: `captain` and `wicketkeeper` IDs (keeper excluded from bowling, credited for stumpings).

## Per-Ball Flow (summary)
1) Select bowler by over rotation (up to 8 bowlers chosen from team; preference to those with `overs_bowled > 0`).
2) Identify striker/non-striker; last-batter mode disables odd runs and strike swaps.
3) Compute batter run potential (RPB) and bowling pressure.
4) Compute wicket probability and roll for wicket; else roll for runs.
5) Update totals, strikes, per-over FOW log, ball-by-ball log, and stop early on target chase.

## Batter Run Potential (RPB)
- Base RPB: `strike_rate/100` if present; else `runs/balls_faced` fallback; default 0.8 if no history.
- Skill features
1) **Penalty ball check** (4% chance): Wide or no-ball; adds runs (first penalty +1, subsequent +3 except last over), counts toward batter balls faced but not bowler legal balls. No-balls trigger free hits.
2) **Select bowler** by over rotation (up to 8 bowlers chosen from team; preference to those with `overs_bowled > 0`; excludes wicketkeeper).
3) **Identify striker/non-striker**; last-batter mode when only one not-out batter remains (disables odd runs and strike swaps).
4) **Compute wicket probability** from batter and bowler skills; roll for dismissal (unless free hit active).
5) **If not out**: roll for runs from distribution based on boundary rates and bat_skill.
6) **LMS retirement**: If batter reaches 50 runs (first time) and replacement exists, retire to back of queue.
7) **Update totals**, strikes, per-over FOW log, ball-by-ball log; check target chase.
8) **Over ends** after 5 legal deliveries (penalty balls don't count toward legal count).

## Batting Skill
- `bat_skill = clamp((strike_rate - 70) / 90, 0..1)`
  - Lower bound: SR 70 → skill 0.0
  - Upper bound: SR 160 → skill 1.0
- Used to adjust boundary probabilities and run distribution.

## Bowling Skill
- `bowler_wpb = wickets / (overs_bowled * balls_per_over)` (default 0.018 if no history)
- `bowl_skill = clamp((bowler_wpb - 0.01) / 0.04, 0..1)`
- Used to compute wicket probability.

## Wicket Probability
- Base formula: `0.02 + (bowl_skill * 0.07) - (bat_skill * 0.03)`
- Clamped to **[0.01, 0.12]** (1% to 12% per legal delivery).
- No additional dynamic pressure or expectation tracking.
- Free hits: wickets disabled (but runs still scored)
Outcome space: `[0, 1, 2, 3, 4, 6]`
- Boundary base probabilities:
  - `four_rate = fours / balls_faced` (default 0.03 if no history)
  - `six_rate = sixes / balls_faced` (default 0.01 if no history)
  - `p4 = max(0.035, four_rate * 1.1 + bat_skill * 0.02)` (plus 0.004 bonus if boundary_hint > 40)
  - `p6 = max(0.015, six_rate * 1.1 + bat_skill * 0.01)` (plus 0.003 bonus if boundary_hint > 40)
- Remaining mass allocated to `[0,1,2,3]` via fixed split: `[0.30, 0.38, 0.20, 0.12]` of the non-boundary probability.
- **Last-batter mode**: odd runs (1, 3) redistributed to even outcomes (0, 2) at 60%/40% split; no strike rotation
- SuMS Format Rules
- **Penalty balls**: First penalty in an over: +1 run; subsequent penalties: +3 runs (except last over where all penalties are +1).
  - Penalty balls count toward batter's balls faced but not bowler's legal ball count.
  - No-balls trigger free hits (next legal delivery cannot result in wicket).
  - Free hit carries to next over if no-ball occurs on 5th+ legal ball.
- **Retirement**: Batters retire at 50 runs (configurable via `retirement_threshold` in match_config).
  - Retired batters move to back of batting queue and can return if wickets fall.
  - Retirement displayed inline: `"1 run - Retired on 50"`.
  - Only retires once per batter (tracked via `retired_once` flag).
- **Over counting**: Overs end after 5 legal deliveries (tracked via `legal_balls_in_over`).
  - Penalty balls increment display ball number but not legal count.
  - Overs display uses `legal_balls_bowled` for accurate 20.0 format.

## Dismissal Types
- **Bowled** (b bowler), **Caught** (c fielder b bowler), **Caught & Bowled** (c&b bowler)
- **Stumped** (st † keeper) — keeper identified via `keeper_id` parameter; credited for stumping only
- **Run Out** (run out fielder) — not credited to bowler
- **LBW** (lbw b bowler)
- Keeper is excluded from bowling selection via `select_bowlers_from_team(team, keeper_id)`.

## Output Formatting
- **Ball-by-ball** mode: `over.ball - bowler - to - batter - outcome`
  - Singular/plural runs: "1 run" vs "2 runs" (applies to scoring and penalty events).
- **Over summaries**: per-over score, runs, wickets, bowler figures, batters at crease, FOW.
- **Core logic**: `simulation_engine.py` — ball-by-ball simulator, wicket/run calculations, LMS rules
- **Config presets**: `match_config.py` — match types (T20, LMS, OD, FIRST_CLASS), simulation styles, team mindsets
- **Output**: `output_formatter.py` — scorecard formatting, over summaries, JSON export
- **Batch testing**: `testing/batch_test.py` — performance validation (compare sim vs historical stats)
- **Score list**: `testing/match_score_list.py` — quick one-line match summaries for regression testing
- **Data loading**: `data_loader.py` — squad/team loading, player ID normalization
- **Team builder**: `team_builder.py` — interactive team creation with captain/keeper selection

---

## Future Ideas

These features were explored in earlier calibration versions but are not currently implemented. They may be valuable for future realism tuning:

### Dynamic Expectation Tracking
- **Per-innings expectations**: Track `exp_rpb` (expected runs per ball from SR/100), `exp_runs_inn` (from batting average), `exp_wpb` (expected wickets per ball).
- **Live pressure adjustments**: Increase wicket probability when batter exceeds historical SR, avg, or expected runs-so-far.
- **Pressure multipliers**: Add per-ball pressure that scales with over-performance (e.g., SR 20% above historical).

### Advanced Wicket Probability Model
- **Batting advantage**: `ba = batsman_rpb / (batsman_rpb + bowler_rpb)` to compute relative strength.
- **Batter protection**: `bat_protect = 1 - bat_avg/600` to reduce dismissal chance for high-average batters.
- **Bowler boost**: Scale wicket chance based on bowling average and wicket-taking history.
- **Economy adjustment**: `econ_adjust` range [0.90, 1.10] to account for bowler economy rate.
- **Per-over safeguards**: Escalating wicket pressure when overs end wicketless.

### Batting Advantage in Run Distribution
- **RPB-based uplift**: If `ba > 0.5`, boost boundary probabilities proportional to batting advantage.
- **Skill scaling**: More refined boundary rate adjustments using `quality_sr` and `quality_avg` indices.
- **Dynamic RPB clamps**: Cap batter RPB at `1.5 * exp_rpb` to prevent runaway performance.

### Statless/Blank Player Handling
- **Neutral players**: Support for `blank_players_summary.json` with zero/minimal stats.
- **Statless flags**: Automatic detection and dampening for players with no historical data.
- **Fallback distributions**: Use league-average rates for batters/bowlers without history.

### Calibration Tooling
- **Target matching**: Tune parameters to match desired batting avg/SR and bowling avg/economy distributions.
- **Per-over analysis**: Track wicket rates and run rates per over to identify imbalances.
- **Player-level tracking**: `testing/player_performance_tracker.py` for longitudinal performance analysis.
- **CSV exports**: Detailed stat breakdowns for external analysis and visualization.

These ideas can be layered back into the simulation engine if realism tuning or historical stat matching becomes a priority
- Player tracker: `Testing/player_performance_tracker.py`
- Data loading: `data_loader.py`

This document should help statisticians and designers identify which parameters to adjust to match target averages, strike rates, wicket frequencies, and economies.
