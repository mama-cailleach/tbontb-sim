import csv
import random
import os
import sys
import re
import time


DATA_DIR = os.path.join(os.path.dirname(__file__), "csv")


def parse_float(s, default=None):
	if s is None or s == "":
		return default
	try:
		# remove stray characters like '*'
		return float(str(s).replace("*", ""))
	except Exception:
		return default


def load_players_summary():
	path = os.path.join(DATA_DIR, "TBONTB_players_summary.csv")
	players = {}
	if not os.path.exists(path):
		print(f"Players summary not found at {path}")
		return players

	# use utf-8-sig to gracefully handle files that include a UTF-8 BOM
	with open(path, encoding="utf-8-sig") as f:
		reader = csv.DictReader(f)
		for r in reader:
			pid = r.get("player_id")
			if not pid:
				continue
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
				# batting
				"matches": int(r.get("matches") or 0),
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


def show_player_list(players):
	print("Available players (player_id : name)")
	for pid, p in sorted(players.items()):
		short = p.get('short_int') if p.get('short_int') is not None else ''
		pad = p.get('short_str') or ''
		print(f"  {short} : {p['player_name']}")


def choose_team(players, team_name="User"):
	pool = set(players.keys())
	show_player_list(players)
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


def simulate_innings(batting_team, bowling_team, balls=100):
	# simple simulator for 100 balls
	# batting_team: list of player dicts (ordered)
	# bowling_team: list of player dicts (we'll rotate bowlers)

	batsmen_stats = {p['player_id']: {'name': p['player_name'], 'runs': 0, 'balls': 0, 'dismissed': False, 'howout': ''} for p in batting_team}
	bowlers_stats = {p['player_id']: {'name': p['player_name'], 'balls': 0, 'runs': 0, 'wickets': 0} for p in bowling_team}

	# initial batsmen
	striker_idx = 0
	non_striker_idx = 1
	next_batsman = 2

	# select bowlers (rotate every 5-ball over)
	bowlers = select_bowlers_from_team(bowling_team)
	num_bowlers = len(bowlers)

	total_runs = 0
	total_wickets = 0

	num_players = len(batting_team)
	for ball_no in range(balls):
		over = ball_no // 5
		bowler = bowlers[over % num_bowlers]
		bstats = bowlers_stats[bowler['player_id']]

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
		if batsman.get('strike_rate'):
			batsman_rpb = batsman['strike_rate'] / 100.0
		else:
			bf = batsman.get('balls_faced') or 0
			runs = batsman.get('runs') or 0
			batsman_rpb = (runs / bf) if bf > 0 else 0.8

		# bowler runs per ball from economy if present
		if bowler.get('economy'):
			bowler_rpb = bowler['economy'] / 5.0
		else:
			# fallback: average
			bowler_rpb = (bowler.get('runs_conceded', 10) / max(1, (bowler.get('overs_bowled') or 1))) / 5.0

		# batting advantage metric
		ba = batsman_rpb / (batsman_rpb + bowler_rpb + 1e-6)

		# wicket probability increases when bowling is strong
		wicket_prob = 0.02 + (1 - ba) * 0.18

		r = random.random()
		if r < wicket_prob:
			# wicket
			total_wickets += 1
			pstats['balls'] += 1
			pstats['dismissed'] = True
			pstats['howout'] = 'Bowled' if random.random() < 0.5 else 'Caught'
			bstats['balls'] += 1
			bstats['wickets'] += 1

			# if that was the last batter, innings ends immediately
			alive_after = [i for i, p in enumerate(batting_team) if not batsmen_stats[p['player_id']]['dismissed']]
			if len(alive_after) == 0:
				break
			# otherwise bring next batsman if available
			if next_batsman < num_players:
				striker_idx = next_batsman
				next_batsman += 1
			else:
				# if no next batsman but still someone alive, ensure striker points to them
				if len(alive_after) == 1:
					striker_idx = alive_after[0]
				else:
					break
		else:
			# runs scored
			# base probabilities influenced by batting advantage
			# base distribution for [0,1,2,3,4,6]
			base = [0.50, 0.30, 0.08, 0.01, 0.08, 0.03]
			# if last batsman only even runs allowed (no 1s or 3s)
			if last_mode:
				# shift odd-run probabilities into 0/2 slots conservatively
				# remove indices 1 and 3 (1 and 3 runs)
				base[0] += base[1] * 0.6 + base[3] * 0.6
				base[2] += base[1] * 0.4
				base[4] += base[3] * 0.4
				base[1] = 0.0
				base[3] = 0.0
			# boost boundary chances by ba
			boost = ba - 0.5
			if boost > 0:
				# increase 4/6 chance proportionally
				base[4] += boost * 0.1
				base[5] += boost * 0.05
			# normalize
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
			pstats['runs'] += run
			pstats['balls'] += 1
			bstats['balls'] += 1
			bstats['runs'] += run

			# swap strike on odd runs (but in last mode odd runs are not possible)
			if (not last_mode) and (run % 2 == 1):
				striker_idx, non_striker_idx = non_striker_idx, striker_idx

		# end of over swap (no swap in last mode since only one batsman)
		if (ball_no + 1) % 5 == 0 and (not last_mode):
			striker_idx, non_striker_idx = non_striker_idx, striker_idx

	# convert bowlers stats balls to overs (5-ball overs)
	for pid, b in bowlers_stats.items():
		overs = b['balls'] // 5
		balls_extra = b['balls'] % 5
		b['overs'] = f"{overs}.{balls_extra}" if b['balls'] > 0 else "0"

	return {
		'runs': total_runs,
		'wickets': total_wickets,
		'batsmen': batsmen_stats,
		'bowlers': bowlers_stats,
	}


