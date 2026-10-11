---
name: continuum-strain-index
description: Turn your WHOOP (or Oura/Apple Health) daily export into a personal strain index that flags when your body is drifting from your own normal, often days before you feel sick.
---
# Continuum strain index

You are helping someone check whether their body is drifting from its own normal, using their wearable's daily export.

## Input
A CSV of daily data (WHOOP: Physiological Cycles + Sleeps export). Find these columns, or the closest match:
- sleep hours (asleep duration)
- resting heart rate (bpm)
- HRV (ms)
- sleep debt (minutes or hours)
- respiratory / breathing rate (breaths per min)

## Method
1. Smooth each feature: 7-day rolling mean for sleep hours and sleep debt; 3-day rolling mean for resting HR, HRV, and breathing rate.
2. For each day, compare to that person's previous 28 days (not including today): z = (today - mean_28d) / std_28d.
3. Flip signs so "worse" is always positive: less sleep, higher RHR, lower HRV, more sleep debt, higher breathing rate.
4. Weighted sum: 0.35 sleep + 0.25 RHR + 0.20 HRV + 0.15 sleep debt + 0.05 breathing.
5. Scale so 50 is a normal day: index = 50 + 10 x weighted sum.
6. Skip any day with missing data or fewer than 28 days of baseline.

## Output
- A bar chart of the daily index over time with a dashed line at 50.
- The last 14 days in a short table.
- Plain-language read: is the index trending up for several days in a row? Which feature is driving it?

## Be honest
This is a personal signal, not a diagnosis. One person's retrospective pattern is not proof of prediction. If the user feels unwell, tell them to talk to a doctor.

Built by @Angela_Busheska at Continuum.
