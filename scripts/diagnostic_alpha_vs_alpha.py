"""
Diagnostic: Alpha vs Alpha (50 Sims, Seed 777)
Eliminates opponent distortion to validate calibration internally.
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
alpha_team1, alpha_name = load_team_from_file('Test_Team_Alpha.json', players)
alpha_team2, _ = load_team_from_file('Test_Team_Alpha.json', players)

print("=" * 100)
print("DIAGNOSTIC: ALPHA vs ALPHA (50 Sims, Seed 777)")
print("=" * 100)
print()

match_config = MatchConfig.default()
output_config = OutputConfig.default()

random.seed(777)

alpha1_batting_stats = {}
alpha1_bowling_stats = {}
alpha2_batting_stats = {}
alpha2_bowling_stats = {}

for sim in range(50):
    # Sim 1: Alpha1 bats, Alpha2 bowls
    output_config.over_summaries = []
    inning1 = simulate_innings(alpha_team1, alpha_team2, match_config, target=None, output_config=output_config)
    
    # Sim 2: Alpha2 bats, Alpha1 bowls
    output_config.over_summaries = []
    target = inning1['runs'] + 1
    inning2 = simulate_innings(alpha_team2, alpha_team1, match_config, target=target, output_config=output_config)
    
    # Collect Alpha1 batting (inning1)
    for pid, stats in inning1['batsmen'].items():
        if pid not in alpha1_batting_stats:
            alpha1_batting_stats[pid] = []
        alpha1_batting_stats[pid].append(stats)
    
    # Collect Alpha1 bowling (inning2)
    for pid, stats in inning2['bowlers'].items():
        if pid not in alpha1_bowling_stats:
            alpha1_bowling_stats[pid] = []
        alpha1_bowling_stats[pid].append(stats)
    
    # Collect Alpha2 batting (inning2)
    for pid, stats in inning2['batsmen'].items():
        if pid not in alpha2_batting_stats:
            alpha2_batting_stats[pid] = []
        alpha2_batting_stats[pid].append(stats)
    
    # Collect Alpha2 bowling (inning1)
    for pid, stats in inning1['bowlers'].items():
        if pid not in alpha2_bowling_stats:
            alpha2_bowling_stats[pid] = []
        alpha2_bowling_stats[pid].append(stats)

# Load full player data
with open(os.path.join(parent_dir, 'json', 'TBONTB_players_with_blank.json'), 'r') as f:
    all_players_data = json.load(f)
player_lookup = {p['player_id']: p for p in all_players_data}

print("ALPHA1 BATTING vs ALPHA2 BOWLING")
print("-" * 100)
print(f"{'Player':<25} {'Hist Avg':<12} {'Sim Avg':<12} {'Hist SR':<12} {'Sim SR':<12} {'Diff':<12}")
print("-" * 100)

total_alpha1_runs = 0
total_alpha1_balls = 0

for pid, stats_list in sorted(alpha1_batting_stats.items()):
    player_ref = next((p for p in alpha_team1 if p['player_id'] == pid), None)
    if not player_ref:
        continue
    
    hist_avg = player_ref.get('bat_avg', 0)
    hist_sr = player_ref.get('strike_rate', 0)
    
    avg_runs = sum(s['runs'] for s in stats_list) / len(stats_list)
    avg_balls = sum(s['balls'] for s in stats_list) / len(stats_list)
    sim_sr = (avg_runs / avg_balls * 100) if avg_balls > 0 else 0
    
    diff = avg_runs - hist_avg
    
    total_alpha1_runs += avg_runs
    total_alpha1_balls += avg_balls
    
    print(f"{player_ref['player_name']:<25} {hist_avg:<12.2f} {avg_runs:<12.2f} {hist_sr:<12.2f} {sim_sr:<12.2f} {diff:+.2f}")

alpha1_avg_sr = (total_alpha1_runs / total_alpha1_balls * 100) if total_alpha1_balls > 0 else 0
alpha1_total_per_inning = total_alpha1_runs * 50  # Total runs per average inning
alpha1_avg_per_player = total_alpha1_runs / len(alpha1_batting_stats)  # Average per player
print(f"\n{'ALPHA1 TOTALS (avg per-player avg)':<25} {'':12} {alpha1_avg_per_player:<12.2f} {'':12} {alpha1_avg_sr:<12.2f}")
print()

print("ALPHA1 BOWLING vs ALPHA2 BATTING")
print("-" * 100)
print(f"{'Player':<25} {'Hist Econ':<12} {'Sim Econ':<12} {'Hist Avg':<12} {'Sim Avg':<12} {'Diff':<12}")
print("-" * 100)

total_alpha1_bowl_runs = 0
total_alpha1_bowl_balls = 0

for pid, stats_list in sorted(alpha1_bowling_stats.items()):
    player_ref = next((p for p in alpha_team1 if p['player_id'] == pid), None)
    if not player_ref:
        continue
    
    player_id_num = int(pid.split('_')[-1])
    full_player = player_lookup.get(player_id_num, {})
    hist_econ = full_player.get('economy', 10.0)
    hist_avg = full_player.get('bowl_avg', 50.0)
    
    avg_runs = sum(s['runs'] for s in stats_list) / len(stats_list)
    avg_balls = sum(s['balls'] for s in stats_list) / len(stats_list)
    sim_econ = (avg_runs / avg_balls * 5) if avg_balls > 0 else 0
    
    total_wickets = sum(s['wickets'] for s in stats_list)
    avg_wickets = total_wickets / len(stats_list) if total_wickets > 0 else 0
    sim_avg = (avg_runs / avg_wickets) if avg_wickets > 0 else 999
    
    diff = sim_econ - hist_econ
    
    total_alpha1_bowl_runs += avg_runs
    total_alpha1_bowl_balls += avg_balls
    
    print(f"{player_ref['player_name']:<25} {hist_econ:<12.2f} {sim_econ:<12.2f} {hist_avg:<12.2f} {sim_avg:<12.2f} {diff:+.2f}")

alpha1_team_econ = (total_alpha1_bowl_runs / total_alpha1_bowl_balls * 5) if total_alpha1_bowl_balls > 0 else 0
print(f"\n{'ALPHA1 BOWLING':<25} {'':12} {alpha1_team_econ:<12.2f}")
print()

print("=" * 100)
print("SUMMARY - ALPHA vs ALPHA")
print("=" * 100)
print()
print(f"Batting (per inning):")
num_players_batting = len(alpha1_batting_stats)
avg_per_player = total_alpha1_runs / num_players_batting
alpha1_total_runs_per_inning = avg_per_player * num_players_batting  # This is just avg_per_player * 8
# Wait, that's circular. Let me think: total_alpha1_runs is already the sum, so:
alpha1_total_runs_per_inning = total_alpha1_runs * num_players_batting  # NO this is wrong too
# Actually: total_alpha1_runs is (sum of all player avg runs) which is already the per-inning total!
print(f"  - Average runs per player: {total_alpha1_runs / num_players_batting:.2f} (expected from model: ~15-20 strong, ~3-7 weak)")
print(f"  - Team total per inning: {total_alpha1_runs:.0f} runs (expected: 120-140)")
print(f"  - Average strike rate: {alpha1_avg_sr:.1f}% (expected: 120-135%)")
print()
print(f"Bowling (per inning):")
print(f"  - Average team economy: {alpha1_team_econ:.2f} runs per 5-ball over (expected: ~9.7-10.9)")
print(f"  - Individual econ range: Check above")
print()
print(f"Interpretation:")
if alpha1_team_econ > 8.0:
    print(f"  [WARN] Economy HIGH - consider tightening bowler calibration")
elif alpha1_team_econ < 6.5:
    print(f"  [WARN] Economy LOW - boundaries may be underspressed")
else:
    print(f"  [OK] Economy in range - calibration balanced for this team composition")

if alpha1_avg_sr < 110:
    print(f"  [WARN] SR TOO LOW - boundaries need uplift")
elif alpha1_avg_sr > 140:
    print(f"  [WARN] SR TOO HIGH - boundary dampening needed")
else:
    print(f"  [OK] SR in range - batting calibration balanced")

print()
