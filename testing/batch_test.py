"""
Batch simulation testing script.
Runs multiple simulations between two teams to validate that player performance
matches their historical averages (batting and bowling).
Uses the new modular architecture.
"""

import json
import os
import sys
import random
from collections import defaultdict

# Add parent directory to path for imports
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

# Import from new modular system
from data_loader import load_players_summary, load_team_from_file
from match_config import MatchConfig
from simulation_engine import simulate_innings
from output_formatter import OutputConfig


def run_batch_simulations(team1_file, team2_file, num_simulations=50, seed=None, players_path=None):
	"""Run multiple simulations and collect statistics."""
	
	if seed is not None:
		random.seed(seed)
	
	# Load players and teams
	players = load_players_summary(players_path)
	if not players:
		print("Failed to load players summary.")
		return None
	
	team1, team1_name = load_team_from_file(team1_file, players)
	team2, team2_name = load_team_from_file(team2_file, players)
	
	if not team1 or not team2:
		print("Failed to load teams.")
		return None
	
	print(f"Running {num_simulations} simulations between {team1_name} and {team2_name}...")
	print()
	
	# Create configurations
	match_config = MatchConfig.default()
	output_config = OutputConfig.default()
	
	# Initialize stats collection
	team1_batting_stats = defaultdict(lambda: {'runs': 0, 'balls': 0, 'dismissals': 0, 'innings': 0})
	team1_bowling_stats = defaultdict(lambda: {'balls': 0, 'runs': 0, 'wickets': 0, 'innings': 0})
	team2_batting_stats = defaultdict(lambda: {'runs': 0, 'balls': 0, 'dismissals': 0, 'innings': 0})
	team2_bowling_stats = defaultdict(lambda: {'balls': 0, 'runs': 0, 'wickets': 0, 'innings': 0})
	
	team1_innings_totals = []
	team2_innings_totals = []
	
	# Run simulations
	for sim_num in range(1, num_simulations + 1):
		# Alternate who bats first
		if sim_num % 2 == 1:
			first_batting = (team1_name, team1)
			second_batting = (team2_name, team2)
		else:
			first_batting = (team2_name, team2)
			second_batting = (team1_name, team1)
		
		# Reset output config for each match
		output_config.over_summaries = []
		
		# Simulate first innings
		first = simulate_innings(first_batting[1], second_batting[1], match_config, 
								  target=None, output_config=output_config)
		
		# Reset for second innings
		output_config.over_summaries = []
		
		# Simulate second innings (with target)
		target_score = first['runs'] + 1
		second = simulate_innings(second_batting[1], first_batting[1], match_config,
								   target=target_score, output_config=output_config)
		
		# Collect stats for team1
		if first_batting[0] == team1_name:
			team1_innings_totals.append(first['runs'])
			for pid, stats in first['batsmen'].items():
				team1_batting_stats[pid]['runs'] += stats['runs']
				team1_batting_stats[pid]['balls'] += stats['balls']
				if stats['dismissed']:
					team1_batting_stats[pid]['dismissals'] += 1
				team1_batting_stats[pid]['innings'] += 1
			for pid, stats in second['bowlers'].items():
				if stats['balls'] > 0:
					team1_bowling_stats[pid]['balls'] += stats['balls']
					team1_bowling_stats[pid]['runs'] += stats['runs']
					team1_bowling_stats[pid]['wickets'] += stats['wickets']
					team1_bowling_stats[pid]['innings'] += 1
			
			team2_innings_totals.append(second['runs'])
			for pid, stats in second['batsmen'].items():
				team2_batting_stats[pid]['runs'] += stats['runs']
				team2_batting_stats[pid]['balls'] += stats['balls']
				if stats['dismissed']:
					team2_batting_stats[pid]['dismissals'] += 1
				team2_batting_stats[pid]['innings'] += 1
			for pid, stats in first['bowlers'].items():
				if stats['balls'] > 0:
					team2_bowling_stats[pid]['balls'] += stats['balls']
					team2_bowling_stats[pid]['runs'] += stats['runs']
					team2_bowling_stats[pid]['wickets'] += stats['wickets']
					team2_bowling_stats[pid]['innings'] += 1
		else:
			team2_innings_totals.append(first['runs'])
			for pid, stats in first['batsmen'].items():
				team2_batting_stats[pid]['runs'] += stats['runs']
				team2_batting_stats[pid]['balls'] += stats['balls']
				if stats['dismissed']:
					team2_batting_stats[pid]['dismissals'] += 1
				team2_batting_stats[pid]['innings'] += 1
			for pid, stats in second['bowlers'].items():
				if stats['balls'] > 0:
					team2_bowling_stats[pid]['balls'] += stats['balls']
					team2_bowling_stats[pid]['runs'] += stats['runs']
					team2_bowling_stats[pid]['wickets'] += stats['wickets']
					team2_bowling_stats[pid]['innings'] += 1
			
			team1_innings_totals.append(second['runs'])
			for pid, stats in second['batsmen'].items():
				team1_batting_stats[pid]['runs'] += stats['runs']
				team1_batting_stats[pid]['balls'] += stats['balls']
				if stats['dismissed']:
					team1_batting_stats[pid]['dismissals'] += 1
				team1_batting_stats[pid]['innings'] += 1
			for pid, stats in first['bowlers'].items():
				if stats['balls'] > 0:
					team1_bowling_stats[pid]['balls'] += stats['balls']
					team1_bowling_stats[pid]['runs'] += stats['runs']
					team1_bowling_stats[pid]['wickets'] += stats['wickets']
					team1_bowling_stats[pid]['innings'] += 1
		
		# Progress indicator
		if sim_num % 10 == 0:
			print(f"Completed {sim_num}/{num_simulations} simulations...")
	
	print(f"Completed all {num_simulations} simulations.\n")
	
	return {
		'team1': {
			'name': team1_name,
			'team': team1,
			'batting_stats': team1_batting_stats,
			'bowling_stats': team1_bowling_stats,
			'innings_totals': team1_innings_totals,
		},
		'team2': {
			'name': team2_name,
			'team': team2,
			'batting_stats': team2_batting_stats,
			'bowling_stats': team2_bowling_stats,
			'innings_totals': team2_innings_totals,
		},
		'num_simulations': num_simulations,
	}


