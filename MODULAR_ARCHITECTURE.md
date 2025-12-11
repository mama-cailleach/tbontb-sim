# TBONTB Cricket Simulator - Modular Architecture

## Overview

The cricket simulator has been refactored into a modular architecture to support future enhancements while maintaining full backward compatibility with the original prototype.

## Module Structure

### Core Modules

#### **main.py**
- Entry point for the simulator
- Orchestrates the match flow
- Handles command-line arguments
- Coordinates all other modules
- Currently configured with default parameters

#### **data_loader.py**
- Loads player data from JSON files
- Manages team file operations
- Provides player lookup utilities
- Handles SHORT_ID_INDEX for player ID resolution

#### **match_config.py**
- Defines match types (T20, TBONTB, ODI, First-Class)
- Configures simulation styles (DEFAULT, MATHEMATICAL, RANDOM, WILD)
- Manages team mindset presets (BALANCED, CONSERVATIVE, AGGRESSIVE, BRUTAL)
- Provides match rules and settings
- **Currently set to DEFAULT for all parameters**

#### **simulation_engine.py**
- Contains core ball-by-ball simulation logic
- Calculates wicket probabilities based on player stats
- Determines run distributions using batting/bowling averages
- Handles special cases (last batsman, target chasing)
- Manages bowler rotation and batsman progression

#### **output_formatter.py**
- Handles different output display modes:
  - `SCORECARD_ONLY`: Final scorecards only
  - `OVER_BY_OVER`: Over summaries (current default)
  - `BALL_BY_BALL`: Detailed commentary (for future)
- Formats innings summaries
- Exports match data to JSON
- Calculates match results

#### **team_selector.py**
- Interactive team selection UI
- Loads saved teams from `json/teams/`
- Provides random team generation
- Handles user input for team choices
- Supports bat/bowl first selection

## Usage

### Basic Usage (Default Settings)
```powershell
python .\main.py
```
This runs the simulator with:
- Match type: TBONTB (100-ball, 5-ball overs, 8 players)
- Simulation style: DEFAULT (balanced, stats-based)
- Output mode: OVER_BY_OVER (shows over summaries)
- Team mindset: BALANCED

### Demo Mode
```powershell
python .\main.py --demo --seed 12345
```
Non-interactive mode with random teams and deterministic results.

### Export Match Data
```powershell
python .\main.py --demo --seed 999 --export-json
```
Exports match boxscore to `json/match_YYYYMMDD_HHMMSS.json`

## Future Expansion Points

The modular structure is designed to easily add:

### 1. Match Type Selection
Modify `main.py` to allow users to choose:
```python
match_config = MatchConfig(match_type='T20')  # or 'ODI', 'FIRST_CLASS'
```

### 2. Simulation Styles
Different levels of randomness vs. stats-driven outcomes:
```python
match_config = MatchConfig(
    match_type='TBONTB',
    simulation_style='MATHEMATICAL'  # More predictable
)
# or 'RANDOM', 'WILD' for more chaos
```

### 3. Team Mindsets
Control batting approach:
```python
match_config = MatchConfig(
    match_type='TBONTB',
    simulation_style='DEFAULT',
    team_mindset='AGGRESSIVE'  # More boundaries, higher risk
)
# or 'CONSERVATIVE', 'BRUTAL'
```

### 4. Output Modes
Change how results are displayed:
```python
output_config = OutputConfig(mode='BALL_BY_BALL')  # Detailed commentary
# or 'SCORECARD_ONLY' for minimal output
```

## File Structure

```
tbontb-sim/
├── main.py                  # Entry point (refactored, modular)
├── main_backup.py           # Original monolithic version (backup)
├── data_loader.py           # Player/team data operations
├── match_config.py          # Match rules and settings
├── simulation_engine.py     # Core simulation logic
├── output_formatter.py      # Result display and export
├── team_selector.py         # Team selection UI
├── team_builder.py          # Team creation tool
├── json/
│   ├── TBONTB_players_summary.json  # Player database
│   └── teams/               # Saved teams
│       ├── Team1.json
│       └── Team2.json
└── testing/
    └── batch_test.py        # Batch simulation tool
```

## Backward Compatibility

All existing functionality is preserved:
- ✅ Team selection from saved files
- ✅ Random team option for computer
- ✅ Over-by-over summaries
- ✅ JSON export with `--export-json`
- ✅ Demo mode with `--demo --seed`
- ✅ Identical simulation results (same seed produces same output)

## Development Workflow

### Adding a New Feature

1. **Match type**: Edit `match_config.py` → Add to `MATCH_TYPES`
2. **Simulation style**: Edit `match_config.py` → Add to `SIMULATION_STYLES`
3. **Output format**: Edit `output_formatter.py` → Add to `OUTPUT_MODES`
4. **UI flow**: Edit `main.py` → Add user prompts for new options

### Testing Changes

```powershell
# Test with deterministic seed
python .\main.py --demo --seed 12345

# Compare with backup version
python .\main_backup.py --demo --seed 12345
```

## Notes for AI Agents

- All modules use **default parameters** currently - features are defined but not yet selectable
- `match_config.py` contains presets for future T20, ODI, First-Class formats
- `simulation_engine.py` has hooks for team mindset multipliers (not yet active)
- `output_formatter.py` has placeholder for ball-by-ball commentary
- The structure is ready for parameter selection UI - just add prompts in `main.py`

## Migration from Old main.py

The original `main.py` has been backed up to `main_backup.py`. The new modular version:
- Maintains identical behavior with default settings
- Imports functions from specialized modules
- Reduces main.py from ~816 lines to ~170 lines
- Makes future features easier to add and test independently
