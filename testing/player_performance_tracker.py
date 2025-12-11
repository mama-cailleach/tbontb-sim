"""
Player Performance Tracker - Per-Innings Analysis

Runs multiple simulations and tracks individual player performance
inning by inning. Allows filtering by:
  - Player (by name or player_id)
  - Stat type (batting runs, strike rate, dismissal method, bowling economy, etc.)
  - Team
"""

import os
import sys
import random
import argparse
from collections import defaultdict

# Add parent directory to path for imports
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

# Import from modular system
from data_loader import load_players_summary, load_team_from_file
from match_config import MatchConfig
from simulation_engine import simulate_innings
from output_formatter import OutputConfig


def find_player_in_team(team, search_term):
	"""Find player in team by name or player_id."""
	search_lower = search_term.lower()
	
	for player in team:
		if (search_lower in player['player_name'].lower() or 
		    search_lower in player['player_id'].lower() or
		    player['player_id'] == search_term):
			return player
	return None


def run_player_tracking(team1_file, team2_file, player_search, stat_type='batting_runs', 
					   num_simulations=50, seed=None):
	"""
	Run simulations and track a specific player's performance.
	
	Args:
		team1_file: First team filename
		team2_file: Second team filename
		player_search: Player name or ID to track
		stat_type: Type of stat to track
			- 'batting_runs': Runs scored per inning
			- 'batting_balls': Balls faced per inning
			- 'batting_sr': Strike rate per inning
			- 'batting_dismissals': Whether dismissed (0=not out, 1=dismissed)
			- 'bowling_economy': Economy rate per inning bowled
			- 'bowling_runs': Runs conceded per inning
			- 'bowling_wickets': Wickets per inning
		num_simulations: Number of simulations
		seed: Random seed for reproducibility
	"""
	
	if seed is not None:
		random.seed(seed)
	
	# Load players and teams
	players = load_players_summary()
	if not players:
		print("Failed to load players summary.")
		return None
	
	team1, team1_name = load_team_from_file(team1_file, players)
	team2, team2_name = load_team_from_file(team2_file, players)
	
	if not team1 or not team2:
		print("Failed to load teams.")
		return None
	
	# Find player in either team
	target_player = find_player_in_team(team1, player_search)
	target_team_name = team1_name
	if not target_player:
		target_player = find_player_in_team(team2, player_search)
		target_team_name = team2_name
	
	if not target_player:
		print(f"Player '{player_search}' not found in either team.")
		return None
	
	player_id = target_player['player_id']
	player_name = target_player['player_name']
	
	print(f"Tracking {player_name} ({player_id})")
	print(f"Team: {target_team_name}")
	print(f"Stat: {stat_type}")
	print(f"Simulations: {num_simulations}")
	print(f"Seed: {seed if seed else 'random'}")
	print()
	
	# Create configurations
	match_config = MatchConfig.default()
	output_config = OutputConfig.default()
	
	# Track performance
	performance_log = []
	innings_count = 0
	
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
		
		# Simulate second innings
		target_score = first['runs'] + 1
		second = simulate_innings(second_batting[1], first_batting[1], match_config,
								   target=target_score, output_config=output_config)
		
		# Track player's performance in each inning if they played
		# First inning
		if first_batting[0] == target_team_name and player_id in first['batsmen']:
			innings_count += 1
			stats = first['batsmen'][player_id]
			perf = _extract_stat(stat_type, player_id, stats, None, first['batsmen'])
			if perf is not None:
				performance_log.append({
					'sim': sim_num,
					'innings': innings_count,
					'match_inning': 1,
					'value': perf,
					'details': stats
				})
		
		if second_batting[0] == target_team_name and player_id in second['batsmen']:
			innings_count += 1
			stats = second['batsmen'][player_id]
			perf = _extract_stat(stat_type, player_id, stats, None, second['batsmen'])
			if perf is not None:
				performance_log.append({
					'sim': sim_num,
					'innings': innings_count,
					'match_inning': 2,
					'value': perf,
					'details': stats
				})
		
		# Bowling tracking
		if 'bowling' in stat_type:
			if first_batting[0] == target_team_name and player_id in first['bowlers']:
				stats = first['bowlers'][player_id]
				perf = _extract_bowling_stat(stat_type, stats)
				if perf is not None:
					performance_log.append({
						'sim': sim_num,
						'innings': innings_count,
						'match_inning': 1,
						'value': perf,
						'details': stats,
						'role': 'bowling'
					})
			
			if second_batting[0] == target_team_name and player_id in second['bowlers']:
				stats = second['bowlers'][player_id]
				perf = _extract_bowling_stat(stat_type, stats)
				if perf is not None:
					performance_log.append({
						'sim': sim_num,
						'innings': innings_count,
						'match_inning': 2,
						'value': perf,
						'details': stats,
						'role': 'bowling'
					})
		
		# Progress indicator
		if sim_num % 20 == 0:
			print(f"Completed {sim_num}/{num_simulations} simulations...")
	
	print(f"Completed all {num_simulations} simulations.\n")
	
	return {
		'player_name': player_name,
		'player_id': player_id,
		'team_name': target_team_name,
		'stat_type': stat_type,
		'num_simulations': num_simulations,
		'total_innings': innings_count,
		'performance_log': performance_log
	}