def print_report(results):
	"""Print detailed statistical report comparing simulation vs historical performance."""
	
	print("=" * 100)
	print("BATCH SIMULATION REPORT")
	print("=" * 100)
	print()
	
	for team_key in ['team1', 'team2']:
		team_data = results[team_key]
		team_name = team_data['name']
		team = team_data['team']
		
		print(f"\n{'=' * 100}")
		print(f"TEAM: {team_name}")
		print(f"{'=' * 100}\n")
		
		# Innings totals summary
		totals = team_data['innings_totals']
		avg_total = sum(totals) / len(totals) if totals else 0
		min_total = min(totals) if totals else 0
		max_total = max(totals) if totals else 0
		print(f"INNINGS SUMMARY ({len(totals)} innings):")
		print(f"  Average Total: {avg_total:.1f}")
		print(f"  Min Total: {min_total}")
		print(f"  Max Total: {max_total}")
		print()
		
		# Batting statistics
		print("BATTING PERFORMANCE:")
		print(f"{'Player':<30} {'Inns':>5} {'Runs':>6} {'Balls':>6} {'Sim Avg':>8} {'Sim SR':>8} | {'Hist Avg':>8} {'Hist SR':>8} | {'Avg Diff':>9} {'SR Diff':>8}")
		print("-" * 150)
		
		for p in team:
			pid = p['player_id']
			pname = p['player_name']
			sim_stats = team_data['batting_stats'][pid]
			
			if sim_stats['innings'] > 0:
				sim_avg = sim_stats['runs'] / sim_stats['dismissals'] if sim_stats['dismissals'] > 0 else sim_stats['runs']
				sim_sr = (sim_stats['runs'] / sim_stats['balls'] * 100) if sim_stats['balls'] > 0 else 0
				
				hist_avg = p.get('bat_avg') or 0
				hist_sr = p.get('strike_rate') or 0
				
				avg_diff = sim_avg - hist_avg if hist_avg > 0 else 0
				sr_diff = sim_sr - hist_sr if hist_sr > 0 else 0
				
				print(f"{pname:<30} {sim_stats['innings']:>5} {sim_stats['runs']:>6} {sim_stats['balls']:>6} "
				      f"{sim_avg:>8.2f} {sim_sr:>8.2f} | {hist_avg:>8.2f} {hist_sr:>8.2f} | "
				      f"{avg_diff:>+9.2f} {sr_diff:>+8.2f}")
		
		print()
		
		# Bowling statistics
		print("BOWLING PERFORMANCE:")
		print(f"{'Player':<30} {'Inns':>5} {'Overs':>7} {'Runs':>6} {'Wkts':>5} {'Sim Avg':>9} {'Sim Econ':>9} | {'Hist Avg':>9} {'Hist Econ':>9} | {'Avg Diff':>10} {'Econ Diff':>10}")
		print("-" * 160)
		
		for p in team:
			pid = p['player_id']
			pname = p['player_name']
			sim_stats = team_data['bowling_stats'][pid]
			
			if sim_stats['innings'] > 0 and sim_stats['balls'] > 0:
				overs = sim_stats['balls'] // 5
				balls_rem = sim_stats['balls'] % 5
				overs_str = f"{overs}.{balls_rem}"
				
				sim_avg = sim_stats['runs'] / sim_stats['wickets'] if sim_stats['wickets'] > 0 else 999.0
				sim_econ = (sim_stats['runs'] / sim_stats['balls'] * 5) if sim_stats['balls'] > 0 else 0
				
				hist_avg = p.get('bowl_avg') or 0
				hist_econ = p.get('economy') or 0
				
				avg_diff = sim_avg - hist_avg if hist_avg > 0 and sim_stats['wickets'] > 0 else 0
				econ_diff = sim_econ - hist_econ if hist_econ > 0 else 0
				
				avg_display = f"{sim_avg:.2f}" if sim_avg < 999 else "N/A"
				hist_avg_display = f"{hist_avg:.2f}" if hist_avg > 0 else "N/A"
				avg_diff_display = f"{avg_diff:+.2f}" if avg_diff != 0 and sim_avg < 999 else "N/A"
				
				print(f"{pname:<30} {sim_stats['innings']:>5} {overs_str:>7} {sim_stats['runs']:>6} {sim_stats['wickets']:>5} "
				      f"{avg_display:>9} {sim_econ:>9.2f} | {hist_avg_display:>9} {hist_econ:>9.2f} | "
				      f"{avg_diff_display:>10} {econ_diff:>+10.2f}")
		
		print()
	
	print("=" * 100)
	print("INTERPRETATION GUIDE:")
	print("  - Sim Avg/SR/Econ: Performance in these simulations")
	print("  - Hist Avg/SR/Econ: Historical performance from player records")
	print("  - Diff columns: Positive means simulated performance is HIGHER than historical")
	print("  - For batting: Higher avg/SR is better; for bowling: Lower avg/econ is better")
	print("  - Small differences (<10-15%) suggest the model is working well")
	print("=" * 100)


