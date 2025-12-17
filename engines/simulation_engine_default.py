"""
Simulation engine for TBONTB Cricket Simulator.
Simplified default engine: light stat influence with plenty of RNG.
"""

import random


def select_bowlers_from_team(team, keeper_id=None):
	"""
	Select bowlers from team, preferring players with bowling history.
	Excludes the wicketkeeper.
	Returns up to 8 bowlers.
	"""
	def is_keeper(player):
		"""Check if player is the keeper (handles both integer and string IDs)."""
		if keeper_id is None:
			return False
		if player['player_id'] == keeper_id:
			return True
		if isinstance(keeper_id, int) and player.get('short_int') == keeper_id:
			return True
		return False
	
	bowlers = [p for p in team if p.get("overs_bowled", 0) > 0 and not is_keeper(p)]
	if len(bowlers) >= 8:
		return random.sample(bowlers, 8)
	need = 8 - len(bowlers)
	others = [p for p in team if p not in bowlers and not is_keeper(p)]
	return bowlers + random.sample(others, min(need, len(others)))


def simulate_innings(batting_team, bowling_team, match_config, target=None, output_config=None, keeper_id=None):
	"""
	Run a single innings simulation with a RNG-first approach.
	keeper_id: player_id of the wicketkeeper (used for stumping)
	"""
	balls_per_over = match_config.balls_per_over
	max_overs = match_config.balls_per_innings // balls_per_over

	batsmen_stats = {
		p['player_id']: {
			'name': p['player_name'],
			'runs': 0,
			'balls': 0,
			'dismissed': False,
			'howout': '',
			'retired': False,
			'retired_once': False
		} for p in batting_team
	}

	if output_config and getattr(output_config, 'ball_by_ball', False):
		output_config.ball_by_ball_events = []

	team_extras = {
		'wides': 0,
		'no_balls': 0,
		'byes': 0,
		'leg_byes': 0,
		'penalty_runs': 0
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

	num_players = len(batting_team)
	batting_queue = list(range(num_players))
	striker_idx = batting_queue.pop(0) if len(batting_queue) > 0 else None
	non_striker_idx = batting_queue.pop(0) if len(batting_queue) > 0 else None

	bowlers = select_bowlers_from_team(bowling_team, keeper_id=keeper_id)
	num_bowlers = len(bowlers)

	total_runs = 0
	total_wickets = 0
	balls_bowled = 0
	legal_balls_bowled = 0

	per_over_fow = []
	over_bowler = None
	over_index = 1
	last_mode = False
	runs_in_over = 0
	wkts_in_over = 0
	bowler_runs_start = 0
	bowler_balls_start = 0
	bowler_wickets_start = 0
	display_ball_in_over = 1
	total_balls_in_over = 0
	legal_balls_in_over = 0
	penalty_in_over = 0
	free_hit = False
	carry_free_hit_next_over = False

	while over_index <= max_overs:
		bowler = bowlers[(over_index - 1) % num_bowlers]
		bstats = bowlers_stats[bowler['player_id']]

		if display_ball_in_over == 1 and total_balls_in_over == 0:
			per_over_fow = []
			over_bowler = bowler
			bowler_runs_start = bstats['runs']
			bowler_balls_start = bstats['balls']
			bowler_wickets_start = bstats['wickets']
			runs_in_over = 0
			wkts_in_over = 0
			legal_balls_in_over = 0

		alive = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive) == 0:
			break

		last_mode = (len(alive) == 1)
		if last_mode:
			striker_idx = alive[0]
			non_striker_idx = None

		batsman = batting_team[striker_idx]
		pstats = batsmen_stats[batsman['player_id']]

		bat_sr = batsman.get('strike_rate') or 95.0
		bat_avg = batsman.get('bat_avg') or 18.0
		bat_skill = max(0.0, min(1.0, (bat_sr - 70.0) / 90.0))
		bat_boundary_hint = (batsman.get('fours') or 0) + (batsman.get('sixes') or 0)

		bowler_wkts = bowler.get('wickets') or 0
		bowler_balls_hist = int((bowler.get('overs_bowled') or 0) * balls_per_over)
		bowler_wpb = (bowler_wkts / bowler_balls_hist) if bowler_balls_hist > 0 else 0.018
		bowl_skill = max(0.0, min(1.0, (bowler_wpb - 0.01) / 0.04))

		wicket_prob = 0.02 + (bowl_skill * 0.07) - (bat_skill * 0.03)
		wicket_prob = max(0.01, min(wicket_prob, 0.12))

		# Determine if this delivery is a penalty ball (wide/no-ball)
		penalty_ball = False
		is_wide = False
		is_no_ball = False
		# modest probability for penalty balls
		penalty_roll = random.random()
		if penalty_roll < 0.04:
			penalty_ball = True
			is_wide = penalty_roll < 0.02
			is_no_ball = not is_wide

		display_over = over_index - 1

		if penalty_ball:
			penalty_in_over += 1
			# Runs for penalty balls per LMS rules
			if over_index < max_overs:
				penalty_runs = 1 if penalty_in_over == 1 else 3
			else:
				penalty_runs = 1

			total_runs += penalty_runs
			runs_in_over += penalty_runs
			if is_wide:
				team_extras['wides'] += penalty_runs
			else:
				team_extras['no_balls'] += penalty_runs
			bstats['runs'] += penalty_runs
			pstats['balls'] += 1
			balls_bowled += 1
			total_balls_in_over += 1

			# Free hit handling
			if is_no_ball:
				if legal_balls_in_over >= balls_per_over and over_index < max_overs:
					carry_free_hit_next_over = True
				else:
					free_hit = True
			elif free_hit:
				# Penalty ball during free hit carries over
				free_hit = True

			if output_config and getattr(output_config, 'ball_by_ball', False):
				outcome_txt = 'Wide' if is_wide else 'No Ball'
				runs_word = 'run' if penalty_runs == 1 else 'runs'
				output_config.ball_by_ball_events.append({
					'ball': f"{display_over}.{display_ball_in_over}",
					'bowler': bowler.get('player_name', 'Unknown'),
					'batter': batsman.get('player_name', 'Unknown'),
					'outcome': f"{outcome_txt} +{penalty_runs} {runs_word}"
				})

			if target is not None and total_runs >= target:
				free_hit = False
				if output_config and output_config.over_by_over:
					_store_over_summary(output_config, over_index, total_runs, total_wickets,
									runs_in_over, wkts_in_over,
									bowlers_stats, over_bowler, batsmen_stats, batting_team,
									striker_idx, non_striker_idx, last_mode, per_over_fow,
									match_config.balls_per_over, partial=True)
				break

			# No over-end check here; over ends only after 5 legal balls
			continue

		if random.random() < wicket_prob and not free_hit:
			total_wickets += 1
			dismissed_idx = striker_idx

			dismissed_player = batting_team[dismissed_idx]
			dstats = batsmen_stats[dismissed_player['player_id']]
			dstats['balls'] += 1
			dstats['dismissed'] = True
			bowler_name = bowler.get('player_name', 'Unknown') or 'Unknown'
			bowler_surname = bowler_name.split()[-1]
			dismissal_type = random.choice(['Bowled', 'Caught', 'Caught and Bowled', 'Run Out', 'Stumped', 'LBW'])
			fielder_surname = None
			keeper_surname = None
			
			# Get wicketkeeper surname for stumping
			if keeper_id is not None:
				# Try to find keeper by matching either player_id directly or by short_int
				keeper = None
				for p in bowling_team:
					if p['player_id'] == keeper_id:
						keeper = p
						break
					# Also check if keeper_id matches the short_int (handles integer IDs vs prefixed IDs)
					if isinstance(keeper_id, int) and p.get('short_int') == keeper_id:
						keeper = p
						break
				
				if keeper:
					keeper_name = keeper.get('player_name', 'Unknown') or 'Unknown'
					keeper_surname = keeper_name.split()[-1]
			
			if dismissal_type in ['Caught', 'Run Out']:
				fielders = [p for p in bowling_team if p is not bowler]
				if fielders:
					fielder = random.choice(fielders)
					fname = fielder.get('player_name', 'Unknown') or 'Unknown'
					fielder_surname = fname.split()[-1]
				else:
					fielder_surname = 'Fielder'
			
			if dismissal_type == 'Bowled':
				howout_text = f"b {bowler_surname}"
			elif dismissal_type == 'Caught':
				howout_text = f"c {fielder_surname} b {bowler_surname}"
			elif dismissal_type == 'Caught and Bowled':
				howout_text = f"c&b {bowler_surname}"
			elif dismissal_type == 'Stumped':
				if keeper_surname:
					howout_text = f"st † {keeper_surname}"
				else:
					howout_text = f"st † Unknown"
			elif dismissal_type == 'LBW':
				howout_text = f"lbw b {bowler_surname}"
			else:
				howout_text = f"run out ({fielder_surname})"

			dstats['howout'] = howout_text
			bstats['balls'] += 1
			if dismissal_type != 'Run Out':
				bstats['wickets'] += 1

			fow_label = f"{display_over}.{display_ball_in_over}"
			per_over_fow.append((fow_label, dismissed_player['player_name'], dstats['runs'], dstats['balls'], dstats['howout']))
			wkts_in_over += 1

			if output_config and getattr(output_config, 'ball_by_ball', False):
				output_config.ball_by_ball_events.append({
					'ball': f"{display_over}.{display_ball_in_over}",
					'bowler': bowler.get('player_name', 'Unknown'),
					'batter': dismissed_player.get('player_name', 'Unknown'),
					'outcome': f"Wicket ({dismissal_type})"
				})

			alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
			balls_bowled += 1
			legal_balls_bowled += 1
			legal_balls_in_over += 1
			total_balls_in_over += 1
			display_ball_in_over += 1
			if len(alive_after) == 0:
				break

			if len(batting_queue) > 0:
				if dismissed_idx == striker_idx:
					striker_idx = batting_queue.pop(0)
					# If a returning retired batter comes in, mark them active again (but keep retired_once)
					batsmen_stats[batting_team[striker_idx]['player_id']]['retired'] = False
				else:
					non_striker_idx = batting_queue.pop(0) if len(batting_queue) > 0 else None
					if non_striker_idx is not None:
						batsmen_stats[batting_team[non_striker_idx]['player_id']]['retired'] = False
			else:
				if len(alive_after) == 1:
					striker_idx = alive_after[0]
					non_striker_idx = None
				else:
					break
		else:
			balls_faced = batsman.get('balls_faced') or 0
			fours = batsman.get('fours') or 0
			sixes = batsman.get('sixes') or 0
			four_rate = (fours / balls_faced) if balls_faced > 0 else 0.03
			six_rate = (sixes / balls_faced) if balls_faced > 0 else 0.01

			p4 = max(0.035, four_rate * 1.1 + bat_skill * 0.02)
			p6 = max(0.015, six_rate * 1.1 + bat_skill * 0.01)
			if bat_boundary_hint > 40:
				p4 += 0.004
				p6 += 0.003

			rem = max(0.0, 1.0 - (p4 + p6))
			base_split = [0.30, 0.38, 0.20, 0.12]
			base0123 = [rem * r for r in base_split]
			probs = [base0123[0], base0123[1], base0123[2], base0123[3], p4, p6]

			if last_mode:
				odd_mass = probs[1] + probs[3]
				probs[1] = 0.0
				probs[3] = 0.0
				probs[0] += odd_mass * 0.6
				probs[2] += odd_mass * 0.4

			total_prob = sum(probs)
			probs = [p / total_prob for p in probs]
			pick = random.random()
			cum = 0.0
			run = 0
			for idx, p in enumerate(probs):
				cum += p
				if pick <= cum:
					run = [0, 1, 2, 3, 4, 6][idx]
					break

			if last_mode and (run % 2 == 1):
				run = 0

			total_runs += run
			runs_in_over += run
			pstats['runs'] += run
			pstats['balls'] += 1
			bstats['balls'] += 1
			bstats['runs'] += run
			balls_bowled += 1
			legal_balls_bowled += 1
			legal_balls_in_over += 1
			free_hit = False

			# LMS format: retire batter only once when they first reach threshold and a replacement exists
			retirement_threshold = match_config.MATCH_TYPES.get(match_config.match_type, {}).get('retirement_threshold', None)
			retirement_note = ""
			if retirement_threshold and pstats['runs'] >= retirement_threshold and (not pstats['retired_once']) and len(batting_queue) > 0:
				pstats['retired'] = True
				pstats['retired_once'] = True
				retirement_note = f" - Retired on {pstats['runs']}"
				# Move retired batter to back of batting queue and bring next in
				batting_queue.append(striker_idx)
				striker_idx = batting_queue.pop(0)
				batsmen_stats[batting_team[striker_idx]['player_id']]['retired'] = False

			if output_config and getattr(output_config, 'ball_by_ball', False):
				runs_word = 'run' if run == 1 else 'runs'
				output_config.ball_by_ball_events.append({
					'ball': f"{display_over}.{display_ball_in_over}",
					'bowler': bowler.get('player_name', 'Unknown'),
					'batter': batsman.get('player_name', 'Unknown'),
					'outcome': f"{run} {runs_word}{retirement_note}"
				})

			if (not last_mode) and (run % 2 == 1):
				striker_idx, non_striker_idx = non_striker_idx, striker_idx

			total_balls_in_over += 1
			display_ball_in_over += 1

			if target is not None and total_runs >= target:
				if output_config and output_config.over_by_over:
					_store_over_summary(output_config, over_index, total_runs, total_wickets,
										 runs_in_over, wkts_in_over,
										 bowlers_stats, over_bowler, batsmen_stats, batting_team,
										 striker_idx, non_striker_idx, last_mode, per_over_fow,
										 match_config.balls_per_over, partial=True)
				break

		# End of over handling based on dynamic limits
		alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive_after) == 0:
			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_index, total_runs, total_wickets,
							 runs_in_over, wkts_in_over,
							 bowlers_stats, over_bowler, batsmen_stats, batting_team,
							 striker_idx, non_striker_idx, last_mode, per_over_fow,
							 match_config.balls_per_over, end=True)
			break

		# Recompute current over limit based on penalties bowled in this over
		if over_index < max_overs:
			current_over_limit = balls_per_over + (1 if penalty_in_over >= 1 else 0)
		else:
			current_over_limit = balls_per_over + penalty_in_over

		if legal_balls_in_over >= balls_per_over:
			bowler_runs_this_over = bstats['runs'] - bowler_runs_start
			if legal_balls_in_over == balls_per_over and bowler_runs_this_over == 0:
				bowlers_stats[over_bowler['player_id']]['maidens'] += 1

			if output_config and output_config.over_by_over:
				_store_over_summary(output_config, over_index, total_runs, total_wickets,
							 bowler_runs_this_over, wkts_in_over,
							 bowlers_stats, over_bowler, batsmen_stats, batting_team,
							 striker_idx, non_striker_idx, last_mode, per_over_fow,
							 match_config.balls_per_over)

			if not last_mode:
				striker_idx, non_striker_idx = non_striker_idx, striker_idx

			# prepare next over
			display_ball_in_over = 1
			total_balls_in_over = 0
			legal_balls_in_over = 0
			penalty_in_over = 0
			over_index += 1
			if carry_free_hit_next_over:
				free_hit = True
				carry_free_hit_next_over = False
			continue

	# Ensure final over summary if partial
	if output_config and output_config.over_by_over and balls_bowled > 0 and total_balls_in_over > 0:
		over_num = over_index
		_store_over_summary(output_config, over_num, total_runs, total_wickets,
							runs_in_over, wkts_in_over,
							bowlers_stats, over_bowler, batsmen_stats, batting_team,
							striker_idx, non_striker_idx, last_mode, per_over_fow,
							match_config.balls_per_over, partial=True)

	for pid, b in bowlers_stats.items():
		overs = b['balls'] // balls_per_over
		balls_extra = b['balls'] % balls_per_over
		b['overs'] = f"{overs}.{balls_extra}" if b['balls'] > 0 else "0"

	return {
		'runs': total_runs,
		'wickets': total_wickets,
		'balls': legal_balls_bowled,
		'batsmen': batsmen_stats,
		'bowlers': bowlers_stats,
		'extras': team_extras,
		'total_extras': sum(team_extras.values())
	}


