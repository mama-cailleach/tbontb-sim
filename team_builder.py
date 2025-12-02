import json
import os
import re
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "json")
PLAYERS_JSON = os.path.join(DATA_DIR, "TBONTB_players_summary.json")


def parse_float(s, default=None):
    if s is None or s == "":
        return default
    try:
        return float(str(s).replace("*", ""))
    except Exception:
        return default


def load_players():
    """Load player summaries from json and normalize to internal dict shape."""
    if not os.path.exists(PLAYERS_JSON):
        print(f"Players JSON not found at {PLAYERS_JSON}")
        return {}
    with open(PLAYERS_JSON, encoding="utf-8") as f:
        rows = json.load(f)

    players = {}
    for r in rows:
        raw_id = r.get("player_id")
        if raw_id is None:
            continue
        try:
            if isinstance(raw_id, int):
                pid = f"TBONTB_{int(raw_id):04d}"
                short_int = int(raw_id)
            else:
                pid = str(raw_id)
                m = re.search(r"(\d+)$", pid)
                short_int = int(m.group(1)) if m else None
        except Exception:
            pid = str(raw_id)
            short_int = None

        players[pid] = {
            "player_id": pid,
            "player_name": r.get("player_name") or r.get("name") or "",
            "short_int": short_int,
            "runs": int(parse_float(r.get("runs"), 0) or 0),
            # key stats used by simulator
            "strike_rate": parse_float(r.get("strike_rate"), None),
            "bat_avg": parse_float(r.get("bat_avg"), None),
            "fours": int(parse_float(r.get("4s", r.get("fours")), 0) or 0),
            "sixes": int(parse_float(r.get("6s", r.get("sixes")), 0) or 0),
            "overs_bowled": parse_float(r.get("overs_bowled"), 0) or 0,
            "runs_conceded": parse_float(r.get("runs_conceded"), 0) or 0,
            "wickets": int(parse_float(r.get("wickets"), 0) or 0),
            "economy": parse_float(r.get("economy"), None),
            "bowl_avg": parse_float(r.get("bowl_avg"), None),
            # keep raw row for completeness
            "__raw": r,
        }

    return players


def print_player_brief(p):
    # show key fields in one line
    sid = p.get("short_int")
    id_label = str(sid) if sid is not None else p.get("player_id")
    runs = p.get("runs")
    sr = p.get("strike_rate")
    ba = p.get("bat_avg")
    f = p.get("fours")
    s = p.get("sixes")
    wk = p.get("wickets")
    econ = p.get("economy")
    bavg = p.get("bowl_avg")
    print(f"{id_label:4} | {p['player_name'][:30]:30} | R:{runs:5} | SR:{sr or '-':6} | AVG:{ba or '-':6} | 4s:{f:3} | 6s:{s:3} | WK:{wk:3} | ECO:{econ or '-':6} | BAVG:{bavg or '-'}")


def show_players_paginated(players, per_page=20):
    keys = sorted(players.keys(), key=lambda k: (players[k]['short_int'] is None, players[k]['short_int'] or k))
    total = len(keys)
    page = 0
    while True:
        start = page * per_page
        if start >= total:
            print("End of list.")
            break
        end = min(total, start + per_page)
        print(f"\nPlayers {start+1}-{end} of {total} (showing: id | name | RUNS | SR | AVG | 4s | 6s | WK | ECO | BOWL AVG):")
        for k in keys[start:end]:
            print_player_brief(players[k])
        if end == total:
            break
        ans = input("Show next page? (Y/n): ").strip().lower()
        if ans in ('n', 'no'):
            break
        page += 1


