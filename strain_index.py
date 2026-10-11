#!/usr/bin/env python3
"""Continuum strain index.

Turns a WHOOP daily export (or any CSV with the same five signals) into a
single daily score that measures how far your body is drifting from your
own normal. 50 is an ordinary day. Higher means more strain than usual
for you, which often shows up days before you feel sick.

Usage:
    python strain_index.py physiological_cycles.csv
    python strain_index.py physiological_cycles.csv --out strain_index.png

Method (see SKILL.md):
    1. Smooth each signal (7-day mean for sleep and sleep debt,
       3-day mean for resting HR, HRV and breathing rate).
    2. Compare each day to your own previous 28 days as a z-score.
    3. Flip signs so "worse" is always positive.
    4. Weighted sum: 0.35 sleep, 0.25 RHR, 0.20 HRV, 0.15 sleep debt,
       0.05 breathing rate.
    5. index = 50 + 10 * weighted sum.
"""

import argparse
import sys

import pandas as pd

WEIGHTS = {
    "sleep_hours": 0.35,
    "resting_hr": 0.25,
    "hrv": 0.20,
    "sleep_debt": 0.15,
    "resp_rate": 0.05,
}

# +1 means a higher value is worse, -1 means a lower value is worse.
SIGN = {
    "sleep_hours": -1,
    "resting_hr": +1,
    "hrv": -1,
    "sleep_debt": +1,
    "resp_rate": +1,
}

SMOOTH_DAYS = {
    "sleep_hours": 7,
    "resting_hr": 3,
    "hrv": 3,
    "sleep_debt": 7,
    "resp_rate": 3,
}

BASELINE_DAYS = 28
# Real exports have gaps (nights without the strap, charging). Windows are
# measured in calendar days, and a day gets a score as long as at least
# this many of the previous 28 days have data.
MIN_BASELINE_OBS = 14

# Column names WHOOP uses in its "Physiological Cycles" export, plus a few
# common alternatives. Matching is case-insensitive and ignores punctuation.
COLUMN_ALIASES = {
    "date": ["cycle start time", "date", "day", "cycle start", "timestamp"],
    "sleep_hours": [
        "asleep duration (min)",
        "asleep duration",
        "sleep hours",
        "total sleep",
        "sleep duration",
    ],
    "resting_hr": ["resting heart rate (bpm)", "resting heart rate", "rhr", "resting hr"],
    "hrv": ["heart rate variability (ms)", "hrv", "heart rate variability"],
    "sleep_debt": ["sleep debt (min)", "sleep debt", "sleep need deficit"],
    "resp_rate": [
        "respiratory rate (rpm)",
        "respiratory rate",
        "breathing rate",
        "respiration rate",
    ],
}


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def find_columns(df: pd.DataFrame) -> dict:
    """Map our canonical names to whatever columns the CSV actually has."""
    normalized = {_norm(c): c for c in df.columns}
    found = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _norm(alias) in normalized:
                found[key] = normalized[_norm(alias)]
                break
    missing = [k for k in COLUMN_ALIASES if k not in found]
    if missing:
        sys.exit(
            f"Could not find columns for: {', '.join(missing)}.\n"
            f"Columns in your file: {list(df.columns)}\n"
            "Rename the matching columns or add an alias in COLUMN_ALIASES."
        )
    return found


def load(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    cols = find_columns(raw)
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(raw[cols["date"]], errors="coerce").dt.normalize(),
            "sleep_hours": pd.to_numeric(raw[cols["sleep_hours"]], errors="coerce"),
            "resting_hr": pd.to_numeric(raw[cols["resting_hr"]], errors="coerce"),
            "hrv": pd.to_numeric(raw[cols["hrv"]], errors="coerce"),
            "sleep_debt": pd.to_numeric(raw[cols["sleep_debt"]], errors="coerce"),
            "resp_rate": pd.to_numeric(raw[cols["resp_rate"]], errors="coerce"),
        }
    )
    # WHOOP exports sleep in minutes; convert anything that looks like minutes.
    if df["sleep_hours"].median() > 24:
        df["sleep_hours"] = df["sleep_hours"] / 60.0
    if df["sleep_debt"].median() > 24:
        df["sleep_debt"] = df["sleep_debt"] / 60.0
    df = df.dropna(subset=["date"]).sort_values("date")
    # One row per day: if WHOOP logged two cycles on a day, keep the mean.
    df = df.groupby("date", as_index=False).mean(numeric_only=True)
    return df.set_index("date").asfreq("D")