def _extract_stat(stat_type, player_id, stats, bowler_stats=None, all_batsmen=None):
	"""Extract specific batting stat from player stats dict."""
	if stat_type == 'batting_runs':
		return stats['runs']
	elif stat_type == 'batting_balls':
		return stats['balls']
	elif stat_type == 'batting_sr':
		if stats['balls'] > 0:
			return (stats['runs'] / stats['balls']) * 100
		return 0
	elif stat_type == 'batting_dismissals':
		return 1 if stats['dismissed'] else 0
	elif stat_type == 'batting_avg':
		if stats['dismissed']:
			return stats['runs']
		return None  # Can't compute average if not out
	return None


def _extract_bowling_stat(stat_type, stats):
	"""Extract specific bowling stat from bowler stats dict."""
	if stat_type == 'bowling_economy':
		if stats['balls'] > 0:
			return (stats['runs'] / stats['balls']) * 5  # 5-ball overs
		return 0
	elif stat_type == 'bowling_runs':
		return stats['runs']
	elif stat_type == 'bowling_wickets':
		return stats['wickets']
	elif stat_type == 'bowling_balls':
		return stats['balls']
	return None


def print_performance_report(result):
	"""Print detailed performance report."""
	
	print("=" * 100)
	print("PLAYER PERFORMANCE TRACKER - DETAILED REPORT")
	print("=" * 100)
	print()
	
	print(f"Player: {result['player_name']} ({result['player_id']})")
	print(f"Team: {result['team_name']}")
	print(f"Stat Type: {result['stat_type']}")
	print(f"Total Simulations: {result['num_simulations']}")
	print(f"Total Innings Tracked: {result['total_innings']}")
	print()
	
	perf_log = result['performance_log']
	
	if not perf_log:
		print("No performance data collected.")
		return
	
	# Summary statistics
	values = [p['value'] for p in perf_log]
	
	print("SUMMARY STATISTICS:")
	print(f"  Count: {len(values)}")
	print(f"  Mean: {sum(values) / len(values):.2f}")
	print(f"  Min: {min(values):.2f}")
	print(f"  Max: {max(values):.2f}")
	print(f"  Median: {sorted(values)[len(values)//2]:.2f}")
	print()
	
	# Detailed list
	print("INNING-BY-INNING PERFORMANCE:")
	print(f"{'Sim':>4} {'Inning':>7} {'M-Inn':>5} {'Value':>10} {'Details':<30}")
	print("-" * 100)
	
	for entry in perf_log:
		details_str = ""
		if 'batting' in result['stat_type']:
			details = entry['details']
			details_str = f"Runs:{details['runs']} Balls:{details['balls']}"
			if details['dismissed']:
				details_str += f" ({details['howout']})"
			else:
				details_str += " (Not Out)"
		elif 'bowling' in result['stat_type']:
			details = entry['details']
			overs = details['balls'] // 5
			balls_rem = details['balls'] % 5
			details_str = f"Overs:{overs}.{balls_rem} R:{details['runs']} W:{details['wickets']}"
		
		value_str = f"{entry['value']:.2f}"
		print(f"{entry['sim']:>4} {entry['innings']:>7} {entry['match_inning']:>5} {value_str:>10} {details_str:<30}")
	
	print()
	print("=" * 100)


def export_to_csv(result, filename=None):
	"""Export performance data to CSV."""
	
	if filename is None:
		filename = f"{result['player_name'].replace(' ', '_')}_{result['stat_type']}_{result['num_simulations']}sims.csv"
	
	csv_dir = os.path.join(os.path.dirname(__file__), 'csv_exports')
	csv_path = os.path.join(csv_dir, filename)
	
	try:
		with open(csv_path, 'w', encoding='utf-8') as f:
			# Header
			f.write("Sim,Inning,Match_Inning,Value,Runs,Balls,Dismissed,HowOut\n")
			
			for entry in result['performance_log']:
				details = entry['details']
				if 'batting' in result['stat_type']:
					f.write(f"{entry['sim']},{entry['innings']},{entry['match_inning']},")
					f.write(f"{entry['value']:.2f},{details['runs']},{details['balls']},")
					f.write(f"{1 if details['dismissed'] else 0},{details['howout']}\n")
		
		print(f"Results exported to {csv_path}")
	except Exception as e:
		print(f"Failed to export CSV: {e}")


def main():
	parser = argparse.ArgumentParser(
		description='Track individual player performance across multiple simulations'
	)
	parser.add_argument('team1', help='Filename of first team (e.g., Test_Team_Alpha.json)')
	parser.add_argument('team2', help='Filename of second team (e.g., Team_Beta_Squad.json)')
	parser.add_argument('player', help='Player name or player_id to track')
	parser.add_argument('-s', '--stat', default='batting_runs',
					   choices=['batting_runs', 'batting_balls', 'batting_sr', 'batting_dismissals',
					           'bowling_economy', 'bowling_runs', 'bowling_wickets', 'bowling_balls'],
					   help='Stat type to track (default: batting_runs)')
	parser.add_argument('-n', '--num-sims', type=int, default=50, 
					   help='Number of simulations (default: 50)')
	parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
	parser.add_argument('--csv', action='store_true', help='Export results to CSV')
	
	args = parser.parse_args()
	
	result = run_player_tracking(
		args.team1, args.team2, args.player,
		stat_type=args.stat,
		num_simulations=args.num_sims,
		seed=args.seed
	)
	
	if result:
		print_performance_report(result)
		
		if args.csv:
			export_to_csv(result)


if __name__ == '__main__':
	main()