def print_innings_summary(team_name, innings):
	print(f"\n{team_name} innings: {innings['runs']} / {innings['wickets']}")
	print("BATTING:")
	for pid, s in innings['batsmen'].items():
		out = s['howout'] if s['dismissed'] else 'Not Out' if s['balls']>0 else 'DNB'
		print(f"  {s['name']}: {s['runs']} ({s['balls']}) - {out}")
	print("BOWLING:")
	for pid, s in innings['bowlers'].items():
		print(f"  {s['name']}: {s.get('overs','0')} overs, {s['runs']} runs, {s['wickets']} wickets")


def main():
	print(DATA_DIR)
	print("TBONTB Simple Cricket Simulator - Prototype")
	players = load_players_summary()
	if not players:
		print("No players loaded. Please ensure csv/TBONTB_players_summary.csv exists.")
		sys.exit(1)

	user_team = choose_team(players, "User")
	exclude = [p['player_id'] for p in user_team]
	comp_team = pick_computer_team(players, exclude)
	print("\nComputer team selected:")
	for p in comp_team:
		print(f"  {p['player_name']}")

	# choose bat or bowl
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
	time.sleep(5)  # brief pause for realism
	first = simulate_innings(first_batting[1], second_batting[1])
	print_innings_summary(first_batting[0], first)

	print(f"\nSimulating second innings: {second_batting[0]} batting...")
	time.sleep(5)  # brief pause for realism
	second = simulate_innings(second_batting[1], first_batting[1])
	print_innings_summary(second_batting[0], second)

	# decide winner
	if first['runs'] > second['runs']:
		winner = first_batting[0]
		margin = first['runs'] - second['runs']
	elif second['runs'] > first['runs']:
		winner = second_batting[0]
		margin = second['wickets'] - first['wickets']
	else:
		winner = None

	print("\nFinal Result:")
	if winner == first_batting[0]:
		print(f"{winner} won by {margin} runs")
	elif winner == second_batting[0]:
		print(f"{winner} won by {margin} wickets")
	else:
		print("Match tied")


if __name__ == '__main__':
	main()