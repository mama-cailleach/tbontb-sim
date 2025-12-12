"""
Debug: Check bowler economy scaling factors
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random
from data_loader import load_players_summary, load_team_from_file

# Load teams
all_players_dict = load_players_summary()
team_alpha, _ = load_team_from_file('Test_Team_Alpha.json', all_players_dict)

print("Team Alpha Bowlers - Economy Analysis:")
print(f"{'Name':<25} {'Hist Econ':<12} {'Target Econ':<15} {'Adj Ratio':<12} {'With Leak':<12}")
print("-" * 100)

for bowler in team_alpha:
    hist_econ = bowler.get('economy', 10.0)
    target_econ = hist_econ if hist_econ else 11.5
    adj_ratio = target_econ / max(1e-3, hist_econ)
    adj_ratio = max(0.55, min(adj_ratio, 2.0))  # Clamp
    
    leakage_avg = 1.05  # midpoint of 0.90-1.20
    fatigue_factor = 1.01  # Average over an inning
    adj_with_leak = adj_ratio * leakage_avg * fatigue_factor
    
    print(f"{bowler['player_name']:<25} {hist_econ:<12.2f} {target_econ:<15.2f} {adj_ratio:<12.3f} {adj_with_leak:<12.3f}")

print()
print("If econ_adjust_run ≈ 1.06×, then:")
print("  - Dot balls: multiplied by 1/1.06 = 0.943× (fewer dots)")
print("  - Boundary balls (1-6): multiplied by 1.06× (more runs)")
print("  - Expected economy: (runs * 1.06) / (balls * avg_overs_per_100balls) = should increase economy")
print()
print("But we're seeing economy DECREASE from 9-10 to 6.3. Why?")
print()
print("Hypothesis 1: Wickets reduce balls bowled, so econ = runs / (overs * 5)")
print("              If overs drop faster than runs, econ drops.")
print()
print("Hypothesis 2: Base run distribution is too heavily weighted to dots,")
print("              so even with 1.06× uplift, it's still suppressed.")
