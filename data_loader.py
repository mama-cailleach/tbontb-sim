"""
Data loading module for TBONTB Cricket Simulator.
Handles loading players from JSON and managing team files.
"""

import json
import os
import re


# Global short ID index for player lookup
SHORT_ID_INDEX = {}


def parse_float(s, default=None):
	"""Parse float values from data, handling special characters."""
	if s is None or s == "":
		return default
	try:
		# remove stray characters like '*'
		return float(str(s).replace("*", ""))
	except Exception:
		return default


def load_players_summary(json_path=None):
	"""
	Load player data from JSON file.
	Returns a dictionary of player objects keyed by player_id.
	"""
	if not json_path:
		json_path = os.path.join(os.path.dirname(__file__), "json", "TBONTB_players_summary.json")
	players = {}
	
	if not os.path.exists(json_path):
		print(f"JSON players summary not found at {json_path}. Please ensure the file exists in the json/ folder.")
		return players

	print(f"Loading players from {json_path}")
	
	with open(json_path, encoding="utf-8") as f:
		try:
			rows = json.load(f)
		except Exception:
			rows = []
	
	for r in rows:
		raw_id = r.get("player_id")
		if raw_id is None:
			continue
		
		# canonical string id like TBONTB_0001 for compatibility
		try:
			if isinstance(raw_id, int):
				pid = f"TBONTB_{int(raw_id):04d}"
			else:
				pid = str(raw_id)
		except Exception:
			pid = str(raw_id)
		
		# extract trailing digits for short id (e.g. TBONTB_0001 -> 1 / '0001')
		m = re.search(r"(\d+)$", pid)
		short_str = m.group(1) if m else None
		short_int = int(short_str) if short_str else None
		
		players[pid] = {
			"player_id": pid,
			"player_name": r.get("player_name", ""),
			# short id forms
			"short_str": short_str,
			"short_int": short_int,
			# extra stats: batting average, boundaries, bowling average
			"bat_avg": parse_float(r.get("bat_avg"), None),
			"fours": int(parse_float(r.get("4s", r.get("fours")), 0) or 0),
			"sixes": int(parse_float(r.get("6s", r.get("sixes")), 0) or 0),
			"bowl_avg": parse_float(r.get("bowl_avg"), None),
			# batting
			"matches": int(r.get("matches") or r.get("matches_played") or 0),
			"runs": parse_float(r.get("runs"), 0) or 0,
			"balls_faced": parse_float(r.get("balls_faced"), 0) or 0,
			"strike_rate": parse_float(r.get("strike_rate"), None),
			# bowling
			"overs_bowled": parse_float(r.get("overs_bowled"), 0) or 0,
			"runs_conceded": parse_float(r.get("runs_conceded"), 0) or 0,
			"wickets": int(parse_float(r.get("wickets"), 0) or 0),
			"economy": parse_float(r.get("economy"), None),
		}
	
	# build a short-id index for quick lookup (accept '1' or '0001')
	global SHORT_ID_INDEX
	SHORT_ID_INDEX = {}
	for pid, p in players.items():
		if p.get('short_int') is not None:
			# map bare int and zero-padded string to full pid
			SHORT_ID_INDEX[str(p['short_int'])] = pid
			if p.get('short_str'):
				SHORT_ID_INDEX[p['short_str']] = pid
	# also allow direct full pid lookup via the same index
	for pid in players.keys():
		SHORT_ID_INDEX[pid] = pid
	
	return players


def list_available_teams():
	"""List all team JSON files in json/teams/ directory."""
	teams_dir = os.path.join(os.path.dirname(__file__), 'json', 'teams')
	if not os.path.exists(teams_dir):
		return []
	try:
		files = [f for f in os.listdir(teams_dir) if f.endswith('.json')]
		return sorted(files)
	except Exception:
		return []


def load_team_from_file(filename, players):
	"""
	Load a team from json/teams/filename and return list of player dicts.
	Returns: (team_list, team_name) or (None, None) on failure.
	"""
	teams_dir = os.path.join(os.path.dirname(__file__), 'json', 'teams')
	path = os.path.join(teams_dir, filename)
	try:
		with open(path, encoding='utf-8') as f:
			team_data = json.load(f)
			saved_ids = [p.get('player_id') for p in team_data.get('team', []) if p.get('player_id')]
			team = [players[pid] for pid in saved_ids if pid in players]
			team_name = team_data.get('team_name', filename.replace('.json', ''))
			if len(team) == 8:
				return team, team_name
	except Exception:
		pass
	return None, None


def get_team_name_from_file(filename):
	"""Get the team name from a team JSON file without loading full player data."""
	teams_dir = os.path.join(os.path.dirname(__file__), 'json', 'teams')
	path = os.path.join(teams_dir, filename)
	try:
		with open(path, encoding='utf-8') as f:
			team_data = json.load(f)
			return team_data.get('team_name', filename.replace('.json', ''))
	except Exception:
		return filename.replace('.json', '')
