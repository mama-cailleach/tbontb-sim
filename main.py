import json
import random
import os
import sys
import re
import time
import argparse
import datetime


DATA_DIR = os.path.join(os.path.dirname(__file__), "json")


def parse_float(s, default=None):
	if s is None or s == "":
		return default
	try:
		# remove stray characters like '*'
		return float(str(s).replace("*", ""))
	except Exception:
		return default


def load_players_summary():
	# prefer JSON summary if present
	json_path = os.path.join(os.path.dirname(__file__), "json", "TBONTB_players_summary.json")
	players = {}
	if os.path.exists(json_path):
		with open(json_path, encoding="utf-8") as f:
			try:
				rows = json.load(f)
			except Exception:
				rows = []
		for r in rows:
			raw_id = r.get("player_id")
			if raw_id is None:
				continue
			# canonical string id like TBONTB_0001 for compatibility with existing code
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
		# proceed to build SHORT_ID_INDEX below
	else:
		# require JSON summary only (CSV kept for reference but not used)
		print(f"JSON players summary not found at {json_path}. Please ensure the file exists in the json/ folder.")
		return players

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


def show_player_list(players):
	print("Available players (player_id : name)")
	for pid, p in sorted(players.items()):
		short = p.get('short_int') if p.get('short_int') is not None else ''
		pad = p.get('short_str') or ''
		print(f"  {short} : {p['player_name']}")


def choose_team(players, team_name="User"):
	pool = set(players.keys())
	#show_player_list(players) COMMENTED FOR NOW
	print(f"\nChoose 8 players for {team_name} by entering their IDs separated by commas.")
	while True:
		s = input("Enter 8 player IDs: ").strip()
		ids = [x.strip() for x in s.split(",") if x.strip()]
		if len(ids) != 8:
			print("Please enter exactly 8 player IDs.")
			continue
		# resolve inputs: accept full pid or short numeric forms like '1' or '0001'
		resolved = []
		bad = []
		for entry in ids:
			# direct full id
			if entry in players:
				resolved.append(players[entry])
				continue
			# try short index
			pid = None
			try:
				# normalize numeric attempts (strip leading +/zeros)
				if entry.isdigit():
					# try raw digits
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


def pick_computer_team(players, exclude_ids):
	pool = [p for pid, p in players.items() if pid not in exclude_ids]
	return random.sample(pool, 8)


def select_bowlers_from_team(team):
	# prefer players with bowling history
	bowlers = [p for p in team if p.get("overs_bowled", 0) > 0]
	if len(bowlers) >= 8:
		return random.sample(bowlers, 8)
	# pad with random other players
	need = 8 - len(bowlers)
	others = [p for p in team if p not in bowlers]
	return bowlers + random.sample(others, min(need, len(others)))


