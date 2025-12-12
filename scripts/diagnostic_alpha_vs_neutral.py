"""
Diagnostic: Compare Expected vs Actual Simulation Results for Team Alpha
Run 50 sims and compare to expected projections to identify mismatch sources.
"""

import os
import sys
import random
import json

parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

from data_loader import load_players_summary, load_team_from_file
from match_config import MatchConfig
from simulation_engine import simulate_innings
from output_formatter import OutputConfig

# Load teams
players = load_players_summary()
alpha_team, alpha_name = load_team_from_file('Test_Team_Alpha.json', players)
neutral_team, neutral_name = load_team_from_file('Neutral_Blank_Team.json', players)

print("=" * 100)
print("DIAGNOSTIC: EXPECTED vs ACTUAL - TEAM ALPHA vs NEUTRAL_BLANK (50 Sims, Seed 777)")
print("=" * 100)
print()

match_config = MatchConfig.default()
output_config = OutputConfig.default()

random.seed(777)

alpha_batting_stats = {}
alpha_bowling_stats = {}
neutral_batting_stats = {}
neutral_bowling_stats = {}

for sim in range(50):
    # Sim 1: Alpha bats, Neutral bowls
    output_config.over_summaries = []
    inning1 = simulate_innings(alpha_team, neutral_team, match_config, target=None, output_config=output_config)
    
    # Sim 2: Neutral bats, Alpha bowls
    output_config.over_summaries = []
    target = inning1['runs'] + 1
    inning2 = simulate_innings(neutral_team, alpha_team, match_config, target=target, output_config=output_config)
    
    # Collect Alpha batting (when they're first innings)
    for pid, stats in inning1['batsmen'].items():
        if pid not in alpha_batting_stats:
            alpha_batting_stats[pid] = []
        alpha_batting_stats[pid].append(stats)
    
    # Collect Alpha bowling (when Neutral is batting in inning2)
    for pid, stats in inning2['bowlers'].items():
        if pid not in alpha_bowling_stats:
            alpha_bowling_stats[pid] = []
        alpha_bowling_stats[pid].append(stats)
    
    # Collect Neutral batting (when they're second innings)
    for pid, stats in inning2['batsmen'].items():
        if pid not in neutral_batting_stats:
            neutral_batting_stats[pid] = []
        neutral_batting_stats[pid].append(stats)
    
    # Collect Neutral bowling (when Alpha is batting in inning1)
    for pid, stats in inning1['bowlers'].items():
        if pid not in neutral_bowling_stats:
            neutral_bowling_stats[pid] = []
        neutral_bowling_stats[pid].append(stats)

# Load full player data
with open(os.path.join(parent_dir, 'json', 'TBONTB_players_with_blank.json'), 'r') as f:
    all_players_data = json.load(f)
player_lookup = {p['player_id']: p for p in all_players_data}

print("ALPHA BATTING vs NEUTRAL BOWLING")
print("-" * 100)
print(f"{'Player':<25} {'Hist Avg':<12} {'Sim Avg':<12} {'Hist SR':<12} {'Sim SR':<12} {'Diff Avg':<12}")
print("-" * 100)

total_alpha_runs = 0
total_alpha_balls = 0

for pid, stats_list in sorted(alpha_batting_stats.items()):
    player_ref = next((p for p in alpha_team if p['player_id'] == pid), None)
    if not player_ref:
        continue
    
    hist_avg = player_ref.get('bat_avg', 0)
    hist_sr = player_ref.get('strike_rate', 0)
    
    avg_runs = sum(s['runs'] for s in stats_list) / len(stats_list)
    avg_balls = sum(s['balls'] for s in stats_list) / len(stats_list)
    sim_sr = (avg_runs / avg_balls * 100) if avg_balls > 0 else 0
    
    diff_avg = avg_runs - hist_avg
    
    total_alpha_runs += avg_runs
    total_alpha_balls += avg_balls
    
    print(f"{player_ref['player_name']:<25} {hist_avg:<12.2f} {avg_runs:<12.2f} {hist_sr:<12.2f} {sim_sr:<12.2f} {diff_avg:+.2f}")

alpha_avg_sr = (total_alpha_runs / total_alpha_balls * 100) if total_alpha_balls > 0 else 0
print(f"\n{'TEAM ALPHA BATTING':<25} {'':<12} {'':12} {'':12} {alpha_avg_sr:<12.2f}")
print()

print("ALPHA BOWLING vs NEUTRAL BATTING")
print("-" * 100)
print(f"{'Player':<25} {'Hist Econ':<12} {'Sim Econ':<12} {'Hist Avg':<12} {'Sim Avg':<12} {'Diff Econ':<12}")
print("-" * 100)

total_alpha_bowl_runs = 0
total_alpha_bowl_balls = 0

for pid, stats_list in sorted(alpha_bowling_stats.items()):
    player_ref = next((p for p in alpha_team if p['player_id'] == pid), None)
    if not player_ref:
        continue
    
    player_id_num = int(pid.split('_')[-1])
    full_player = player_lookup.get(player_id_num, {})
    hist_econ = full_player.get('economy', 10.0)
    hist_avg = full_player.get('bowl_avg', 50.0)
    
    avg_runs = sum(s['runs'] for s in stats_list) / len(stats_list)
    avg_balls = sum(s['balls'] for s in stats_list) / len(stats_list)
    sim_econ = (avg_runs / avg_balls * 5) if avg_balls > 0 else 0
    
    # Calculate bowling average (runs conceded per wicket)
    total_wickets = sum(s['wickets'] for s in stats_list)
    avg_wickets = total_wickets / len(stats_list) if total_wickets > 0 else 0
    sim_avg = (avg_runs / avg_wickets) if avg_wickets > 0 else 999
    
    diff_econ = sim_econ - hist_econ
    
    total_alpha_bowl_runs += avg_runs
    total_alpha_bowl_balls += avg_balls
    
    print(f"{player_ref['player_name']:<25} {hist_econ:<12.2f} {sim_econ:<12.2f} {hist_avg:<12.2f} {sim_avg:<12.2f} {diff_econ:+.2f}")

alpha_team_econ = (total_alpha_bowl_runs / total_alpha_bowl_balls * 5) if total_alpha_bowl_balls > 0 else 0
print(f"\n{'TEAM ALPHA BOWLING':<25} {'':12} {alpha_team_econ:<12.2f}")
print()

print("=" * 100)
print("ANALYSIS")
print("=" * 100)
print()
print(f"Alpha Batting:")
print(f"  - Expected: ~16-17 avg for strong batters, ~3-7 for weak")
print(f"  - Actual (vs Neutral): Check above")
print(f"  - Issue: Neutral bowlers weak, should allow MORE runs, not less")
print()
print(f"Alpha Bowling:")
print(f"  - Expected econ: ~9.7-12.5 (depends on player)")
print(f"  - Actual (vs Neutral): Check above")
print(f"  - Issue: Neutral batters heavily clamped, might suppress wicket-taking")
print()
print("Hypothesis:")
print("  1. Neutral_Blank bowlers might be too STRONG (econ logic inverted?)")
print("  2. OR stochastic leakage/fatigue is reducing economy too much")
print("  3. Wicket probability with Neutral batters creates artificial pressure on Alpha bowlers")
print()
