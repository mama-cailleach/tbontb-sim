"""
Team selection module for TBONTB Cricket Simulator.
Handles interactive team selection UI.
"""

import random
from data_loader import (
	list_available_teams,
	load_team_from_file,
	get_team_name_from_file,
	SHORT_ID_INDEX
)


def show_player_list(players):
	"""Display list of all available players."""
	print("Available players (player_id : name)")
	for pid, p in sorted(players.items()):
		short = p.get('short_int') if p.get('short_int') is not None else ''
		print(f"  {short} : {p['player_name']}")


def choose_team_manual(players, team_name="User"):
	"""
	Interactive manual team selection by player IDs.
	
	Args:
		players: Dictionary of all available players
		team_name: Name for the team being selected
	
	Returns:
		List of 8 selected player dictionaries
	"""
	print(f"\nChoose 8 players for {team_name} by entering their IDs separated by commas.")
	
	while True:
		s = input("Enter 8 player IDs: ").strip()
		ids = [x.strip() for x in s.split(",") if x.strip()]
		
		if len(ids) != 8:
			print("Please enter exactly 8 player IDs.")
			continue
		
		# Resolve inputs: accept full pid or short numeric forms
		resolved = []
		bad = []
		
		for entry in ids:
			# Direct full id
			if entry in players:
				resolved.append(players[entry])
				continue
			
			# Try short index
			pid = None
			try:
				if entry.isdigit():
					pid = SHORT_ID_INDEX.get(entry)
					if pid is None:
						pid = SHORT_ID_INDEX.get(str(int(entry)))
				else:
					pid = SHORT_ID_INDEX.get(entry)
			except Exception:
				pid = SHORT_ID_INDEX.get(entry)
			
			if pid and pid in players:
				resolved.append(players[pid])
			else:
				bad.append(entry)
		
		if bad:
			print("These IDs were not found:", ",".join(bad))
			continue
		
		print(f"\n{team_name} team selected:")
		for p in resolved:
			print(f"  {p['player_name']}")
		
		return resolved


def pick_random_team(players, exclude_ids, team_size=8):
	"""
	Pick a random team from available players.
	
	Args:
		players: Dictionary of all available players
		exclude_ids: List of player IDs to exclude
		team_size: Number of players to select
	
	Returns:
		List of randomly selected player dictionaries
	"""
	pool = [p for pid, p in players.items() if pid not in exclude_ids]
	return random.sample(pool, team_size)


def choose_team_from_list(players, prompt="Choose a team"):
	"""
	Prompt user to select a team from saved team files.
	
	Args:
		players: Dictionary of all available players
		prompt: Prompt message to display
	
	Returns:
		Tuple of (team_list, team_name, captain_id, keeper_id) or (None, None, None, None) if cancelled
	"""
	team_files = list_available_teams()
	if not team_files:
		print("No saved teams found in json/teams/. Please create a team using team_builder.py first.")
		return None, None, None, None
	
	print(f"\n{prompt}:")
	for i, fname in enumerate(team_files, start=1):
		team_name = get_team_name_from_file(fname)
		print(f"  {i}. {team_name}")
	
	while True:
		choice = input(f"Enter team number (1-{len(team_files)}): ").strip()
		try:
			idx = int(choice)
			if 1 <= idx <= len(team_files):
				team, team_name, captain_id, keeper_id = load_team_from_file(team_files[idx-1], players)
				if team:
					return team, team_name, captain_id, keeper_id
				else:
					print("Failed to load team. Please try another.")
		except ValueError:
			pass
		print(f"Please enter a number between 1 and {len(team_files)}.")


def choose_computer_team_from_list(players, exclude_ids):
	"""
	Prompt user to select computer team from saved teams or use random selection.
	
	Args:
		players: Dictionary of all available players
		exclude_ids: List of player IDs already selected (to avoid duplicates)
	
	Returns:
		Tuple of (team_list, team_name, captain_id, keeper_id)
	"""
	team_files = list_available_teams()
	
	print("\nChoose computer team:")
	for i, fname in enumerate(team_files, start=1):
		team_name = get_team_name_from_file(fname)
		print(f"  {i}. {team_name}")
	print(f"  {len(team_files) + 1}. Random Team (auto-select)")
	
	while True:
		choice = input(f"Enter team number (1-{len(team_files) + 1}): ").strip()
		try:
			idx = int(choice)
			if idx == len(team_files) + 1:
				# Random team (no captain/keeper info)
				return pick_random_team(players, exclude_ids), "Random Team", None, None
			elif 1 <= idx <= len(team_files):
				team, team_name, captain_id, keeper_id = load_team_from_file(team_files[idx-1], players)
				if team:
					return team, team_name, captain_id, keeper_id
				else:
					print("Failed to load team. Please try another.")
		except ValueError:
			pass
		print(f"Please enter a number between 1 and {len(team_files) + 1}.")


def choose_bat_or_bowl():
	"""
	Prompt user to choose batting or bowling first.
	
	Returns:
		'bat' or 'bowl'
	"""
	while True:
		choice = input("Do you want to bat first or bowl first? (bat/bowl): ").strip().lower()
		if choice in ('bat', 'bowl'):
			return choice
		print("Please type 'bat' or 'bowl'.")
