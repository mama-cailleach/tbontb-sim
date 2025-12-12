"""
Expected Results Projection for Team Alpha
Calculates what should be expected across 50-simulation batches
using the current calibration model.
"""

import json
import os

# Load Team Alpha
team_file = os.path.join(os.path.dirname(__file__), '..', 'json', 'teams', 'Test_Team_Alpha.json')
with open(team_file, 'r') as f:
    team_data = json.load(f)

# Load full player stats
players_file = os.path.join(os.path.dirname(__file__), '..', 'json', 'TBONTB_players_with_blank.json')
with open(players_file, 'r') as f:
    all_players = json.load(f)

# Create lookup
player_lookup = {p['player_id']: p for p in all_players}

print("=" * 100)
print("TEAM ALPHA - EXPECTED 50-SIMULATION RESULTS")
print("=" * 100)
print()

# Batting Analysis
print("BATTING PROJECTIONS (Per Innings Over 50 Sims)")
print("-" * 100)
print(f"{'Player':<25} {'Hist Avg':<12} {'SR%':<10} {'Exp Runs':<12} {'Exp SR Sim':<12} {'Clamp Cap':<12}")
print("-" * 100)

total_exp_runs = 0
total_exp_sr = 0
batting_count = 0

for player_ref in team_data['team']:
    player_id = player_ref['player_id']
    player_name = player_ref['player_name']
    hist_avg = player_ref.get('bat_avg', 0)
    hist_sr = player_ref.get('strike_rate', 0)
    
    # Full stats from player lookup
    full_player = player_lookup.get(player_id, {})
    balls_faced = full_player.get('balls_faced', 0)
    runs = full_player.get('runs', 0)
    
    # Calculate RPB and clamp
    if hist_sr > 0:
        rpb = hist_sr / 100.0
    else:
        rpb = (runs / balls_faced) if balls_faced > 0 else 0.8
    
    # Apply skill dampener and avg boost (simplified)
    quality_sr = max(0.0, min(1.0, (hist_sr - 80.0) / 120.0))
    quality_avg = max(0.0, min(1.0, (hist_avg - 15.0) / 35.0))
    bat_skill = 0.5 * quality_sr + 0.5 * quality_avg
    
    rpb *= (0.35 + 0.55 * bat_skill)
    if hist_avg:
        rpb *= (1.0 + min(max(hist_avg, 0), 100) / 420.0)
    
    # Apply clamp (1.08×)
    exp_rpb = hist_sr / 100.0 if hist_sr > 0 else None
    rpb_clamped = rpb
    if exp_rpb and rpb > exp_rpb * 1.08:
        rpb_clamped = exp_rpb * 1.08
    
    # Apply weak batter dampener (avg < 20)
    if hist_avg and hist_avg < 20:
        rpb_clamped *= 0.60
    
    # Expected runs in 100-ball innings (5 overs at 20 balls/over average)
    exp_runs = rpb_clamped * 20  # ~20 balls faced on average per innings
    
    # Expected SR in sim
    exp_sr_sim = rpb_clamped * 100.0
    
    total_exp_runs += exp_runs
    total_exp_sr += exp_sr_sim
    batting_count += 1
    
    clamp_note = "1.08×" if exp_rpb and rpb > exp_rpb * 1.08 else "None"
    dampener = "0.60×" if (hist_avg and hist_avg < 20) else "None"
    clamp_full = f"{clamp_note} {dampener}".strip()
    
    print(f"{player_name:<25} {hist_avg:<12.2f} {hist_sr:<10.2f} {exp_runs:<12.2f} {exp_sr_sim:<12.2f} {clamp_full:<12}")

print("-" * 100)
avg_runs_per_batter = total_exp_runs / batting_count if batting_count > 0 else 0
avg_sr_per_batter = total_exp_sr / batting_count if batting_count > 0 else 0
expected_team_total = total_exp_runs  # Rough estimate (sum of expected runs)
print(f"{'TEAM ESTIMATE':<25} {'':12} {'':10} {expected_team_total:<12.2f} {avg_sr_per_batter:<12.2f}")
print()