def simulate_innings(batting_team, bowling_team, balls=100, target=None, print_over_summary=False):
	# simple simulator for 100 balls
	# batting_team: list of player dicts (ordered)
	# bowling_team: list of player dicts (we'll rotate bowlers)

	batsmen_stats = {p['player_id']: {'name': p['player_name'], 'runs': 0, 'balls': 0, 'dismissed': False, 'howout': ''} for p in batting_team}
	bowlers_stats = {p['player_id']: {'name': p['player_name'], 'balls': 0, 'runs': 0, 'wickets': 0, 'maidens': 0} for p in bowling_team}

	# initial batsmen
	striker_idx = 0
	non_striker_idx = 1
	next_batsman = 2

	# select bowlers (rotate every 5-ball over)
	bowlers = select_bowlers_from_team(bowling_team)
	num_bowlers = len(bowlers)

	total_runs = 0
	total_wickets = 0
	balls_bowled = 0

	num_players = len(batting_team)
	for ball_no in range(balls):
		over = ball_no // 5
		bowler = bowlers[over % num_bowlers]
		bstats = bowlers_stats[bowler['player_id']]

		# start of over bookkeeping for per-over summary
		if ball_no % 5 == 0:
			per_over_start_balls = {pid: s['balls'] for pid, s in batsmen_stats.items()}
			runs_in_over = 0
			wickets_in_over = 0
			over_bowler = bowler
			over_index = over + 1
			start_striker = striker_idx
			start_non_striker = non_striker_idx
			# capture bowler stats at start of over to compute maiden/full-over runs
			bowler_runs_start = bstats['runs']
			bowler_balls_start = bstats['balls']
			per_over_fow = []

		# determine alive batsmen
		alive = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive) == 0:
			break
		last_mode = (len(alive) == 1)

		# if last mode, ensure the striker is the last alive batsman
		if last_mode:
			striker_idx = alive[0]
			non_striker_idx = None

		# prepare batsman and batsman stats
		batsman = batting_team[striker_idx]
		pstats = batsmen_stats[batsman['player_id']]

		# get batting rpb (runs per ball) from strike_rate or runs/balls
		# combine strike_rate and batting average to estimate runs-per-ball
		if batsman.get('strike_rate'):
			batsman_rpb = batsman['strike_rate'] / 100.0
		else:
			bf = batsman.get('balls_faced') or 0
			runs = batsman.get('runs') or 0
			batsman_rpb = (runs / bf) if bf > 0 else 0.8
		# small boost from batting average (higher avg -> slightly higher scoring consistency)
		if batsman.get('bat_avg'):
			bat_avg = batsman['bat_avg']
			# Balanced preset: scale between 0 and ~+33% for reasonable averages
			batsman_rpb *= (1.0 + min(max(bat_avg, 0), 100) / 300.0)

		# bowler runs per ball from economy if present
		if bowler.get('economy'):
			bowler_rpb = bowler['economy'] / 5.0
		else:
			# fallback: average
			bowler_rpb = (bowler.get('runs_conceded', 10) / max(1, (bowler.get('overs_bowled') or 1))) / 5.0
		# capture bowling average for influencing wicket chances
		bowler_bowl_avg = bowler.get('bowl_avg')
		bowler_wickets = bowler.get('wickets') or 0

		# batting advantage metric
		ba = batsman_rpb / (batsman_rpb + bowler_rpb + 1e-6)

		# base wicket probability (depends on batting advantage)
		base_wicket_prob = 0.02 + (1 - ba) * 0.18
		# adjust wicket probability by batting average (higher avg => more resistance)
		bat_avg = batsman.get('bat_avg') or 0
		# Balanced preset: batting average offers moderate protection
		bat_protect = 1.0 - min(max(bat_avg, 0), 100) / 180.0
		# adjust for bowler quality: lower bowling average increases wicket likelihood
		bowl_boost = 1.0
		if bowler_bowl_avg:
			# Balanced preset: make bowl_avg differences a bit more influential
			bowl_boost += max(0.0, (50.0 - bowler_bowl_avg) / 80.0)
		# also modest boost from bowler wickets experience (Balanced)
		bowl_boost *= (1.0 + min(bowler_wickets, 200) / 300.0)

		wicket_prob = base_wicket_prob * bowl_boost * bat_protect
		# clamp
		wicket_prob = max(0.01, min(wicket_prob, 0.5))

		r = random.random()
		if r < wicket_prob:
			# wicket - choose mode including Stumped and Run Out
			total_wickets += 1
			# possible modes and rough likelihoods
			mode_pick = random.random()
			if mode_pick < 0.4:
				mode = 'Bowled'
			elif mode_pick < 0.75:
				mode = 'Caught'
			elif mode_pick < 0.88:
				mode = 'Stumped'
			else:
				mode = 'Run Out'

			# determine who is dismissed (usually striker, but run outs can hit non-striker)
			dismissed_idx = striker_idx
			if mode == 'Run Out' and (not last_mode) and non_striker_idx is not None:
				# 70% striker, 30% non-striker for run-outs
				if random.random() < 0.3:
					dismissed_idx = non_striker_idx

			dismissed_player = batting_team[dismissed_idx]
			dstats = batsmen_stats[dismissed_player['player_id']]
			dstats['balls'] += 1
			dstats['dismissed'] = True
			dstats['howout'] = mode

			# update bowler stats: do not credit bowler with wicket for run-outs
			bstats['balls'] += 1
			# record fall-of-wicket for this over (label uses zero-based over like '0.2')
			ball_in_over = (ball_no % 5) + 1
			fow_label = f"{over}.{ball_in_over}"
			per_over_fow.append((fow_label, dismissed_player['player_name'], dstats['runs'], dstats['balls']))
			wickets_in_over += 1
			if mode != 'Run Out':
				bstats['wickets'] += 1

			# if that was the last batter, innings ends immediately
			alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
			if len(alive_after) == 0:
				break

			# otherwise bring next batsman if available, replacing the dismissed slot
			if next_batsman < num_players:
				if dismissed_idx == striker_idx:
					striker_idx = next_batsman
				else:
					non_striker_idx = next_batsman
				next_batsman += 1
			else:
				# if no next batsman but still someone alive, ensure striker/non-striker point correctly
				if len(alive_after) == 1:
					striker_idx = alive_after[0]
					non_striker_idx = None
				else:
					break
		else:
			# runs scored
			# Build player-specific base probabilities for [0,1,2,3,4,6]
			# start with default non-boundary distribution
			balls_faced = batsman.get('balls_faced') or 0
			fours = batsman.get('fours') or 0
			sixes = batsman.get('sixes') or 0
			four_rate = (fours / balls_faced) if balls_faced > 0 else 0.03
			six_rate = (sixes / balls_faced) if balls_faced > 0 else 0.01
			# map boundary empirical rates into ball-level probabilities (Balanced scaling)
			p4 = max(0.03, four_rate * 0.8)
			p6 = max(0.01, six_rate * 0.8)
			# remaining mass to distribute to 0/1/2/3
			rem = max(0.0, 1.0 - (p4 + p6))
			# base split for non-boundary events (favor dot and single)
			base_split = [0.6, 0.25, 0.1, 0.05]
			base0123 = [rem * r for r in base_split]
			base = [base0123[0], base0123[1], base0123[2], base0123[3], p4, p6]

			# if last batsman only even runs allowed (no 1s or 3s), redistribute odd mass
			if last_mode:
				odd_mass = base[1] + base[3]
				base[0] += odd_mass * 0.6
				base[2] += odd_mass * 0.4
				base[1] = 0.0
				base[3] = 0.0

			# boost boundaries for stronger batting advantage
			if ba > 0.5:
				boost = (ba - 0.5)
				# Balanced preset: slightly stronger boundary uplift for positive batting advantage
				base[4] += boost * 0.18
				base[5] += boost * 0.10

			# normalize and sample
			s = sum(base)
			probs = [x / s for x in base]
			pick = random.random()
			cum = 0
			run = 0
			for idx, p in enumerate(probs):
				cum += p
				if pick <= cum:
					run = [0,1,2,3,4,6][idx]
					break

			# if last_mode and an odd run is somehow picked, force it to next even (shouldn't happen)
			if last_mode and (run % 2 == 1):
				run = 0

			total_runs += run
			runs_in_over += run
			pstats['runs'] += run
			pstats['balls'] += 1
			bstats['balls'] += 1
			bstats['runs'] += run

			# swap strike on odd runs (but in last mode odd runs are not possible)
			if (not last_mode) and (run % 2 == 1):
				striker_idx, non_striker_idx = non_striker_idx, striker_idx

		# if chasing a target, stop as soon as target is reached or passed
		balls_bowled += 1
		if target is not None and total_runs >= target:
			# innings over - chasing team has reached the target
			# print end-of-over (partial) summary if requested
			if print_over_summary:
				# bowler cumulative figures
				bowler_pid = over_bowler['player_id']
				b = bowlers_stats[bowler_pid]
				overs_done = b['balls'] // 5
				balls_extra = b['balls'] % 5
				maidens = b.get('maidens', 0)
				print(f"Over {over_index} (partial): {total_runs}/{total_wickets}")
				print(f"Bowler: {b['name']} {overs_done}-{maidens}-{b['runs']}-{b['wickets']}")
				# batters currently in (striker/non-striker)
				batters_line = []
				if striker_idx is not None:
					s = batsmen_stats[batting_team[striker_idx]['player_id']]
					batters_line.append(f"{s['name']} {s['runs']}* ({s['balls']})")
				if non_striker_idx is not None:
					ns = batsmen_stats[batting_team[non_striker_idx]['player_id']]
					batters_line.append(f"{ns['name']} {ns['runs']}* ({ns['balls']})")
				print("Batters: " + " | ".join(batters_line))
				if per_over_fow:
					print("FOW:")
					for f in per_over_fow:
						label, name, rr, bb = f
						print(f"{label} Wicket: {name} {rr}({bb})")
			break

		# end of over swap (no swap in last mode since only one batsman)
		if (ball_no + 1) % 5 == 0 and (not last_mode):
			# determine runs conceded by bowler this over
			bowler_runs_this_over = bstats['runs'] - bowler_runs_start
			bowler_balls_this_over = bstats['balls'] - bowler_balls_start
			# if full over (5 balls) and zero runs, count as maiden
			if bowler_balls_this_over == 5 and bowler_runs_this_over == 0:
				bowlers_stats[over_bowler['player_id']]['maidens'] += 1
			if print_over_summary:
				# bowler cumulative figures
				bowler_pid = over_bowler['player_id']
				b = bowlers_stats[bowler_pid]
				overs_done = b['balls'] // 5
				balls_extra = b['balls'] % 5
				maidens = b.get('maidens', 0)
				print(f"Over {over_index}: {total_runs}/{total_wickets}")
				print(f"Bowler: {b['name']} {overs_done}-{maidens}-{b['runs']}-{b['wickets']}")
				# batters currently in (striker/non-striker)
				batters_line = []
				if striker_idx is not None:
					s = batsmen_stats[batting_team[striker_idx]['player_id']]
					batters_line.append(f"{s['name']} {s['runs']}* ({s['balls']})")
				if non_striker_idx is not None:
					ns = batsmen_stats[batting_team[non_striker_idx]['player_id']]
					batters_line.append(f"{ns['name']} {ns['runs']}* ({ns['balls']})")
				print("Batters: " + " | ".join(batters_line))
				if per_over_fow:
					print("FOW:")
					for f in per_over_fow:
						label, name, rr, bb = f
						print(f"{label} Wicket: {name} {rr}({bb})")
			striker_idx, non_striker_idx = non_striker_idx, striker_idx
		# if the innings ended mid-over due to all out, print a partial over summary
		alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
		if len(alive_after) == 0:
			if print_over_summary:
				# partial over summary at innings end
				b = bowlers_stats[over_bowler['player_id']]
				overs_done = b['balls'] // 5
				maidens = b.get('maidens', 0)
				print(f"Over {over_index} (end): {total_runs}/{total_wickets}")
				print(f"Bowler: {b['name']} {overs_done}-{maidens}-{b['runs']}-{b['wickets']}")
				# batters currently in
				batters_line = []
				if alive_after:
					for idx in alive_after:
						s = batsmen_stats[batting_team[idx]['player_id']]
						batters_line.append(f"{s['name']} {s['runs']}* ({s['balls']})")
				print("Batters: " + " | ".join(batters_line))
				if per_over_fow:
					print("FOW:")
					for f in per_over_fow:
						label, name, rr, bb = f
						print(f"{label} Wicket: {name} {rr}({bb})")
			break

	# convert bowlers stats balls to overs (5-ball overs)
	for pid, b in bowlers_stats.items():
		overs = b['balls'] // 5
		balls_extra = b['balls'] % 5
		b['overs'] = f"{overs}.{balls_extra}" if b['balls'] > 0 else "0"

	return {
		'runs': total_runs,
		'wickets': total_wickets,
		'balls': balls_bowled,
		'batsmen': batsmen_stats,
		'bowlers': bowlers_stats,
	}


