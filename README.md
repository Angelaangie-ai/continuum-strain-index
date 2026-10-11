# Continuum strain index

One number from your wearable that tells you when your body is drifting from your own normal, often days before you feel sick.

Most wearables tell you you're sick on the day you're already sick. This index looks at five signals (sleep, resting heart rate, HRV, sleep debt, breathing rate), compares each one to your own last 28 days, and rolls them into a single daily score. 50 is a normal day for you. A score that climbs for several days in a row is worth paying attention to.

In the first worked example, the score climbed from 39 to 55 over the 9 days before a cold, while resting heart rate went 62 → 74 bpm and HRV went 62 → 43 ms, and the person felt completely fine.

## Two ways to use it

### 1. With an AI agent (no code)

Give `SKILL.md` to Claude, ChatGPT or any agent that can run code, attach your WHOOP export, and ask it to run the skill. It will compute the index, chart it, and give you a plain-language read.

### 2. With the script

```bash
pip install pandas matplotlib
python strain_index.py physiological_cycles.csv
```

This prints your last 14 days, saves a chart to `strain_index.png`, and tells you whether the index is trending up. Add `--csv-out scores.csv` to save every day's score and which signal drove it.

## Getting your data

**WHOOP:** app → profile → settings → data export. Use the `physiological_cycles.csv` file.

**Oura or Apple Health:** export to CSV and rename the columns to match the names in `COLUMN_ALIASES` at the top of `strain_index.py`. Any daily CSV with sleep hours, resting HR, HRV, sleep debt and breathing rate will work.

## How it's calculated

1. **Smooth** each signal so one odd night doesn't swing the score: 7-day rolling mean for sleep hours and sleep debt, 3-day rolling mean for resting HR, HRV and breathing rate.
2. **Compare to yourself.** For each day, compute a z-score against your own previous 28 days (not including today): `z = (today − mean of last 28 days) / standard deviation`. A z of 1 means "one standard deviation more unusual than normal for you."
3. **Point everything the same way.** Flip signs so that "worse" is always positive: less sleep, higher resting HR, lower HRV, more sleep debt, higher breathing rate.
4. **Weight and sum.** `0.35 × sleep + 0.25 × resting HR + 0.20 × HRV + 0.15 × sleep debt + 0.05 × breathing rate`
5. **Scale.** `index = 50 + 10 × weighted sum`. So 60 means your signals are, on average, one standard deviation worse than your own normal.

Days with missing data, or without 28 days of history behind them, get no score.

### Why one number instead of five charts

Each signal can move for innocent reasons: a hard workout raises resting HR, a late night drops HRV. When the signals disagree they partly cancel and the score stays near 50. When they all drift the same way, as they do when your immune system is ramping up, they stack and the score climbs. One number is quieter than any single input on a normal day and louder on a sick day, and it gives you one line to watch instead of five.

## Be honest about what this is

This is a personal signal, not a diagnosis. The worked example is one person and one illness, looked at after the fact. Overtraining, a few bad nights, travel or heavy drinking can produce a similar picture. The next step is to lock the formula in advance, run it live across many people, and log illness separately. If you want to be part of that, reply to the post or open an issue.

If you feel unwell, talk to a doctor.
