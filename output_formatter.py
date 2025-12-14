"""
Output formatter module for TBONTB Cricket Simulator.
Handles different display options for simulation results.
"""

import json
import os
import datetime


class OutputConfig:
	"""Configuration for output display options."""
	
	OUTPUT_MODES = {
		'SCORECARD_ONLY': {
			'description': 'Show only final scorecards',
			'ball_by_ball': False,
			'over_by_over': False,
			'scorecard': True
		},
		'OVER_BY_OVER': {
			'description': 'Show over-by-over summaries',
			'ball_by_ball': False,
			'over_by_over': True,
			'scorecard': True
		},
		'BALL_BY_BALL': {
			'description': 'Show detailed ball-by-ball commentary',
			'ball_by_ball': True,
			'over_by_over': True,
			'scorecard': True
		}
	}
	
	def __init__(self, mode='OVER_BY_OVER'):
		"""
		Initialize output configuration.
		
		Args:
			mode: Output display mode (SCORECARD_ONLY, OVER_BY_OVER, BALL_BY_BALL)
		"""
		if mode not in self.OUTPUT_MODES:
			raise ValueError(f"Unknown output mode: {mode}")
		
		self.mode = mode
		settings = self.OUTPUT_MODES[mode]
		self.ball_by_ball = settings['ball_by_ball']
		self.over_by_over = settings['over_by_over']
		self.scorecard = settings['scorecard']
		
		# Storage for over summaries and ball-by-ball (populated during simulation)
		self.over_summaries = []
		self.ball_by_ball_events = []
	
	@classmethod
	def default(cls):
		"""Create default output config matching current prototype."""
		return cls(mode='BALL_BY_BALL')
	
	def __repr__(self):
		return f"OutputConfig(mode={self.mode})"


def print_over_summaries(output_config):
	"""Print stored over-by-over summaries."""
	# Suppress when detailed ball-by-ball is requested to avoid duplicate summaries
	if not output_config.over_by_over or output_config.ball_by_ball:
		return
	
	for summary in output_config.over_summaries:
		label_suffix = f" ({summary['label']})" if summary['label'] else ""
		print(f"Over {summary['over']}{label_suffix}: {summary['score']}")
		print(f"Bowler: {summary['bowler']}")
		
		if summary['batters']:
			print("Batters: " + " | ".join(summary['batters']))
		
		if summary['fow']:
			print("FOW:")
			for entry in summary['fow']:
				if len(entry) == 5:
					fow_label, name, runs, balls, howout = entry
					print(f"{fow_label} Wicket: {name} {howout} {runs}({balls})")
				else:
					fow_label, name, runs, balls = entry
					print(f"{fow_label} Wicket: {name} {runs}({balls})")


def print_ball_by_ball(output_config):
	"""Print stored ball-by-ball events grouped by over with end-of-over summary."""
	if not output_config.ball_by_ball:
		return

	over_summaries = {s['over']: s for s in output_config.over_summaries}
	current_over = None

	def _print_over_footer(over_idx):
		summary = over_summaries.get(over_idx)
		if not summary:
			return
		runs_word = "run" if summary.get('over_runs', 0) == 1 else "runs"
		wkts_word = "wicket" if summary.get('over_wkts', 0) == 1 else "wickets"
		print()
		print(f"End of Over {over_idx}: {summary['score']} | {summary.get('over_runs', 0)} {runs_word} | {summary.get('over_wkts', 0)} {wkts_word}")
		print(f"Bowler: {summary['bowler']}")
		if summary.get('batters'):
			print("Batters: " + " | ".join(summary['batters']))
		if summary.get('fow'):
			print("FOW:")
			for fow_label, name, runs, balls, howout in summary['fow']:
				print(f"{fow_label} {name} {runs}({balls}) {howout}")
		print()

	for evt in output_config.ball_by_ball_events:
		over_part = evt['ball'].split('.')[0]
		over_idx = int(over_part) + 1
		if current_over is None or over_idx != current_over:
			if current_over is not None:
				_print_over_footer(current_over)
			print(f"Over {over_idx}:")
			current_over = over_idx
		print(f"{evt['ball']} - {evt['bowler']} - to - {evt['batter']} - {evt['outcome']}")

	if current_over is not None:
		_print_over_footer(current_over)


