#!/usr/bin/env python3
"""
Build a TOPIX constituent transition chart from listed_info.pkl.

Usage:
  python3 scripts/plot_topix_transition.py \
    --input /path/to/listed_info.pkl \
    --output data/topix/topix_transition.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


TOPIX_BUCKETS = [
    "TOPIX Core30",
    "TOPIX Large70",
    "TOPIX Mid400",
    "TOPIX Small 1",
    "TOPIX Small 2",
]


def build_monthly_counts(input_path: Path) -> pd.DataFrame:
    df = pd.read_pickle(input_path)
    if "ScaleCategory" not in df.columns:
        raise ValueError("ScaleCategory column not found in input data.")

    scale = df["ScaleCategory"].astype(str)
    topix_df = df[scale.str.startswith("TOPIX")].reset_index()[["Date", "ScaleCategory"]]

    counts = topix_df.pivot_table(index="Date", columns="ScaleCategory", aggfunc="size", fill_value=0)
    for col in TOPIX_BUCKETS:
        if col not in counts.columns:
            counts[col] = 0
    counts = counts[TOPIX_BUCKETS].sort_index()

    monthly = counts.groupby(counts.index.to_period("M")).first()
    monthly.index = monthly.index.to_timestamp()
    monthly["Total"] = monthly.sum(axis=1)
    return monthly


def draw_chart(monthly: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 5.8))

    colors = ["#2e86c1", "#5dade2", "#76d7c4", "#f5b041", "#ec7063"]
    ax.stackplot(
        monthly.index,
        [monthly[c] for c in TOPIX_BUCKETS],
        labels=TOPIX_BUCKETS,
        colors=colors,
        alpha=0.95,
    )
    ax.axvspan(pd.Timestamp("2022-04-01"), pd.Timestamp("2025-01-31"), color="#f2d7d5", alpha=0.25)
    ax.axvspan(pd.Timestamp("2025-02-01"), monthly.index.max(), color="#fcf3cf", alpha=0.25)
    ax.set_title("TOPIX Constituent Transition (Stacked)", fontsize=13, pad=10)
    ax.set_ylabel("Constituent Count")
    ax.set_xlabel("Date")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", ncol=3, fontsize=9, frameon=False)
    ax.set_xlim(monthly.index.min(), monthly.index.max())

    fig.text(
        0.01,
        0.01,
        "Note: Source data starts from 2014-01; monthly first-observation snapshot is used.",
        fontsize=9,
        color="#444444",
    )

    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot TOPIX constituent transition.")
    parser.add_argument("--input", required=True, type=Path, help="Path to listed_info.pkl")
    parser.add_argument("--output", required=True, type=Path, help="Output png path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    monthly = build_monthly_counts(args.input)
    draw_chart(monthly, args.output)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