def print_innings_summary(team_name, innings):
	# format overs from total balls (5-ball overs)
	total_balls = innings.get('balls', 0)
	overs = total_balls // 5
	balls_extra = total_balls % 5
	print(f"\n{team_name} innings: {innings['runs']} / {innings['wickets']} ({overs}.{balls_extra} Overs)")
	print("BATTING:")
	for pid, s in innings['batsmen'].items():
		if s['dismissed']:
			print(f"  {s['name']}: {s['runs']} ({s['balls']}) - {s['howout']}")
		else:
			# batsman still in
			if s['balls'] > 0:
				print(f"  {s['name']}: {s['runs']}* ({s['balls']}) - Not Out")
			else:
				print(f"  {s['name']}: DNB")
	print("BOWLING:")
	for pid, s in innings['bowlers'].items():
		# show overs-maidens-runs-wickets if maidens present
		maidens = s.get('maidens', 0)
		overs = s.get('overs', '0')
		print(f"  {s['name']}: {overs}-{maidens}-{s['runs']}-{s['wickets']}")


def export_match_json(path, match_obj):
	"""Write match_obj (a serializable dict) to path (dir) with timestamped filename."""
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


def main():
	parser = argparse.ArgumentParser(description='TBONTB Simple Cricket Simulator - Prototype')
	parser.add_argument('--demo', action='store_true', help='Run a non-interactive demo match')
	parser.add_argument('--seed', type=int, help='Random seed for deterministic demo')
	parser.add_argument('--export-json', action='store_true', help='Export match boxscore to json/')
	args = parser.parse_args()

	if args.seed is not None:
		random.seed(args.seed)

	print(DATA_DIR)
	print("TBONTB Simple Cricket Simulator - Prototype")
	players = load_players_summary()
	if not players:
		print("No players loaded. Please ensure csv/TBONTB_players_summary.csv exists.")
		sys.exit(1)

	if args.demo:
		# Non-interactive demo: pick two random teams from the pool
		pool = list(players.values())
		random.shuffle(pool)
		user_team = pool[:8]
		comp_team = pool[8:16]
		print("Demo mode: Teams selected automatically.")
		print("User team:")
		for p in user_team:
			print(f"  {p['player_name']}")
		print("Computer team:")
		for p in comp_team:
			print(f"  {p['player_name']}")
		choice = 'bat'  # default demo choice: user bats first
	else:
		user_team = choose_team(players, "User")
		exclude = [p['player_id'] for p in user_team]
		comp_team = pick_computer_team(players, exclude)
		print("\nComputer team selected:")
		for p in comp_team:
			print(f"  {p['player_name']}")

	# choose bat or bowl
	if not args.demo:
		while True:
			choice = input("Do you want to bat first or bowl first? (bat/bowl): ").strip().lower()
			if choice in ('bat', 'bowl'):
				break
			print("Please type 'bat' or 'bowl'.")

	if choice == 'bat':
		first_batting = ('User', user_team)
		second_batting = ('Computer', comp_team)
	else:
		first_batting = ('Computer', comp_team)
		second_batting = ('User', user_team)

	print(f"\nSimulating first innings: {first_batting[0]} batting...")
	if not args.demo:
		time.sleep(5)  # brief pause for realism
	first = simulate_innings(first_batting[1], second_batting[1], print_over_summary=True)
	print_innings_summary(first_batting[0], first)

	print(f"\nSimulating second innings: {second_batting[0]} batting...")
	if not args.demo:
		time.sleep(5)  # brief pause for realism
	# set a chase target: need one more than the first innings
	target_score = first['runs'] + 1
	second = simulate_innings(second_batting[1], first_batting[1], target=target_score, print_over_summary=True)
	print_innings_summary(second_batting[0], second)

	# decide winner
	if first['runs'] > second['runs']:
		winner = first_batting[0]
		margin = first['runs'] - second['runs']
		print(f"\nFinal Result:\n{winner} won by {margin} runs")
	elif second['runs'] > first['runs']:
		winner = second_batting[0]
		# wickets remaining = team size - wickets lost
		wickets_remaining = len(second_batting[1]) - second['wickets']
		print(f"\nFinal Result:\n{winner} won by {wickets_remaining} wickets")
	else:
		print("\nFinal Result:\nMatch tied")

	# optional export
	if args.export_json:
		# build serializable match object
		match_obj = {
			"date": datetime.datetime.now().isoformat(),
			"teams": {
				first_batting[0]: [{"player_id": p.get('player_id'), "player_name": p.get('player_name')} for p in first_batting[1]],
				second_batting[0]: [{"player_id": p.get('player_id'), "player_name": p.get('player_name')} for p in second_batting[1]],
			},
			"first_innings": {
				"team": first_batting[0],
				"runs": first['runs'],
				"wickets": first['wickets'],
				"balls": first['balls'],
				"batsmen": [],
				"bowlers": [],
			},
			"second_innings": {
				"team": second_batting[0],
				"runs": second['runs'],
				"wickets": second['wickets'],
				"balls": second['balls'],
				"batsmen": [],
				"bowlers": [],
			},
			"result": {
				"text": (f"{winner} won by {margin} runs") if first['runs'] != second['runs'] else (f"{winner} won by {wickets_remaining} wickets" if first['runs'] != second['runs'] else "Match tied")
			}
		}
		# populate batsmen and bowlers lists for both innings
		for pid, b in first['batsmen'].items():
			match_obj['first_innings']['batsmen'].append({
				"player_id": pid,
				"name": b['name'],
				"runs": b['runs'],
				"balls": b['balls'],
				"dismissed": b['dismissed'],
				"howout": b.get('howout', '')
			})
		for pid, b in first['bowlers'].items():
			match_obj['first_innings']['bowlers'].append({
				"player_id": pid,
				"name": b['name'],
				"overs": b.get('overs'),
				"maidens": b.get('maidens', 0),
				"runs": b.get('runs', 0),
				"wickets": b.get('wickets', 0)
			})
		for pid, b in second['batsmen'].items():
			match_obj['second_innings']['batsmen'].append({
				"player_id": pid,
				"name": b['name'],
				"runs": b['runs'],
				"balls": b['balls'],
				"dismissed": b['dismissed'],
				"howout": b.get('howout', '')
			})
		for pid, b in second['bowlers'].items():
			match_obj['second_innings']['bowlers'].append({
				"player_id": pid,
				"name": b['name'],
				"overs": b.get('overs'),
				"maidens": b.get('maidens', 0),
				"runs": b.get('runs', 0),
				"wickets": b.get('wickets', 0)
			})
		# write to json/ directory next to script
		export_dir = os.path.join(os.path.dirname(__file__), 'json')
		export_match_json(export_dir, match_obj)


if __name__ == '__main__':
	main()