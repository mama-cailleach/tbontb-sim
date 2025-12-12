import json

with open('json/teams/Test_Team_Alpha.json') as f:
    team = json.load(f)
with open('json/TBONTB_players_summary.json') as f:
    players = json.load(f)
lookup = {p['player_id']: p for p in players}

print('Team Alpha Players:')
print(f"{'Name':<25} {'Avg':<8} {'SR%':<8} {'Balls Faced':<12} {'Runs':<8} {'Overs':<8} {'Econ':<8}")
print('-' * 100)

batting_stats = []
bowling_stats = []

for p in team['team']:
    full = lookup.get(p['player_id'], {})
    batting_stats.append({
        'name': p['player_name'],
        'avg': p.get('bat_avg', 0),
        'sr': p.get('strike_rate', 0),
        'balls': full.get('balls_faced', 0),
        'runs': full.get('runs', 0)
    })
    bowling_stats.append({
        'name': p['player_name'],
        'econ': full.get('economy', 0),
        'overs': full.get('overs_bowled', 0),
        'runs_conc': full.get('runs_conceded', 0)
    })

for b in batting_stats:
    print(f"{b['name']:<25} {b['avg']:<8.1f} {b['sr']:<8.1f} {b['balls']:<12} {b['runs']:<8}")

print()
print('Bowling:')
print(f"{'Name':<25} {'Econ':<8} {'Overs':<8} {'Runs Conc':<12}")
for b in bowling_stats:
    print(f"{b['name']:<25} {b['econ']:<8.2f} {b['overs']:<8.1f} {b['runs_conc']:<12}")

# Calculate aggregate
total_runs = sum(b['runs'] for b in batting_stats)
total_balls = sum(b['balls'] for b in batting_stats)
avg_sr = sum(b['sr'] for b in batting_stats) / len(batting_stats)
avg_avg = sum(b['avg'] for b in batting_stats) / len(batting_stats)
total_econ = sum(b['econ'] for b in bowling_stats) / len(bowling_stats)

print()
print(f'AGGREGATE: Team avg {avg_avg:.1f}, Team SR {avg_sr:.1f}%, Total runs {total_runs}, Total balls {total_balls}')
print(f'Overall team economy: {total_econ:.2f}')

# Per-inning projection based on historical
print()
print("IF they played a 100-ball innings with proportional contribution:")
# Assume 8 batters, each faces ~12-13 balls on average
balls_per_batter = 12.5
print(f"  Avg balls/batter: {balls_per_batter:.1f}")
for b in batting_stats:
    if b['avg'] > 0:
        exp_runs = b['avg'] / 100 * balls_per_batter * (b['sr'] / 100.0)
        exp_runs_simple = (b['runs'] / b['balls']) * balls_per_batter if b['balls'] > 0 else 0
        print(f"    {b['name']:<25}: ~{exp_runs_simple:.1f} runs (based on {b['runs']}/{b['balls']})")

total_proj_runs = sum((b['runs'] / b['balls']) * balls_per_batter if b['balls'] > 0 else 0 for b in batting_stats)
print(f"  Team total projected: ~{total_proj_runs:.0f} runs per 100-ball innings")
