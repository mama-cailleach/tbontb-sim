"""
Debug: Check actual balls bowled vs expected
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
team_alpha, _ = load_team_from_file('Test_Team_Alpha.json', all_players_dict)
config = MatchConfig.default()

print("Debug: Balls Bowled Analysis (10 sims, seed 777)")
print(f"{'Seed':<6} {'Runs':<8} {'Balls':<8} {'Wickets':<10} {'Avg Econ':<10} {'Issues':<40}")
print("-" * 100)

random.seed(777)
for sim in range(10):
    result = simulate_innings(
        batting_team=team_alpha,
        bowling_team=team_alpha,
        match_config=config
    )
    
    runs = result['runs']
    balls = result['balls']
    wickets = result['wickets']
    
    # Calculate economy
    overs = balls / 5
    econ = runs / overs if overs > 0 else 0
    
    issues = []
    if balls < 90:
        issues.append(f"Early finish ({balls} balls)")
    if wickets > 8:
        issues.append(f"Too many wickets ({wickets})")
    if econ < 8:
        issues.append(f"Low economy ({econ:.1f})")
    
    issue_str = "; ".join(issues) if issues else "OK"
    
    print(f"{sim:<6} {runs:<8} {balls:<8} {wickets:<10} {econ:<10.2f} {issue_str:<40}")

print()
print("Expected: 100 balls, ~120-140 runs, 6-7 wickets, 9-10 econ")
