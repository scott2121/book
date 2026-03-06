"""
Iran Strike on Israel マーケットの価格推移をプロットする。
特に2/28周辺のベッティング推移を可視化。
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "polymarket")

FILES = {
    "by Jan 15": "iran_strike_Jan15_yes.csv",
    "by Jan 31": "iran_strike_Jan31_yes.csv",
    "by Feb 28": "iran_strike_Feb28_yes.csv",
    "by Mar 31": "iran_strike_Mar31_yes.csv",
    "by Dec 31": "iran_strike_Dec31_yes.csv",
}


def load_data():
    dfs = {}
    for label, fname in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["timestamp_iso"])
            df = df.rename(columns={"timestamp_iso": "datetime", "price": "price"})
            dfs[label] = df
    return dfs


def plot_all(dfs):
    """全マーケットの推移を1枚のグラフに。"""
    fig, ax = plt.subplots(figsize=(14, 7))

    for label, df in dfs.items():
        ax.plot(df["datetime"], df["price"], label=label, alpha=0.85, linewidth=1.2)

    ax.set_title("Polymarket: Iran Strike on Israel — Yes Price (Implied Probability)", fontsize=14)
    ax.set_ylabel("Yes Price (0–1)")
    ax.set_xlabel("Date (UTC)")
    ax.legend(loc="upper left")
    ax.set_ylim(-0.05, 1.05)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)
    ax.grid(True, alpha=0.3)

    # 2/28をハイライト
    ax.axvline(pd.Timestamp("2026-02-28"), color="red", linestyle="--", alpha=0.6, label="Feb 28")

    plt.tight_layout()
    outpath = os.path.join(DATA_DIR, "iran_strike_all_markets.png")
    plt.savefig(outpath, dpi=150)
    print(f"Saved: {outpath}")
    plt.close()


def plot_feb28_zoom(dfs):
    """2/28マーケットの2/20〜3/1をズームイン。"""
    if "by Feb 28" not in dfs:
        return

    df = dfs["by Feb 28"]
    mask = (df["datetime"] >= "2026-02-20") & (df["datetime"] <= "2026-03-01")
    df_zoom = df[mask]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df_zoom["datetime"], df_zoom["price"], color="tab:red", linewidth=1.5, label="by Feb 28 (Yes)")

    # Mar31もあれば重ねる
    if "by Mar 31" in dfs:
        df2 = dfs["by Mar 31"]
        mask2 = (df2["datetime"] >= "2026-02-20") & (df2["datetime"] <= "2026-03-01")
        ax.plot(df2[mask2]["datetime"], df2[mask2]["price"], color="tab:blue",
                linewidth=1.5, alpha=0.8, label="by Mar 31 (Yes)")

    ax.set_title("Iran Strike — Feb 28 Market Zoom (2/20–3/1)", fontsize=14)
    ax.set_ylabel("Yes Price (Implied Probability)")
    ax.set_xlabel("Date (UTC)")
    ax.legend()
    ax.set_ylim(-0.05, 1.05)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=45)
    ax.grid(True, alpha=0.3)
    ax.axvline(pd.Timestamp("2026-02-28"), color="red", linestyle="--", alpha=0.5)

    plt.tight_layout()
    outpath = os.path.join(DATA_DIR, "iran_strike_feb28_zoom.png")
    plt.savefig(outpath, dpi=150)
    print(f"Saved: {outpath}")
    plt.close()


def print_feb28_summary(dfs):
    """2/28マーケットの主要な価格変動をサマリー出力。"""
    if "by Feb 28" not in dfs:
        return

    df = dfs["by Feb 28"]
    print("\n=== Feb 28 Market — Key Price Points ===")

    for date_str in ["2026-02-20", "2026-02-24", "2026-02-25", "2026-02-26",
                     "2026-02-27", "2026-02-28"]:
        mask = df["datetime"].dt.strftime("%Y-%m-%d") == date_str
        day_data = df[mask]
        if not day_data.empty:
            print(f"  {date_str}: open={day_data.iloc[0]['price']:.3f}, "
                  f"high={day_data['price'].max():.3f}, "
                  f"low={day_data['price'].min():.3f}, "
                  f"close={day_data.iloc[-1]['price']:.3f}")


def main():
    dfs = load_data()
    print(f"Loaded {len(dfs)} markets")

    plot_all(dfs)
    plot_feb28_zoom(dfs)
    print_feb28_summary(dfs)


if __name__ == "__main__":
    main()