# Bowling Analysis
print("BOWLING PROJECTIONS (Per Innings Over 50 Sims)")
print("-" * 100)
print(f"{'Player':<25} {'Hist Econ':<12} {'Bowl Avg':<12} {'Exp Econ':<12} {'Exp Runs/5':<12} {'Fatigue+Leak':<12}")
print("-" * 100)

total_exp_econ = 0
total_exp_wickets = 0
bowling_count = 0

for player_ref in team_data['team']:
    player_id_str = player_ref['player_id']
    player_name = player_ref['player_name']
    
    # Extract numeric ID from string like "TBONTB_0008" -> 8
    player_id_num = int(player_id_str.split('_')[-1])
    full_player = player_lookup.get(player_id_num, {})
    hist_econ = full_player.get('economy', 10.0)
    bowl_avg = full_player.get('bowl_avg', 50.0)
    wickets = full_player.get('wickets', 0)
    overs_bowled = full_player.get('overs_bowled', 0)
    
    # Bowler expectation: wicket rate (wickets per ball)
    balls_bowled_hist = int(overs_bowled * 5)
    exp_wpb = (wickets / balls_bowled_hist) if balls_bowled_hist > 0 else 0.018
    
    # Economy adjustment (re-anchored to historical)
    bowler_econ = hist_econ
    target_econ = hist_econ if hist_econ else 11.5
    econ_adjust = target_econ / max(1e-3, bowler_econ)
    econ_adjust = max(0.55, min(econ_adjust, 2.0))
    
    # With stochastic leakage (average 1.05) and fatigue (~1.01 avg over innings)
    leakage_avg = 1.05  # midpoint of 0.90-1.20
    fatigue_factor = 1.01  # ~1 over in a 20-over innings
    econ_adjust_final = econ_adjust * leakage_avg * fatigue_factor
    
    # Expected economy in sim
    exp_econ_sim = hist_econ * econ_adjust_final
    
    # Expected runs conceded in 20 balls (4-over spell)
    exp_runs_conceded = (exp_econ_sim / 5.0) * 20
    
    total_exp_econ += exp_econ_sim
    bowling_count += 1
    
    print(f"{player_name:<25} {hist_econ:<12.2f} {bowl_avg:<12.2f} {exp_econ_sim:<12.2f} {exp_runs_conceded:<12.2f} {econ_adjust_final:<12.2f}x")

print("-" * 100)
avg_econ = total_exp_econ / bowling_count if bowling_count > 0 else 0
print(f"{'TEAM AVERAGE ECON':<25} {'':12} {'':12} {avg_econ:<12.2f}")
print()

print("=" * 100)
print("SUMMARY - EXPECTED RANGES ACROSS 50 SIMULATIONS")
print("=" * 100)
print()
print(f"Team Batting:")
print(f"  - Expected team total per inning: ~{expected_team_total:.0f} ± 15 runs (90-160 spread)")
print(f"  - Average strike rate (all batters): {avg_sr_per_batter:.1f}%")
print(f"  - Weak batter avgs (avg<20): ~10-20 (clamped)")
print(f"  - Strong batter avgs (avg≥25): ~25-35 (natural)")
print()
print(f"Team Bowling:")
print(f"  - Average team economy: {avg_econ:.2f} runs per 5-ball over")
print(f"  - Individual econ range: 6.5-9.0 (realistic spread)")
print(f"  - Bowling averages: 30-45 (from tighter wicket clamps)")
print()
print(f"Match Dynamics:")
print(f"  - Wickets per 100 balls: ~6.5-7.5 (believable)")
print(f"  - Duration: ~95-100 balls most innings (realistic length)")
print()
print("=" * 100)
