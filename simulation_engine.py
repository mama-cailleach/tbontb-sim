"""
Simulation engine for TBONTB Cricket Simulator.
Contains the core ball-by-ball simulation logic.
"""

import random


def select_bowlers_from_team(team):
	"""
	Select bowlers from team, preferring players with bowling history.
	Returns up to 8 bowlers.
	"""
	bowlers = [p for p in team if p.get("overs_bowled", 0) > 0]
	if len(bowlers) >= 8:
		return random.sample(bowlers, 8)
	# pad with random other players
	need = 8 - len(bowlers)
	others = [p for p in team if p not in bowlers]
	return bowlers + random.sample(others, min(need, len(others)))


def simulate_innings(batting_team, bowling_team, match_config, target=None, output_config=None):
	"""
	Simulate a cricket innings ball-by-ball.
	
	Args:
		batting_team: List of player dicts in batting order
		bowling_team: List of player dicts (bowlers will be selected)
		match_config: MatchConfig object with match rules
		target: Optional target score to chase
		output_config: OutputConfig object for display settings
	
	Returns:
		Dictionary with innings statistics
	"""
	balls_per_over = match_config.balls_per_over
	balls = match_config.balls_per_innings
	
	# Initialize stats
	batsmen_stats = {
		p['player_id']: {
			'name': p['player_name'],
			'runs': 0,
			'balls': 0,
			'dismissed': False,
			'howout': ''
		} for p in batting_team
	}
	bowlers_stats = {
		p['player_id']: {
			'name': p['player_name'],
			'balls': 0,
			'runs': 0,
			'wickets': 0,
			'maidens': 0
		} for p in bowling_team
	}
	
	# Initial batsmen
	striker_idx = 0
	non_striker_idx = 1
	next_batsman = 2
	
	# Select bowlers (rotate every over)
	bowlers = select_bowlers_from_team(bowling_team)
	num_bowlers = len(bowlers)
	
	total_runs = 0
	total_wickets = 0
	balls_bowled = 0
	
	num_players = len(batting_team)
	
	# Ball-by-ball simulation
	for ball_no in range(balls):
		over = ball_no // balls_per_over
		bowler = bowlers[over % num_bowlers]
		bstats = bowlers_stats[bowler['player_id']]
		
		# Start of over bookkeeping
		if ball_no % balls_per_over == 0:
			per_over_start_balls = {pid: s['balls'] for pid, s in batsmen_stats.items()}
			runs_in_over = 0
			wickets_in_over = 0
			over_bowler = bowler
			over_index = over + 1
			start_striker = striker_idx
			start_non_striker = non_striker_idx
			bowler_runs_start = bstats['runs']
			bowler_balls_start = bstats['balls']
			per_over_fow = []
		
		# Determine alive batsmen
		alive = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive) == 0:
			break
		last_mode = (len(alive) == 1)
		
		# If last mode, ensure striker is the last alive batsman
		if last_mode:
			striker_idx = alive[0]
			non_striker_idx = None
		
		# Prepare batsman
		batsman = batting_team[striker_idx]
		pstats = batsmen_stats[batsman['player_id']]
		
		# Calculate batsman runs-per-ball
		if batsman.get('strike_rate'):
			batsman_rpb = batsman['strike_rate'] / 100.0
		else:
			bf = batsman.get('balls_faced') or 0
			runs = batsman.get('runs') or 0
			batsman_rpb = (runs / bf) if bf > 0 else 0.8
		
		# Boost from batting average
		if batsman.get('bat_avg'):
			bat_avg = batsman['bat_avg']
			batsman_rpb *= (1.0 + min(max(bat_avg, 0), 100) / 300.0)
		
		# Calculate bowler runs-per-ball
		if bowler.get('economy'):
			bowler_rpb = bowler['economy'] / balls_per_over
		else:
			bowler_rpb = (bowler.get('runs_conceded', 10) / max(1, (bowler.get('overs_bowled') or 1))) / balls_per_over
		
		bowler_bowl_avg = bowler.get('bowl_avg')
		bowler_wickets = bowler.get('wickets') or 0
		
		# Batting advantage metric
		ba = batsman_rpb / (batsman_rpb + bowler_rpb + 1e-6)
		
		# Calculate wicket probability
		base_wicket_prob = 0.008 + (1 - ba) * 0.08
		bat_avg = batsman.get('bat_avg') or 0
		bat_protect = 1.0 - min(max(bat_avg, 0), 100) / 250.0
		
		bowl_boost = 1.0
		if bowler_bowl_avg:
			bowl_boost += max(0.0, (50.0 - bowler_bowl_avg) / 120.0)
		bowl_boost *= (1.0 + min(bowler_wickets, 200) / 300.0)
		
		wicket_prob = base_wicket_prob * bowl_boost * bat_protect
		wicket_prob = max(0.003, min(wicket_prob, 0.18))
		
		# Roll for wicket
		r = random.random()
		if r < wicket_prob:
			# Wicket!
			total_wickets += 1
			
			# Determine dismissal mode
			mode_pick = random.random()
			if mode_pick < 0.4:
				mode = 'Bowled'
			elif mode_pick < 0.75:
				mode = 'Caught'
			elif mode_pick < 0.88:
				mode = 'Stumped'
			else:
				mode = 'Run Out'
			
			# Determine who is dismissed
			dismissed_idx = striker_idx
			if mode == 'Run Out' and (not last_mode) and non_striker_idx is not None:
				if random.random() < 0.3:
					dismissed_idx = non_striker_idx
			
			dismissed_player = batting_team[dismissed_idx]
			dstats = batsmen_stats[dismissed_player['player_id']]
			dstats['balls'] += 1
			dstats['dismissed'] = True
			dstats['howout'] = mode
			
			bstats['balls'] += 1
			
			# Record fall-of-wicket
			ball_in_over = (ball_no % balls_per_over) + 1
			fow_label = f"{over}.{ball_in_over}"
			per_over_fow.append((fow_label, dismissed_player['player_name'], dstats['runs'], dstats['balls']))
			wickets_in_over += 1
			
			if mode != 'Run Out':
				bstats['wickets'] += 1
			
			# Check if innings ends
			alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
			if len(alive_after) == 0:
				break
			
			# Bring next batsman
			if next_batsman < num_players:
				if dismissed_idx == striker_idx:
					striker_idx = next_batsman
				else:
					non_striker_idx = next_batsman
				next_batsman += 1
			else:
				if len(alive_after) == 1:
					striker_idx = alive_after[0]
					non_striker_idx = None
				else:
					break
		else:
			# Runs scored
			balls_faced = batsman.get('balls_faced') or 0
			fours = batsman.get('fours') or 0
			sixes = batsman.get('sixes') or 0
			four_rate = (fours / balls_faced) if balls_faced > 0 else 0.03
			six_rate = (sixes / balls_faced) if balls_faced > 0 else 0.01
			
			# Build probability distribution for [0,1,2,3,4,6]
			p4 = max(0.05, four_rate * 1.2)
			p6 = max(0.02, six_rate * 1.0)
			rem = max(0.0, 1.0 - (p4 + p6))
			base_split = [0.45, 0.35, 0.12, 0.08]
			base0123 = [rem * r for r in base_split]
			base = [base0123[0], base0123[1], base0123[2], base0123[3], p4, p6]
			
			# If last batsman, only even runs allowed
			if last_mode:
				odd_mass = base[1] + base[3]
				base[0] += odd_mass * 0.6
				base[2] += odd_mass * 0.4
				base[1] = 0.0
				base[3] = 0.0
			
			# Boost boundaries for strong batting advantage
			if ba > 0.5:
				boost = (ba - 0.5)
				base[4] += boost * 0.20
				base[5] += boost * 0.12
			
			# Normalize and sample
			s = sum(base)
			probs = [x / s for x in base]
			pick = random.random()
			cum = 0
			run = 0
			for idx, p in enumerate(probs):
				cum += p
				if pick <= cum:
					run = [0, 1, 2, 3, 4, 6][idx]
					break
			
			# Safety check for last mode
			if last_mode and (run % 2 == 1):
				run = 0
			
			total_runs += run
			runs_in_over += run
			pstats['runs'] += run
			pstats['balls'] += 1
			bstats['balls'] += 1
			bstats['runs'] += run
			
			# Swap strike on odd runs (not in last mode)
			if (not last_mode) and (run % 2 == 1):
				striker_idx, non_striker_idx = non_striker_idx, striker_idx
		
		balls_bowled += 1
		
		# Check if target reached
		if target is not None and total_runs >= target:
			# Store over summary data for output
			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_index, total_runs, total_wickets,
									bowlers_stats, over_bowler, batsmen_stats, batting_team,
									striker_idx, non_striker_idx, last_mode, per_over_fow, partial=True)
			break
		
		# End of over handling
		if (ball_no + 1) % balls_per_over == 0:
			# Check for maiden
			bowler_runs_this_over = bstats['runs'] - bowler_runs_start
			bowler_balls_this_over = bstats['balls'] - bowler_balls_start
			if bowler_balls_this_over == balls_per_over and bowler_runs_this_over == 0:
				bowlers_stats[over_bowler['player_id']]['maidens'] += 1
			
			# Store over summary for output
			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_index, total_runs, total_wickets,
									bowlers_stats, over_bowler, batsmen_stats, batting_team,
									striker_idx, non_striker_idx, last_mode, per_over_fow)
			
			# Swap strike only if not in last mode
			if not last_mode:
				striker_idx, non_striker_idx = non_striker_idx, striker_idx
		
		# Check if all out mid-over
		alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive_after) == 0:
			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_index, total_runs, total_wickets,
									bowlers_stats, over_bowler, batsmen_stats, batting_team,
									striker_idx, non_striker_idx, last_mode, per_over_fow, end=True)
			break
	
	# Handle final partial over if needed
	if output_config and output_config.over_by_over and balls_bowled > 0:
		last_ball_index = balls_bowled - 1
		if (last_ball_index + 1) % balls_per_over != 0:
			over_num = last_ball_index // balls_per_over + 1
			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_num, total_runs, total_wickets,
									bowlers_stats, over_bowler, batsmen_stats, batting_team,
									striker_idx, non_striker_idx, last_mode, per_over_fow, partial=True)
	
	# Convert bowler balls to overs
	for pid, b in bowlers_stats.items():
		overs = b['balls'] // balls_per_over
		balls_extra = b['balls'] % balls_per_over
		b['overs'] = f"{overs}.{balls_extra}" if b['balls'] > 0 else "0"
	
	return {
		'runs': total_runs,
		'wickets': total_wickets,
		'balls': balls_bowled,
		'batsmen': batsmen_stats,
		'bowlers': bowlers_stats,
	}


