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
	pick_random_team
)


def intro_screen():
	"""Display the welcome intro screen."""
	os.system('cls' if os.name == 'nt' else 'clear')
	print("=" * 60)
	print()
	print("  Hello! Welcome to the TBONTB simulator")
	print()
	print("  Here is where we try to find out answers to that auld")
	print("  question: 'But can they do it 8v8 on a summer")
	print("  sunday in clapham?'")
	print()
	print("=" * 60)
	input("\nPRESS ENTER TO START")


def main_menu():
	"""Display main menu and return user choice."""
	os.system('cls' if os.name == 'nt' else 'clear')
	print()
	print("  TBONTB SIM")
	print()
	print("  MENU")
	print("  1. Play")
	print("  2. Settings")
	print("  3. Team Builder")
	print("  4. Quit")
	print()
	choice = input("  Enter choice (1-4): ").strip()
	return choice


def settings_screen():
	"""Display settings placeholder."""
	os.system('cls' if os.name == 'nt' else 'clear')
	print()
	print("  SETTINGS")
	print()
	print("  Place Holder")
	print()
	input("  Press ENTER to go back to menu")


def list_available_squads():
	"""List all available player squad files in json/squads/."""
	squads_dir = os.path.join(os.path.dirname(__file__), 'json', 'squads')
	if not os.path.exists(squads_dir):
		return []
	try:
		files = [f.replace('.json', '') for f in os.listdir(squads_dir) if f.endswith('.json') and not f.startswith('.')]
		return sorted(files)
	except Exception:
		return []


def squad_selection_menu():
	"""Display squad selection menu and return choice."""
	os.system('cls' if os.name == 'nt' else 'clear')
	squads = list_available_squads()
	
	print()
	print("  BUILD YOUR TEAM")
	print()
	print("  Select the Squad:")
	print()
	
	for idx, squad in enumerate(squads, start=1):
		print(f"  {idx}. {squad}")
	
	print("  M. Menu")
	print()
	choice = input("  Enter choice: ").strip().lower()
	
	if choice == 'm':
		return None
	
	try:
		idx = int(choice) - 1
		if 0 <= idx < len(squads):
			return squads[idx]
	except ValueError:
		pass
	
	print("  Invalid choice. Press ENTER to go back.")
	input()
	return squad_selection_menu()


def team_builder_menu(players, squad_name="TBONTB"):
	"""Team builder menu that calls team_builder functions."""
	# Import team_builder functions
	from team_builder import choose_team, choose_captain_and_keeper, reorder_batting, save_team
	
	os.system('cls' if os.name == 'nt' else 'clear')
	print("\n  Building your team...\n")
	
	# Choose 8 players
	team = choose_team(players)
	if not team:
		print("Team building cancelled.")
		input()
		return None
	
	# Choose captain and keeper
	captain, keeper = choose_captain_and_keeper(team)
	print(f"\nCaptain: {captain['player_name']}")
	print(f"Wicketkeeper: {keeper['player_name']}")
	
	# Reorder batting
	team = reorder_batting(team)
	
	# Save team
	team_name = input("\nEnter team name: ").strip()
	if team_name:
		save_team(team, captain, keeper, team_name, squad_name=squad_name)
		print(f"\nTeam '{team_name}' saved from {squad_name} squad!")
	else:
		print("\nTeam not saved (no name provided).")
	
	input("Press ENTER to continue...")
	return team


def choose_toss_or_conversation():
	"""Handle toss vs Conversation™ decision and return 'bat' or 'bowl'."""
	while True:
		choice = input("Do you want toss or Conversation (TM)? (toss/conversation): ").strip().lower()
		if choice.startswith('c'):
			print("\nConversation (TM) sucessfull, you are bowling first!")
			return 'bowl'
		if choice.startswith('t'):
			break
		print("Please type 'toss' or 'conversation'.")

	while True:
		call = input("Call heads or tails? (heads/tails): ").strip().lower()
		if call.startswith('h'):
			call = 'heads'
			break
		if call.startswith('t'):
			call = 'tails'
			break
		print("Please type 'heads' or 'tails'.")

	coin = random.choice(['heads', 'tails'])
	print(f"\nCoin toss... it is {coin.upper()}!")

	if call == coin:
		while True:
			decision = input("You won the toss. Bat or bowl? (bat/bowl): ").strip().lower()
			if decision in ('bat', 'bowl'):
				return decision
			print("Please type 'bat' or 'bowl'.")
	else:
		comp_decision = random.choice(['bat', 'bowl'])
		print(f"The computer won the toss and will {comp_decision} first.")
		return comp_decision


