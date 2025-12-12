"""
Debug script: Run 10 separate Alpha vs Alpha innings to check for variance
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
all_players_dict = load_players_summary()
team_alpha, team_name = load_team_from_file('Test_Team_Alpha.json', all_players_dict)

# Create match config
config = MatchConfig.default()

print("=" * 100)
print("DEBUG: 10x Alpha vs Alpha Innings with Different Seeds")
print("=" * 100)
print()

for seed in [777, 778, 779, 780, 781, 782, 783, 784, 785, 786]:
    random.seed(seed)
    
    result = simulate_innings(
        batting_team=team_alpha,
        bowling_team=team_alpha,
        match_config=config
    )
    
    batting_runs = result['runs']
    batting_stats = result['batsmen']
    
    avg_runs_per_player = sum(s['runs'] for s in batting_stats.values()) / len(batting_stats)
    
    print(f"Seed {seed}: Total={batting_runs:3d} runs,  Avg per player={avg_runs_per_player:5.2f},  Players dismissed: {sum(1 for s in batting_stats.values() if s['runs'] > 0)}/8")