def choose_team(players):
    print("\nYou will pick 8 players for your team.")
    print("You can either: \n - type 'list' to browse players, \n - or enter player numbers separated by commas (e.g. 1,5,12,34,...)")
    selected = []
    pid_index = {str(p['short_int']): pid for pid, p in players.items() if p.get('short_int') is not None}
    while True:
        s = input("Enter 8 player IDs or 'list': ").strip()
        if not s:
            continue
        if s.lower() == 'list':
            show_players_paginated(players)
            continue
        entries = [x.strip() for x in s.split(',') if x.strip()]
        picks = []
        bad = []
        for e in entries:
            # accept full pid or numeric short id
            if e in players:
                picks.append(e)
                continue
            if e in pid_index:
                picks.append(pid_index[e])
                continue
            # maybe numeric with leading zeros
            try:
                ne = str(int(e))
                if ne in pid_index:
                    picks.append(pid_index[ne])
                    continue
            except Exception:
                pass
            bad.append(e)
        if bad:
            print("These IDs were not found:", ",".join(bad))
            continue
        if len(picks) != 8:
            print(f"You picked {len(picks)} players; please pick exactly 8.")
            continue
        # verify uniqueness
        if len(set(picks)) != 8:
            print("Duplicate picks detected; please pick 8 distinct players.")
            continue
        selected = [players[pid] for pid in picks]
        print("\nTeam selected:")
        for idx, p in enumerate(selected, start=1):
            print(f" {idx}. {p['short_int'] or p['player_id']} - {p['player_name']}")
        confirm = input("Accept this team? (Y/n): ").strip().lower()
        if confirm in ('', 'y', 'yes'):
            return selected


def choose_captain_and_keeper(team):
    print("\nSelect a captain (enter 1-8)")
    for i, p in enumerate(team, start=1):
        print(f" {i}. {p['short_int'] or p['player_id']} - {p['player_name']}")
    while True:
        c = input("Captain number: ").strip()
        try:
            ci = int(c)
            if 1 <= ci <= len(team):
                captain = team[ci-1]
                break
        except Exception:
            pass
        print("Please enter a number between 1 and 8.")

    print("\nSelect wicketkeeper (enter 1-8)")
    while True:
        k = input("Wicketkeeper number: ").strip()
        try:
            ki = int(k)
            if 1 <= ki <= len(team):
                keeper = team[ki-1]
                break
        except Exception:
            pass
        print("Please enter a number between 1 and 8.")

    return captain, keeper


def reorder_batting(team):
    print("\nCurrent batting order:")
    for i, p in enumerate(team, start=1):
        print(f" {i}. {p['short_int'] or p['player_id']} - {p['player_name']}")
    ans = input("Would you like to reorder the batting lineup? (y/N): ").strip().lower()
    if ans not in ('y', 'yes'):
        return team
    print("Enter a new order as the current positions separated by commas, e.g. '3,1,2,5,4,6,7,8'")
    while True:
        s = input("New order: ").strip()
        parts = [x.strip() for x in s.split(',') if x.strip()]
        try:
            nums = [int(x) for x in parts]
            if len(nums) != len(team) or set(nums) != set(range(1, len(team)+1)):
                raise ValueError()
            new = [team[n-1] for n in nums]
            print("New batting order:")
            for i, p in enumerate(new, start=1):
                print(f" {i}. {p['short_int'] or p['player_id']} - {p['player_name']}")
            ok = input("Accept new order? (Y/n): ").strip().lower()
            if ok in ('', 'y', 'yes'):
                return new
        except Exception:
            pass
        print("Invalid input. Please provide a permutation of 1..8 separated by commas.")


def save_team(team, captain, keeper, path=None):
    obj = {
        "team": [
            {
                "player_id": p['player_id'],
                "player_name": p['player_name'],
                "short_int": p.get('short_int'),
                "strike_rate": p.get('strike_rate'),
                "bat_avg": p.get('bat_avg'),
            } for p in team
        ],
        "captain": captain['player_id'],
        "wicketkeeper": keeper['player_id'],
    }
    if path is None:
        path = os.path.join(DATA_DIR, 'user_team.json')
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"Team saved to {path}")
    except Exception as e:
        print(f"Failed to save team: {e}")


def main():
    players = load_players()
    if not players:
        print("No players loaded. Ensure TBONTB_players_summary.json is present in json/ folder.")
        sys.exit(1)

    print("Welcome to the TBONTB Team Builder prototype.")
    print("You will pick 8 players by their numeric ID shown in the list.")
    team = choose_team(players)
    captain, keeper = choose_captain_and_keeper(team)
    team = reorder_batting(team)

    print("\nFinal team:")
    for i, p in enumerate(team, start=1):
        role = []
        if p['player_id'] == captain['player_id']:
            role.append('C')
        if p['player_id'] == keeper['player_id']:
            role.append('WK')
        role_str = ' '.join(role)
        print(f" {i}. {p.get('short_int') or p['player_id']} - {p['player_name']} {role_str}")

    ans = input("Save this team to json/user_team.json? (Y/n): ").strip().lower()
    if ans in ('', 'y', 'yes'):
        save_team(team, captain, keeper)


if __name__ == '__main__':
    main()