def _store_over_summary(output_config, over_index, total_runs, total_wickets,
						over_runs, over_wkts,
						bowlers_stats, over_bowler, batsmen_stats, batting_team,
						striker_idx, non_striker_idx, last_mode, per_over_fow,
						balls_per_over, partial=False, end=False):
	"""Store over summary data in output config for later display."""
	if not hasattr(output_config, 'over_summaries'):
		output_config.over_summaries = []

	bowler_pid = over_bowler['player_id']
	b = bowlers_stats[bowler_pid]
	over_balls = b['balls']
	overs_done = over_balls // balls_per_over
	balls_extra = over_balls % balls_per_over
	maidens = b.get('maidens', 0)

	batters_line = []
	if striker_idx is not None:
		s = batsmen_stats[batting_team[striker_idx]['player_id']]
		retired_suffix = " - Retired" if s['retired'] else ""
		batters_line.append(f"{s['name']} {s['runs']}* ({s['balls']}){retired_suffix}")
	if non_striker_idx is not None and not last_mode:
		ns = batsmen_stats[batting_team[non_striker_idx]['player_id']]
		retired_suffix = " - Retired" if ns['retired'] else ""
		batters_line.append(f"{ns['name']} {ns['runs']}* ({ns['balls']}){retired_suffix}")

	label = "partial" if partial else ("end" if end else "")

	output_config.over_summaries.append({
		'over': over_index,
		'label': label,
		'score': f"{total_runs}/{total_wickets}",
		'over_runs': over_runs,
		'over_wkts': over_wkts,
		'bowler': f"{b['name']} {overs_done}.{balls_extra}-{maidens}-{b['runs']}-{b['wickets']}",
		'batters': batters_line,
		'fow': per_over_fow.copy()
	})