def print_innings_summary(team_name, innings, match_config):
	"""
	Print innings summary scorecard.
	
	Args:
		team_name: Name of the batting team
		innings: Innings statistics dictionary
		match_config: MatchConfig object for formatting
	"""
	total_balls = innings.get('balls', 0)
	overs_str = match_config.get_overs_from_balls(total_balls)
	
	print(f"\n{team_name} innings: {innings['runs']} / {innings['wickets']} ({overs_str} Overs)")
	print("BATTING:")
	for pid, s in innings['batsmen'].items():
		if s['dismissed']:
			print(f"  {s['name']}: {s['runs']} ({s['balls']}) - {s['howout']}")
		else:
			if s['balls'] > 0:
				print(f"  {s['name']}: {s['runs']}* ({s['balls']}) - Not Out")
			else:
				print(f"  {s['name']}: DNB")
	
	print("BOWLING:")
	for pid, s in innings['bowlers'].items():
		maidens = s.get('maidens', 0)
		overs = s.get('overs', '0')
		print(f"  {s['name']}: {overs}-{maidens}-{s['runs']}-{s['wickets']}")


def export_match_json(path, match_obj):
	"""
	Write match object to JSON file with timestamped filename.
	
	Args:
		path: Directory path to save the file (should be json/match_reports/)
		match_obj: Serializable dictionary with match data
	"""
	try:
		os.makedirs(path, exist_ok=True)
		ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
		fname = f"match_{ts}.json"
		full = os.path.join(path, fname)
		with open(full, 'w', encoding='utf-8') as f:
			json.dump(match_obj, f, ensure_ascii=False, indent=2)
		print(f"Match exported to {full}")
	except Exception as e:
		print(f"Failed to export match json: {e}")


def build_match_export_object(first_batting, first_innings, second_batting, second_innings, result_text):
	"""
	Build a serializable match object for JSON export.
	
	Args:
		first_batting: Tuple of (team_name, team_list) for first innings
		first_innings: First innings statistics
		second_batting: Tuple of (team_name, team_list) for second innings
		second_innings: Second innings statistics
		result_text: Match result description
	
	Returns:
		Dictionary ready for JSON serialization
	"""
	match_obj = {
		"date": datetime.datetime.now().isoformat(),
		"teams": {
			first_batting[0]: [{"player_id": p.get('player_id'), "player_name": p.get('player_name')} for p in first_batting[1]],
			second_batting[0]: [{"player_id": p.get('player_id'), "player_name": p.get('player_name')} for p in second_batting[1]],
		},
		"first_innings": {
			"team": first_batting[0],
			"runs": first_innings['runs'],
			"wickets": first_innings['wickets'],
			"balls": first_innings['balls'],
			"batsmen": [],
			"bowlers": [],
		},
		"second_innings": {
			"team": second_batting[0],
			"runs": second_innings['runs'],
			"wickets": second_innings['wickets'],
			"balls": second_innings['balls'],
			"batsmen": [],
			"bowlers": [],
		},
		"result": {
			"text": result_text
		}
	}
	
	# Populate batsmen and bowlers for first innings
	for pid, b in first_innings['batsmen'].items():
		match_obj['first_innings']['batsmen'].append({
			"player_id": pid,
			"name": b['name'],
			"runs": b['runs'],
			"balls": b['balls'],
			"dismissed": b['dismissed'],
			"howout": b.get('howout', '')
		})
	
	for pid, b in first_innings['bowlers'].items():
		match_obj['first_innings']['bowlers'].append({
			"player_id": pid,
			"name": b['name'],
			"overs": b.get('overs'),
			"maidens": b.get('maidens', 0),
			"runs": b.get('runs', 0),
			"wickets": b.get('wickets', 0)
		})
	
	# Populate batsmen and bowlers for second innings
	for pid, b in second_innings['batsmen'].items():
		match_obj['second_innings']['batsmen'].append({
			"player_id": pid,
			"name": b['name'],
			"runs": b['runs'],
			"balls": b['balls'],
			"dismissed": b['dismissed'],
			"howout": b.get('howout', '')
		})
	
	for pid, b in second_innings['bowlers'].items():
		match_obj['second_innings']['bowlers'].append({
			"player_id": pid,
			"name": b['name'],
			"overs": b.get('overs'),
			"maidens": b.get('maidens', 0),
			"runs": b.get('runs', 0),
			"wickets": b.get('wickets', 0)
		})
	
	return match_obj


def calculate_result(first_runs, first_wickets, second_runs, second_wickets, 
					 first_team_name, second_team_name, team_size):
	"""
	Calculate match result text.
	
	Returns: (winner_name, result_text)
	"""
	if first_runs > second_runs:
		winner = first_team_name
		margin = first_runs - second_runs
		result_text = f"{winner} won by {margin} runs"
	elif second_runs > first_runs:
		winner = second_team_name
		wickets_remaining = team_size - second_wickets
		result_text = f"{winner} won by {wickets_remaining} wickets"
	else:
		winner = None
		result_text = "Match tied"
	
	return winner, result_text
