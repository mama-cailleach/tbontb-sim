"""
TBONTB Simple Cricket Simulator - Main Entry Point

This is a modular cricket simulator with support for different match types,
simulation styles, and output formats. Currently configured with default
parameters matching the original prototype behavior.
"""

import random
import os
import sys
import time
import argparse

# Import custom modules
from data_loader import load_players_summary
from match_config import MatchConfig
from simulation_engine import simulate_innings
from output_formatter import (
	OutputConfig,
	print_ball_by_ball,
	print_over_summaries,
	print_innings_summary,
	export_match_json,
	build_match_export_object,
	calculate_result
)
from team_selector import (
	choose_team_from_list,
	choose_computer_team_from_list,
	choose_bat_or_bowl,
	pick_random_team
)


def main():
	"""Main entry point for the cricket simulator."""
	parser = argparse.ArgumentParser(description='TBONTB Simple Cricket Simulator - Prototype')
	parser.add_argument('--demo', action='store_true', help='Run a non-interactive demo match')
	parser.add_argument('--seed', type=int, help='Random seed for deterministic demo')
	parser.add_argument('--export-json', action='store_true', help='Export match boxscore to json/')
	parser.add_argument('--players-file', type=str, help='Path to alternate players summary JSON (e.g., blank set for testing)')
	args = parser.parse_args()
	
	if args.seed is not None:
		random.seed(args.seed)
	
	# Load default configurations
	match_config = MatchConfig.default()
	output_config = OutputConfig.default()
	
	# Display startup info
	data_dir = os.path.join(os.path.dirname(__file__), "json")
	print(data_dir)
	print("TBONTB Simple Cricket Simulator - Prototype")
	print(f"Match type: {match_config.match_type}")
	print(f"Output mode: {output_config.mode}")
	
	# Load players
	players = load_players_summary(args.players_file)
	if not players:
		print("No players loaded. Please ensure json/TBONTB_players_summary.json exists.")
		sys.exit(1)
	
	# Team selection
	if args.demo:
		# Non-interactive demo: pick two random teams
		pool = list(players.values())
		random.shuffle(pool)
		user_team = pool[:match_config.team_size]
		comp_team = pool[match_config.team_size:match_config.team_size*2]
		user_team_name = "Demo User Team"
		comp_team_name = "Demo Computer Team"
		
		print("Demo mode: Teams selected automatically.")
		print(f"User team ({user_team_name}):")
		for p in user_team:
			print(f"  {p['player_name']}")
		print(f"Computer team ({comp_team_name}):")
		for p in comp_team:
			print(f"  {p['player_name']}")
		
		choice = 'bat'  # default demo choice: user bats first
	else:
		# Interactive team selection
		user_team, user_team_name = choose_team_from_list(players, "Choose your team")
		if not user_team:
			print("No team selected. Exiting.")
			sys.exit(1)
		
		print(f"\nYou selected: {user_team_name}")
		for p in user_team:
			print(f"  {p['player_name']}")
		
		# Computer team selection (excluding user picks)
		exclude = [p['player_id'] for p in user_team]
		comp_team, comp_team_name = choose_computer_team_from_list(players, exclude)
		
		print(f"\nComputer team: {comp_team_name}")
		for p in comp_team:
			print(f"  {p['player_name']}")
		
		# Choose batting or bowling first
		choice = choose_bat_or_bowl()
	
	# Determine batting order
	if choice == 'bat':
		first_batting = (user_team_name, user_team)
		second_batting = (comp_team_name, comp_team)
	else:
		first_batting = (comp_team_name, comp_team)
		second_batting = (user_team_name, user_team)
	
	# Simulate first innings
	print(f"\nSimulating first innings: {first_batting[0]} batting...")
	if not args.demo:
		time.sleep(5)  # brief pause for realism
	
	first = simulate_innings(
		first_batting[1],
		second_batting[1],
		match_config,
		target=None,
		output_config=output_config
	)
	
	# Display first innings results
	print_ball_by_ball(output_config)
	print_over_summaries(output_config)
	print_innings_summary(first_batting[0], first, match_config)
	
	# Reset over summaries for second innings
	output_config.over_summaries = []
	output_config.ball_by_ball_events = []
	
	# Simulate second innings
	print(f"\nSimulating second innings: {second_batting[0]} batting...")
	if not args.demo:
		time.sleep(5)  # brief pause for realism
	
	target_score = first['runs'] + 1
	second = simulate_innings(
		second_batting[1],
		first_batting[1],
		match_config,
		target=target_score,
		output_config=output_config
	)
	
	# Display second innings results
	print_ball_by_ball(output_config)
	print_over_summaries(output_config)
	print_innings_summary(second_batting[0], second, match_config)
	
	# Calculate and display result
	winner, result_text = calculate_result(
		first['runs'], first['wickets'],
		second['runs'], second['wickets'],
		first_batting[0], second_batting[0],
		match_config.team_size
	)
	
	print(f"\nFinal Result:\n{result_text}")
	
	# Optional JSON export
	if args.export_json:
		match_obj = build_match_export_object(
			first_batting, first,
			second_batting, second,
			result_text
		)
		export_dir = os.path.join(os.path.dirname(__file__), 'json')
		export_match_json(export_dir, match_obj)


if __name__ == '__main__':
	main()
