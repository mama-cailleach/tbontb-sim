"""
Debug: Check RPB calculations for Team Alpha
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_loader import load_players_summary, load_team_from_file

# Load teams
all_players_dict = load_players_summary()
team_alpha, _ = load_team_from_file('Test_Team_Alpha.json', all_players_dict)

print("Team Alpha - RPB Analysis:")
print(f"{'Name':<25} {'SR%':<8} {'Avg':<8} {'Base RPB':<12} {'Avg Boost':<12} {'Final RPB':<12}")
print("-" * 100)

for player in team_alpha:
    sr = player.get('strike_rate', 0)
    bat_avg = player.get('bat_avg', 0)
    
    # Base RPB
    batsman_rpb = sr / 100.0 if sr > 0 else 0.8
    base_rpb = batsman_rpb
    
    # Average boost
    avg_boost_factor = (1.0 + min(max(bat_avg, 0), 100) / 420.0) if bat_avg else 1.0
    batsman_rpb *= avg_boost_factor
    
    # Check if blank
    is_blank = sr == 0 and bat_avg == 0
    if is_blank:
        batsman_rpb = max(batsman_rpb, 0.35)
    
    print(f"{player['player_name']:<25} {sr:<8.1f} {bat_avg:<8.1f} {base_rpb:<12.4f} {avg_boost_factor:<12.4f} {batsman_rpb:<12.4f}")

print()
print("Expected: RPB should roughly match SR/100 (e.g., 110% SR -> 1.1 RPB)")
print("Interpretation: If RPB ~= 1.1, then bowling 20 overs with ~2.2 runs/over (11 RPB) = 0.65 overs = 3.25 runs")
print("But Alpha batters should score ~20+ per inning, which requires ~1.0 RPB avg across all 8 batters")