def main():
	import argparse
	
	parser = argparse.ArgumentParser(description='Batch simulation tester for cricket simulator')
	parser.add_argument('team1', help='Filename of first team in json/teams/ (e.g., Test_Team_Alpha.json)')
	parser.add_argument('team2', help='Filename of second team in json/teams/ (e.g., Team_Beta_Squad.json)')
	parser.add_argument('-n', '--num-sims', type=int, default=50, help='Number of simulations to run (default: 50)')
	parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
	parser.add_argument('--csv', action='store_true', help='Export results to CSV file')
	parser.add_argument('--players-file', type=str, help='Path to alternate players summary JSON (e.g., combined with blanks)')
	
	args = parser.parse_args()
	
	results = run_batch_simulations(args.team1, args.team2, args.num_sims, args.seed, args.players_file)
	
	if results:
		print_report(results)
		
		if args.csv:
			# Export to CSV
			csv_file = f"batch_test_{results['team1']['name']}_{results['team2']['name']}_{args.num_sims}sims.csv"
			csv_file = csv_file.replace(' ', '_')
			csv_dir = os.path.join(os.path.dirname(__file__), 'csv_exports')
			csv_path = os.path.join(csv_dir, csv_file)
			
			with open(csv_path, 'w', encoding='utf-8') as f:
				# Header
				f.write("Team,Player,Role,Innings,Runs,Balls,Sim_Avg,Sim_SR,Hist_Avg,Hist_SR,Avg_Diff,SR_Diff,")
				f.write("Bowl_Innings,Overs,Runs_Conc,Wickets,Sim_Bowl_Avg,Sim_Econ,Hist_Bowl_Avg,Hist_Econ,Bowl_Avg_Diff,Econ_Diff\n")
				
				for team_key in ['team1', 'team2']:
					team_data = results[team_key]
					team_name = team_data['name']
					team = team_data['team']
					
					for p in team:
						pid = p['player_id']
						pname = p['player_name']
						
						# Batting stats
						bat_stats = team_data['batting_stats'][pid]
						sim_bat_avg = bat_stats['runs'] / bat_stats['dismissals'] if bat_stats['dismissals'] > 0 else bat_stats['runs']
						sim_sr = (bat_stats['runs'] / bat_stats['balls'] * 100) if bat_stats['balls'] > 0 else 0
						hist_avg = p.get('bat_avg') or 0
						hist_sr = p.get('strike_rate') or 0
						avg_diff = sim_bat_avg - hist_avg if hist_avg > 0 else 0
						sr_diff = sim_sr - hist_sr if hist_sr > 0 else 0
						
						# Bowling stats
						bowl_stats = team_data['bowling_stats'][pid]
						if bowl_stats['balls'] > 0:
							overs_bowled = bowl_stats['balls'] / 5.0
							sim_bowl_avg = bowl_stats['runs'] / bowl_stats['wickets'] if bowl_stats['wickets'] > 0 else 0
							sim_econ = (bowl_stats['runs'] / bowl_stats['balls'] * 5) if bowl_stats['balls'] > 0 else 0
							hist_bowl_avg = p.get('bowl_avg') or 0
							hist_econ = p.get('economy') or 0
							bowl_avg_diff = sim_bowl_avg - hist_bowl_avg if hist_bowl_avg > 0 and bowl_stats['wickets'] > 0 else 0
							econ_diff = sim_econ - hist_econ if hist_econ > 0 else 0
						else:
							overs_bowled = 0
							sim_bowl_avg = 0
							sim_econ = 0
							hist_bowl_avg = 0
							hist_econ = 0
							bowl_avg_diff = 0
							econ_diff = 0
						
						f.write(f"{team_name},{pname},All-rounder,{bat_stats['innings']},{bat_stats['runs']},{bat_stats['balls']},")
						f.write(f"{sim_bat_avg:.2f},{sim_sr:.2f},{hist_avg:.2f},{hist_sr:.2f},{avg_diff:.2f},{sr_diff:.2f},")
						f.write(f"{bowl_stats['innings']},{overs_bowled:.1f},{bowl_stats['runs']},{bowl_stats['wickets']},")
						f.write(f"{sim_bowl_avg:.2f},{sim_econ:.2f},{hist_bowl_avg:.2f},{hist_econ:.2f},{bowl_avg_diff:.2f},{econ_diff:.2f}\n")
			
			print(f"\nResults exported to {csv_path}")


if __name__ == '__main__':
	main()
