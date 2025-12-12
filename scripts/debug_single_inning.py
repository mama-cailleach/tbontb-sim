"""
Debug script: Run a single Alpha vs Alpha inning with detailed trace
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import random
from data_loader import load_players_summary, load_team_from_file
from match_config import MatchConfig
from simulation_engine import simulate_innings

# Load teams
all_players_dict = load_players_summary()  # Returns dict keyed by player_id
alpha_team_file = os.path.join(os.path.dirname(__file__), '..', 'json', 'teams', 'Test_Team_Alpha.json')

team_alpha, team_name = load_team_from_file('Test_Team_Alpha.json', all_players_dict)

# Set seed for reproducibility
random.seed(777)

# Create match config
config = MatchConfig.default()

print("=" * 100)
print("DEBUG: Single Alpha vs Alpha Inning")
print("=" * 100)
print()

# Simulate one inning
print("ALPHA1 Batting vs ALPHA2 Bowling:")
print("-" * 100)

result = simulate_innings(
    batting_team=team_alpha,
    bowling_team=team_alpha,
    match_config=config
)

batting_runs = result['runs']
batting_stats = result['batsmen']
bowlers_stats = result['bowlers']

print()
print(f"Total Runs: {batting_runs}")
print()
print("Batting Stats by Player:")
print(f"{'Name':<25} {'Runs':<8} {'Balls':<8} {'SR%':<8} {'Avg':<8}")
print("-" * 60)
for pid, stats in sorted(batting_stats.items(), key=lambda x: x[1]['runs'], reverse=True):
    player = all_players_dict.get(pid, {})
    name = player.get('player_name', 'Unknown')[:25]
    runs = stats['runs']
    balls = stats['balls']
    sr = (runs / balls * 100) if balls > 0 else 0
    avg = player.get('bat_avg', 0)
    print(f"{name:<25} {runs:<8} {balls:<8} {sr:<8.1f} {avg:<8.1f}")

print()
print("Over Summaries:")
print("-" * 100)
for over_idx in range(1, 21):
    print(f"Over {over_idx} (balls {over_idx*5-4}-{over_idx*5}): Awaiting detailed output")
