"""
Match score list script.
Runs multiple simulations between two teams and prints a one-line
score summary for each match:

Example:
Team 1 100/6(20.0 overs) - 101/5(16.1 overs) Team 2

Usage:
  python testing/match_score_list.py TEAM1.json TEAM2.json -n 10 --seed 123

TEAM files are relative to json/teams/ unless an absolute/relative path is provided.
"""

import os
import sys
import argparse
import random

# Add parent directory to path for imports
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

from data_loader import load_players_summary, load_team_from_file
from match_config import MatchConfig
from simulation_engine import simulate_innings


def resolve_team_path(team_arg: str) -> str:
    """Resolve a team file path to json/teams/ if only a filename is provided."""
    if os.path.isabs(team_arg) or os.path.exists(team_arg):
        return team_arg
    base = os.path.join(os.path.dirname(__file__), '..', 'json', 'teams')
    return os.path.join(base, team_arg)


def run_scores(team1_file: str, team2_file: str, num_simulations: int = 10, seed: int | None = None, players_path: str | None = None):
    if seed is not None:
        random.seed(seed)

    # Load players summary
    players = load_players_summary(players_path)
    if not players:
        print("Failed to load players summary.")
        return

    # Load team files
    team1_path = resolve_team_path(team1_file)
    team2_path = resolve_team_path(team2_file)

    team1, team1_name, team1_captain, team1_keeper = load_team_from_file(os.path.basename(team1_path), players)
    team2, team2_name, team2_captain, team2_keeper = load_team_from_file(os.path.basename(team2_path), players)

    if not team1 or not team2:
        print("Failed to load teams.")
        return

    match_config = MatchConfig.default()

    lines = []
    for i in range(1, num_simulations + 1):
        # Team1 bats first, Team2 chases
        first = simulate_innings(
            team1,
            team2,
            match_config,
            target=None,
            output_config=None,
            keeper_id=team2_keeper
        )

        target_score = first['runs'] + 1
        second = simulate_innings(
            team2,
            team1,
            match_config,
            target=target_score,
            output_config=None,
            keeper_id=team1_keeper
        )

        overs1 = match_config.get_overs_from_balls(first.get('balls', 0))
        overs2 = match_config.get_overs_from_balls(second.get('balls', 0))

        line = f"{team1_name} {first['runs']}/{first['wickets']}({overs1} overs) - {second['runs']}/{second['wickets']}({overs2} overs) {team2_name}"
        lines.append(line)
        print(line)

    return lines


def main():
    parser = argparse.ArgumentParser(description='Run multiple simulations and print score list lines')
    parser.add_argument('team1', help='Filename of first team in json/teams/ (e.g., ENG_test.json)')
    parser.add_argument('team2', help='Filename of second team in json/teams/ (e.g., TBO_VIII.json)')
    parser.add_argument('-n', '--num-sims', type=int, default=10, help='Number of simulations to run (default: 10)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--players-file', type=str, help='Path to alternate players summary JSON')

    args = parser.parse_args()
    run_scores(args.team1, args.team2, args.num_sims, args.seed, args.players_file)


if __name__ == '__main__':
    main()
