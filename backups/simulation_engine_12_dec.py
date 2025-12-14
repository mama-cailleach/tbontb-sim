"""
Simulation engine for TBONTB Cricket Simulator.
Contains the core ball-by-ball simulation logic.
"""

import random
import math


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

	# Precompute expectations per player (simple priors from historical SR/avg; blanks yield None)
	batter_expect = {}
	for p in batting_team:
		sr = p.get('strike_rate') or 0.0
		bat_avg_stat = p.get('bat_avg') or 0.0
		if sr > 0:
			exp_rpb = sr / 100.0
		else:
			exp_rpb = None
		# Expected runs per innings from batting average; cap small for blanks
		exp_runs_inn = bat_avg_stat if bat_avg_stat and bat_avg_stat > 0 else None
		batter_expect[p['player_id']] = {
			'exp_rpb': exp_rpb,
			'exp_runs_inn': exp_runs_inn
		}

	bowler_expect = {}
	for p in bowling_team:
		w = p.get('wickets') or 0
		balls_bowled = int((p.get('overs_bowled') or 0) * balls_per_over)
		exp_wpb = (w / balls_bowled) if balls_bowled > 0 else None
		bowler_expect[p['player_id']] = {
			'exp_wpb': exp_wpb
		}

	# Reset ball-by-ball log per innings if enabled
	if output_config and getattr(output_config, 'ball_by_ball', False):
		output_config.ball_by_ball_events = []
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

	# Precompute bowling average distribution for centered boosts
	bowl_avgs = [p.get('bowl_avg') for p in bowling_team if p.get('bowl_avg')]
	if bowl_avgs:
		bowl_avg_mean = sum(bowl_avgs) / len(bowl_avgs)
		variance = sum((x - bowl_avg_mean) ** 2 for x in bowl_avgs) / max(1, len(bowl_avgs) - 1)
		bowl_avg_sd = math.sqrt(variance) if variance > 0 else 0.0
	else:
		bowl_avg_mean = None
		bowl_avg_sd = 0.0
	
	total_runs = 0
	total_wickets = 0
	balls_bowled = 0
	wicket_cooldown = False
	
	# Detect if batting team is mostly blank (for economy anchor scaling)
	batting_team_avg = sum(p.get('bat_avg', 0) for p in batting_team) / len(batting_team) if batting_team else 0
	is_blank_batting_team = batting_team_avg < 15  # Neutral_Blank team has avg ~0-5
	
	num_players = len(batting_team)
	
	# Ball-by-ball simulation
	for ball_no in range(balls):
		over = ball_no // balls_per_over
		bowler = bowlers[over % num_bowlers]
		bstats = bowlers_stats[bowler['player_id']]
		ball_in_over = (ball_no % balls_per_over) + 1
		
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
		
		# Calculate batsman runs-per-ball from historical strike rate
		sr = batsman.get('strike_rate') or 0.0
		bat_avg_stat = batsman.get('bat_avg') or 0.0
		
		# RPB = Strike Rate / 100 (primary)
		if sr > 0:
			batsman_rpb = sr / 100.0
		else:
			# Fallback: runs/balls from historical if no SR
			bf = batsman.get('balls_faced') or 0
			runs = batsman.get('runs') or 0
			batsman_rpb = (runs / bf) if bf > 0 else 0.8
		
		# Calculate batting skill for modulation (0 to 1 scale)
		quality_sr = max(0.0, min(1.0, (sr - 80.0) / 120.0))
		quality_avg = max(0.0, min(1.0, (bat_avg_stat - 15.0) / 35.0))
		bat_skill = 0.5 * quality_sr + 0.5 * quality_avg
		
		# Check if this is a statless (blank) player
		statless_batter = all((sr or 0) == 0 for sr in [batsman.get('strike_rate'), batsman.get('runs'), batsman.get('balls_faced'), batsman.get('fours'), batsman.get('sixes'), batsman.get('bat_avg')])
		
		# Modest average boost for better context
		if batsman.get('bat_avg'):
			batsman_rpb *= (1.0 + min(max(bat_avg_stat, 0), 100) / 420.0)
		
		# Blank players: use floor to prevent zero scoring
		if statless_batter:
			batsman_rpb = max(batsman_rpb, 0.35)
		
		# Floor for blank/neutral players to prevent over-suppression
		if bat_avg_stat == 0 and sr == 0:
			batsman_rpb = max(batsman_rpb, 0.35)  # Neutral baseline: ~35% SR

		# Apply expectation guardrails ONLY for weak but real players, not blanks
		exp_info = batter_expect.get(batsman['player_id'], {})
		exp_rpb = exp_info.get('exp_rpb')
		
		# Calculate bowler wicket skill (strike-rate like) rather than economy
		bowler_bowl_avg = bowler.get('bowl_avg')
		bowler_wickets = bowler.get('wickets') or 0
		bowler_econ = bowler.get('economy') or 10.0
		statless_bowler = all((bowler.get(k) or 0) == 0 for k in ['wickets', 'overs_bowled', 'runs_conceded', 'economy', 'bowl_avg'])

		bowler_exp = bowler_expect.get(bowler['player_id'], {})
		bowler_wicket_rate = bowler_exp.get('exp_wpb')
		if bowler_wicket_rate is None:
			balls_bowled_hist = int((bowler.get('overs_bowled') or 0) * balls_per_over)
			bowler_wicket_rate = (bowler_wickets / balls_bowled_hist) if balls_bowled_hist > 0 else 0.018
		bowl_wicket_strength = max(0.006, min(0.08, bowler_wicket_rate)) * 40.0

		# Batting advantage metric (runs potential vs wicket-taking threat)
		ba = batsman_rpb / (batsman_rpb + bowl_wicket_strength + 1e-6)

		# Base wicket probability with softer slope
		base_wicket_prob = 0.0075 + (1 - ba) * 0.045
		bat_avg = batsman.get('bat_avg') or 0
		bat_protect = 1.0 - min(max(bat_avg, 0), 80) * 0.00275
		bat_protect = max(0.75, min(1.05, bat_protect))

		# Recentered bowl boost using z-score on bowling average, no wickets compounding
		bowl_boost = 1.0
		if bowler_bowl_avg and bowl_avg_mean:
			if bowl_avg_sd > 0:
				z = (bowl_avg_mean - bowler_bowl_avg) / bowl_avg_sd
			else:
				z = 0.0
			bowl_boost += max(-0.08, min(0.08, z * 0.04))
		bowl_boost = max(0.92, min(1.08, bowl_boost))

		wicket_prob = base_wicket_prob * bowl_boost * bat_protect

		# Additive pressure (bounded) when batter exceeds priors; no econ coupling
		hist_avg = bat_avg if bat_avg > 0 else None
		hist_sr = batsman.get('strike_rate') or 0
		runs_so_far = pstats['runs']
		balls_so_far = pstats['balls'] if pstats['balls'] > 0 else 1
		exp_info = batter_expect.get(batsman['player_id'], {})
		exp_rpb = exp_info.get('exp_rpb')
		exp_runs_inn = exp_info.get('exp_runs_inn')
		exp_runs_so_far = (exp_rpb * balls_so_far) if exp_rpb else None
		pressure_add = 0.0
		if hist_avg and runs_so_far > hist_avg:
			excess = (runs_so_far - hist_avg) / max(hist_avg * 1.2, 12.0)
			pressure_add += min(0.18, excess * 0.22)
		if hist_sr and hist_sr > 0 and balls_so_far >= 6:
			sim_sr = (runs_so_far / balls_so_far) * 100.0
			if sim_sr > hist_sr:
				sr_excess = (sim_sr - hist_sr) / max(40.0, hist_sr)
				pressure_add += min(0.16, sr_excess * 0.20)
		if exp_runs_so_far and runs_so_far > exp_runs_so_far:
			over_run_ratio = runs_so_far / max(1.0, exp_runs_so_far)
			pressure_add += min(0.14, (over_run_ratio - 1.0) * 0.18)
		if exp_runs_inn and runs_so_far > exp_runs_inn * 1.2:
			pressure_add += 0.08
		wicket_prob *= (1.0 + min(0.35, pressure_add))

		# Flow guardrails: cooldown after wicket and soft cap per over
		if wicket_cooldown:
			wicket_prob *= 0.70
		if wickets_in_over >= 2:
			wicket_prob *= 0.80

		wicket_prob = max(0.004, min(wicket_prob, 0.08))
		
		# Roll for wicket
		r = random.random()
		if r < wicket_prob:
			# Wicket!
			total_wickets += 1
			wicket_cooldown = True
			
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
			fow_label = f"{over}.{ball_in_over}"
			per_over_fow.append((fow_label, dismissed_player['player_name'], dstats['runs'], dstats['balls']))
			wickets_in_over += 1
			
			if mode != 'Run Out':
				bstats['wickets'] += 1
			
			# Log ball event
			if output_config and getattr(output_config, 'ball_by_ball', False):
				bowler_name = bowler.get('player_name', 'Unknown')
				batter_name = batsman.get('player_name', 'Unknown')
				label = f"{over}.{ball_in_over}"
				output_config.ball_by_ball_events.append({
					'ball': label,
					'bowler': bowler_name,
					'batter': batter_name,
					'outcome': f"wicket ({mode})"
				})

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
			wicket_cooldown = False
			balls_faced = batsman.get('balls_faced') or 0
			fours = batsman.get('fours') or 0
			sixes = batsman.get('sixes') or 0
			four_rate = (fours / balls_faced) if balls_faced > 0 else 0.03
			six_rate = (sixes / balls_faced) if balls_faced > 0 else 0.01
		
			# Build probability distribution for [0,1,2,3,4,6]
			# Raise run flow: fewer dots, higher boundary floors
			p4 = max(0.0335, four_rate * 1.02)
			p6 = max(0.0170, six_rate * 1.02)
			# Relaxed dampening: (0.60 + 0.70*bat_skill) allows better boundary expression
			p4 *= (0.60 + 0.70 * bat_skill)
			p6 *= (0.60 + 0.70 * bat_skill)
			# Balanced floors: economy 7.0-7.2, SR 125-128%
			p4 = max(0.0418, p4)  # At least 4.18% fours
			p6 = max(0.0162, p6)  # At least 1.62% sixes
			p4 += 0.0113
			p6 += 0.0077
			
			# Conditional boundary uplift for strong batters only (avg >= 25)
			if bat_avg_stat and bat_avg_stat >= 25:
				p4 += 0.0011
				p6 += 0.0011
			
			rem = max(0.0, 1.0 - (p4 + p6))
			base_split = [0.33 - 0.06 * bat_skill, 0.37 + 0.05 * bat_skill, 0.21 + 0.02 * bat_skill, 0.09 + 0.02 * bat_skill]
			base0123 = [rem * r for r in base_split]
			base = [base0123[0], base0123[1], base0123[2], base0123[3], p4, p6]
			
			# If last batsman, only even runs allowed
			if last_mode:
				odd_mass = base[1] + base[3]
				base[0] += odd_mass * 0.6
				base[2] += odd_mass * 0.4
				base[1] = 0.0
				base[3] = 0.0

			# Economy adjustment: re-anchor to historical, but detect blanks
			hist_econ = bowler.get('economy')
			is_blank_bowler = statless_bowler or (hist_econ and hist_econ == 10.0 and bowler_bowl_avg and bowler_bowl_avg >= 50)
			
			if is_blank_batting_team:
				# Batting team is blank: scale economy UP to simulate facing real batters
				# Use a multiplier to compensate for blank batters not scoring
				target_econ = hist_econ * 1.15 if hist_econ else 11.5  # 15% boost
			elif is_blank_bowler:
				# Bowler is blank, use league average
				target_econ = 9.0
			else:
				# Real bowler vs real batter, use historical
				target_econ = hist_econ if hist_econ else 11.5
			
			econ_adjust_run = target_econ / max(1e-3, bowler_econ)
			econ_adjust_run = max(0.55, min(econ_adjust_run, 2.0))
			
			# Add stochastic leakage variance (±10%)
			leakage = random.uniform(0.90, 1.20)
			econ_adjust_run *= leakage
			
			# Add bowler fatigue over time
			overs_bowled_now = bstats['balls'] // balls_per_over
			fatigue_factor = 1.0 + 0.02 * overs_bowled_now
			econ_adjust_run *= fatigue_factor
			
			base[0] *= 1.0 / econ_adjust_run
			for idx in range(1, len(base)):
				base[idx] *= econ_adjust_run
			
			# Boost boundaries for strong batting advantage, scaled by batting skill (smaller)
			if ba > 0.5:
				boost = (ba - 0.5)
				skill_scale = 0.45 + 0.35 * bat_skill
				base[4] += boost * 0.08 * skill_scale
				base[5] += boost * 0.05 * skill_scale

			# SR floor uplift for naturally quick players; tiny
			sr = batsman.get('strike_rate') or 0.0
			sr_floor_boost = max(0.0, (sr - 135.0) / 280.0)
			base[4] += sr_floor_boost * 0.006
			base[5] += sr_floor_boost * 0.003
			
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

			# Log ball event
			if output_config and getattr(output_config, 'ball_by_ball', False):
				bowler_name = bowler.get('player_name', 'Unknown')
				batter_name = batsman.get('player_name', 'Unknown')
				label = f"{over}.{ball_in_over}"
				outcome_desc = f"{run} runs"
				output_config.ball_by_ball_events.append({
					'ball': label,
					'bowler': bowler_name,
					'batter': batter_name,
					'outcome': outcome_desc
				})
			
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