def play_match(players, match_config, args):
	"""Run a match between two teams."""
	output_config = OutputConfig.default()
	
	# Team selection
	if args.demo:
		# Non-interactive demo: pick two random teams
		pool = list(players.values())
		random.shuffle(pool)
		user_team = pool[:match_config.team_size]
		comp_team = pool[match_config.team_size:match_config.team_size*2]
		user_team_name = "Demo User Team"
		comp_team_name = "Demo Computer Team"
		user_keeper_id = None
		comp_keeper_id = None
		
		print("\nDemo mode: Teams selected automatically.")
		print(f"User team ({user_team_name}):")
		for p in user_team:
			print(f"  {p['player_name']}")
		print(f"Computer team ({comp_team_name}):")
		for p in comp_team:
			print(f"  {p['player_name']}")
		
		choice = 'bat'  # default demo choice: user bats first
	else:
		os.system('cls' if os.name == 'nt' else 'clear')
		
		# Interactive team selection
		user_team, user_team_name, user_captain_id, user_keeper_id = choose_team_from_list(players, "Choose your team")
		if not user_team:
			print("No team selected. Returning to menu.")
			input("Press ENTER to continue...")
			return
		
		print(f"\nYou selected: {user_team_name}")
		def _fmt_with_roles(p, captain_id, keeper_id):
			roles = []
			pid = p.get('player_id')
			short_int = p.get('short_int')
			def _matches(role_id):
				if role_id is None:
					return False
				if pid == role_id:
					return True
				return isinstance(role_id, int) and short_int == role_id
			if _matches(captain_id):
				roles.append('c')
			if _matches(keeper_id):
				roles.append('wk')
			suffix = '' if not roles else ' (' + ') ('.join(roles) + ')'
			return f"  {p['player_name']}{suffix}"
		for p in user_team:
			print(_fmt_with_roles(p, user_captain_id, user_keeper_id))
		
		# Computer team selection (excluding user picks)
		exclude = [p['player_id'] for p in user_team]
		comp_team, comp_team_name, comp_captain_id, comp_keeper_id = choose_computer_team_from_list(players, exclude)
		
		print(f"\nComputer team: {comp_team_name}")
		for p in comp_team:
			print(_fmt_with_roles(p, comp_captain_id, comp_keeper_id))
		
		# Choose batting or bowling first via toss or Conversation
		choice = choose_toss_or_conversation()
	
	# Determine batting order and keeper assignments
	if choice == 'bat':
		first_batting = (user_team_name, user_team, user_keeper_id)
		second_batting = (comp_team_name, comp_team, comp_keeper_id)
	else:
		first_batting = (comp_team_name, comp_team, comp_keeper_id)
		second_batting = (user_team_name, user_team, user_keeper_id)
	
	# Simulate first innings
	print(f"\nSimulating first innings: {first_batting[0]} batting...")
	if not args.demo:
		time.sleep(5)  # brief pause for realism
	
	first = simulate_innings(
		first_batting[1],
		second_batting[1],
		match_config,
		target=None,
		output_config=output_config,
		keeper_id=second_batting[2]
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
		output_config=output_config,
		keeper_id=first_batting[2]
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
		export_dir = os.path.join(os.path.dirname(__file__), 'json', 'match_reports')
		export_match_json(export_dir, match_obj)


def main():
	"""Main entry point for the cricket simulator."""
	parser = argparse.ArgumentParser(description='TBONTB Simple Cricket Simulator - Prototype')
	parser.add_argument('--demo', action='store_true', help='Run a non-interactive demo match')
	parser.add_argument('--seed', type=int, help='Random seed for deterministic demo')
	parser.add_argument('--export-json', action='store_true', help='Export match boxscore to json/')
	parser.add_argument('--players-file', type=str, help='Path to alternate players summary JSON (e.g., blank set for testing)')
	parser.add_argument('--no-intro', action='store_true', help='Skip intro screen')
	args = parser.parse_args()
	
	if args.seed is not None:
		random.seed(args.seed)
	
	# Load default configurations
	match_config = MatchConfig.default()
	
	# Display startup info
	data_dir = os.path.join(os.path.dirname(__file__), "json")
	print(data_dir)
	print("TBONTB Simple Cricket Simulator - Prototype")
	print(f"Match type: {match_config.match_type}")
	
	# Load players
	players = load_players_summary(args.players_file)
	if not players:
		print("No players loaded. Please ensure json/squads/TBONTB_players_summary.json exists.")
		sys.exit(1)
	
	# Show intro unless --no-intro or --demo
	if not args.no_intro and not args.demo:
		intro_screen()
	
	# Main menu loop (unless in demo mode)
	if args.demo:
		play_match(players, match_config, args)
	else:
		while True:
			choice = main_menu()
			
			if choice == '1':
				play_match(players, match_config, args)
				input("\nPress ENTER to return to menu...")
			elif choice == '2':
				settings_screen()
			elif choice == '3':
				squad = squad_selection_menu()
				if squad:
					squad_file = f"{squad}.json"
					squad_path = os.path.join(os.path.dirname(__file__), 'json', 'squads', squad_file)
					if os.path.exists(squad_path):
						squad_players = load_players_summary(squad_path)
						if squad_players:
							team_builder_menu(squad_players, squad_name=squad)
						else:
							print(f"Could not load squad: {squad}")
							input("Press ENTER to continue...")
					else:
						print(f"Squad file not found: {squad_file}")
						input("Press ENTER to continue...")
			elif choice == '4':
				print("\nGoodbye!")
				sys.exit(0)
			else:
				print("Invalid choice. Press ENTER to continue...")
				input()


if __name__ == '__main__':
	main()