def compute(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for key, w in WEIGHTS.items():
        # Calendar-day windows so gaps in the export don't break the math.
        smoothed = df[key].rolling(f"{SMOOTH_DAYS[key]}D", min_periods=1).mean()
        # Baseline is the previous 28 days, not including today (hence shift).
        base = smoothed.shift(1, freq="D").rolling(
            f"{BASELINE_DAYS}D", min_periods=MIN_BASELINE_OBS
        )
        mean, std = base.mean().reindex(df.index), base.std().reindex(df.index)
        z = (smoothed - mean) / std
        # No raw reading today means no score today.
        z[df[key].isna()] = float("nan")
        out[f"z_{key}"] = SIGN[key] * z
        out[f"c_{key}"] = w * out[f"z_{key}"]
    contrib = out[[f"c_{k}" for k in WEIGHTS]]
    out["index"] = 50 + 10 * contrib.sum(axis=1, min_count=len(WEIGHTS))
    has_score = out["index"].notna()
    out["driver"] = None
    out.loc[has_score, "driver"] = (
        contrib[has_score].idxmax(axis=1).str.replace("c_", "", regex=False)
    )
    return out


def plot(result: pd.DataFrame, path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = result["index"].dropna()
    if s.empty:
        print("Not enough data to plot (need at least 28 days of baseline).")
        return
    fig, ax = plt.subplots(figsize=(11, 4))
    colors = ["#c0392b" if v > 50 else "#7f8c8d" for v in s]
    ax.bar(s.index, s.values - 50, bottom=50, color=colors, width=0.8)
    ax.axhline(50, color="black", linestyle="--", linewidth=1)
    ax.set_ylabel("strain index (50 = normal day)")
    ax.set_title("Continuum strain index")
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    print(f"Chart saved to {path}")


def read_out(result: pd.DataFrame) -> None:
    s = result["index"].dropna()
    if s.empty:
        print("Not enough data yet. The index needs 28 days of history before the first score.")
        return
    last = result.dropna(subset=["index"]).tail(14)
    print("\nLast 14 days:")
    print(
        last[["index", "driver"]]
        .assign(index=lambda d: d["index"].round(1))
        .to_string()
    )
    recent = s.tail(5)
    rising = (recent.diff().dropna() > 0).all() and len(recent) == 5
    above = (recent > 55).sum()
    print()
    if rising:
        print("The index has climbed five days in a row. Worth paying attention to.")
    elif above >= 3:
        print("The index has been above 55 on most of the last five days.")
    else:
        print("No sustained drift in the last five days.")
    drivers = last["driver"].value_counts()
    if not drivers.empty:
        print(f"Most common driver over the last 14 days: {drivers.index[0]}")
    print(
        "\nThis is a personal signal, not a diagnosis. If you feel unwell, talk to a doctor."
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", help="WHOOP Physiological Cycles export (or similar CSV)")
    p.add_argument("--out", default="strain_index.png", help="where to save the chart")
    p.add_argument("--csv-out", default=None, help="optionally save the daily scores as CSV")
    args = p.parse_args()

    df = load(args.csv)
    result = compute(df)
    if args.csv_out:
        result.to_csv(args.csv_out)
        print(f"Scores saved to {args.csv_out}")
    plot(result, args.out)
    read_out(result)


if __name__ == "__main__":
    main()