def _store_over_summary(output_config, over_index, total_runs, total_wickets,
						bowlers_stats, over_bowler, batsmen_stats, batting_team,
						striker_idx, non_striker_idx, last_mode, per_over_fow,
						partial=False, end=False):
	"""Store over summary data in output config for later display."""
	if not hasattr(output_config, 'over_summaries'):
		output_config.over_summaries = []
	
	bowler_pid = over_bowler['player_id']
	b = bowlers_stats[bowler_pid]
	overs_done = b['balls'] // 5
	balls_extra = b['balls'] % 5
	maidens = b.get('maidens', 0)
	
	batters_line = []
	if striker_idx is not None:
		s = batsmen_stats[batting_team[striker_idx]['player_id']]
		batters_line.append(f"{s['name']} {s['runs']}* ({s['balls']})")
	if non_striker_idx is not None and not last_mode:
		ns = batsmen_stats[batting_team[non_striker_idx]['player_id']]
		batters_line.append(f"{ns['name']} {ns['runs']}* ({ns['balls']})")
	
	label = "partial" if partial else ("end" if end else "")
	
	output_config.over_summaries.append({
		'over': over_index,
		'label': label,
		'score': f"{total_runs}/{total_wickets}",
		'bowler': f"{b['name']} {overs_done}.{balls_extra}-{maidens}-{b['runs']}-{b['wickets']}",
		'batters': batters_line,
		'fow': per_over_fow.copy()
	})
