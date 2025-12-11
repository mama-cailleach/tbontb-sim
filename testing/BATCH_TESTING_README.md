# Batch Testing and Model Tuning Guide

## Quick Start

```powershell
cd testing
```

### Run Batch Test (50 simulations)
```powershell
python .\batch_test.py Test_Team_Alpha.json Team_Beta_Squad.json -n 50 --seed 123
```

### Export Results to CSV
```powershell
python .\batch_test.py Test_Team_Alpha.json Team_Beta_Squad.json -n 50 --seed 123 --csv
```

### View Tuning Recommendations
```powershell
python .\TUNING_GUIDE.py
```

## What the Batch Test Shows

The batch test runs multiple simulations and compares:
- **Simulated batting averages** vs Historical batting averages
- **Simulated strike rates** vs Historical strike rates  
- **Simulated bowling averages** vs Historical bowling averages
- **Simulated economies** vs Historical economies

## Understanding the Output

### Batting Performance Table
- **Sim Avg**: Average runs per dismissal in simulations
- **Sim SR**: Strike rate (runs per 100 balls) in simulations
- **Hist Avg/SR**: Player's actual historical performance
- **Diff columns**: How far off the simulation is (negative = underperforming)

### Bowling Performance Table
- **Sim Avg**: Bowling average (runs per wicket) in simulations
- **Sim Econ**: Economy rate (runs per over) in simulations
- **Hist Avg/Econ**: Player's actual historical performance
- **Diff columns**: How far off the simulation is (negative = better than history)

## Current Model Performance (Before Tuning)

Based on 50 simulations with seed 123:

### Issues Found:
1. **Strike Rates 40-70% TOO LOW** (averaging ~60 instead of ~100-120)
2. **Batting Averages 50-80% TOO LOW** (averaging ~5-10 instead of ~20-30)
3. **Bowling Economy 60-70% TOO LOW** (averaging ~3 instead of ~9-12)
4. **Bowling Averages 80-90% TOO LOW** (averaging ~6-8 instead of ~40-60)

### Root Causes:
- Wicket probability is too high
- Boundary probability is too low
- Dot ball rate is too high
- Not enough differentiation for good batsmen

## Recommended Workflow

1. **Establish Baseline**: Run batch test with current model
2. **Apply Tuning**: Make adjustments suggested in TUNING_GUIDE.py
3. **Re-test**: Run batch test again with SAME seed to compare
4. **Iterate**: Fine-tune parameters until simulated stats match historical within 10-20%
5. **Validate**: Test with different team matchups

## CSV Export

When you use `--csv`, the results are exported to `json/batch_test_[teams]_[num]sims.csv` with columns for easy analysis in Excel/spreadsheet tools.

## Additional Options

```powershell
# Run more simulations for better statistical accuracy
python .\batch_test.py Team1.json Team2.json -n 100

# Use different random seed
python .\batch_test.py Team1.json Team2.json --seed 456

# Run fewer simulations for quick checks
python .\batch_test.py Team1.json Team2.json -n 10
```

## What Good Results Look Like

After tuning, you should see:
- **Batting Averages**: Within ±20% of historical
- **Strike Rates**: Within ±15% of historical
- **Bowling Economy**: Within ±20% of historical
- **Bowling Averages**: Within ±25% of historical

Some variance is expected due to:
- Sample size (50-100 innings vs thousands in real career)
- Match situation differences
- Opponent quality variations
