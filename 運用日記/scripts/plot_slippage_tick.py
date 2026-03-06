"""
寄り付き前後のtickデータを可視化し、実約定位置とスリッページを示す。

改善点:
- tick推移を折れ線で描画し価格の流れを見やすく
- 出来高を下部のバーで表示
- Y軸範囲をtickレンジ全体に広げて文脈を示す
- 東北電のOpen=exec_2の重複を視覚的に処理
- 注釈の配置を調整

出力: data/slippage/slippage_tick_open.png
"""

import csv
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
import numpy as np

# 日本語フォント
jp_fonts = [f.name for f in fm.fontManager.ttflist if "Hiragino" in f.name]
if jp_fonts:
    plt.rcParams["font.family"] = jp_fonts[0]
plt.rcParams["axes.unicode_minus"] = False

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "slippage")

STOCKS = [
    {
        "code": "7532",
        "name": "パンパシHD（7532）",
        "tick_file": "tick_7532_20260224.csv",
        "exec_1": 1012.5,
        "exec_2": 1013.5,
        "open": 1016.0,
    },
    {
        "code": "9506",
        "name": "東北電（9506）",
        "tick_file": "tick_9506_20260224.csv",
        "exec_1": 1301.0,
        "exec_2": 1305.0,
        "open": 1305.0,
    },
]

WINDOW_MINUTES = 2


def load_ticks(filepath, minutes=WINDOW_MINUTES):
    """tickデータを読み込み、寄り付きからN分間を返す。"""
    times, prices, volumes = [], [], []
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = datetime.strptime("2026-02-24 " + row["Time"],
                                   "%Y-%m-%d %H:%M:%S.%f")
            times.append(dt)
            prices.append(float(row["Price"]))
            volumes.append(float(row["TradingVolume"]))

    cutoff = times[0] + timedelta(minutes=minutes)
    idx = [i for i, t in enumerate(times) if t <= cutoff]
    return (
        [times[i] for i in idx],
        [prices[i] for i in idx],
        [volumes[i] for i in idx],
    )


def calc_minute_ohlcv(times, prices, volumes):
    """tickデータから1分足OHLCVを計算する。"""
    from collections import defaultdict
    buckets = defaultdict(lambda: {"prices": [], "volumes": []})
    for t, p, v in zip(times, prices, volumes):
        key = t.replace(second=0, microsecond=0)
        buckets[key]["prices"].append(p)
        buckets[key]["volumes"].append(v)

    candles = []
    for minute_dt in sorted(buckets.keys()):
        ps = buckets[minute_dt]["prices"]
        vs = buckets[minute_dt]["volumes"]
        candles.append({
            "time": minute_dt,
            "open": ps[0],
            "high": max(ps),
            "low": min(ps),
            "close": ps[-1],
            "volume": sum(vs),
        })
    return candles


def draw_candlesticks(ax, candles, width_seconds=40):
    """ローソク足を描画する。"""
    bar_width = timedelta(seconds=width_seconds)
    wick_width = 1.5
    for c in candles:
        center = c["time"] + timedelta(seconds=30)  # 分の中央に配置
        color = "#d62728" if c["close"] < c["open"] else "#2ca02c"
        if abs(c["close"] - c["open"]) < 0.01:
            color = "gray"

        # ヒゲ（high-low）
        ax.plot(
            [center, center], [c["low"], c["high"]],
            color=color, linewidth=wick_width, zorder=1, solid_capstyle="round",
        )
        # 実体（open-close）
        body_bottom = min(c["open"], c["close"])
        body_height = abs(c["close"] - c["open"])
        if body_height < 0.1:
            body_height = 0.3  # 十字線でも見えるように
        rect = plt.Rectangle(
            (center - bar_width / 2, body_bottom),
            bar_width, body_height,
            facecolor=color, edgecolor=color, alpha=0.25,
            linewidth=1, zorder=1,
        )
        ax.add_patch(rect)


def bp(price, ref):
    return (price - ref) / ref * 10000


def main():
    fig = plt.figure(figsize=(13, 10))
    fig.suptitle(
        "寄り付き直後のtick推移と実約定位置（2026/02/24）",
        fontsize=15, fontweight="bold", y=0.98,
    )

    # 2行 × 1列、各行を価格(上)と出来高(下)に分割
    gs_outer = fig.add_gridspec(2, 1, hspace=0.35, top=0.93, bottom=0.06)

    for row_idx, stock in enumerate(STOCKS):
        filepath = os.path.join(DATA_DIR, stock["tick_file"])
        times, prices, volumes = load_ticks(filepath)

        open_p = stock["open"]
        ex1 = stock["exec_1"]
        ex2 = stock["exec_2"]
        slip_bp = bp(ex2, ex1)

        # 各銘柄を価格(3) + 出来高(1) に分割
        gs_inner = gs_outer[row_idx].subgridspec(
            2, 1, height_ratios=[3, 1], hspace=0.05,
        )
        ax_price = fig.add_subplot(gs_inner[0])
        ax_vol = fig.add_subplot(gs_inner[1], sharex=ax_price)

        # ────────── 価格パネル ──────────

        # tick折れ線（価格推移を見やすく）
        ax_price.plot(
            times, prices,
            linewidth=0.5, color="steelblue", alpha=0.7, zorder=2,
        )
        # 出来高で点サイズを変える
        max_vol = max(volumes)
        sizes = [max(8, min(100, v / max_vol * 120)) for v in volumes]
        ax_price.scatter(
            times, prices,
            s=sizes, c="steelblue", alpha=0.5, edgecolors="none",
            zorder=2, label="約定tick（点の大きさ＝出来高）",
        )

        # 板寄せ（最初の大口約定）
        ax_price.scatter(
            [times[0]], [prices[0]],
            s=80, c="#2ca02c", marker="D", edgecolors="black",
            linewidths=0.8, zorder=6,
            label=f"板寄せ = {open_p:,.1f}円（{volumes[0]:,.0f}株）",
        )

        # ── 約定推定時刻マーカー ──
        # tickデータから実約定価格に最初にヒットした時刻を特定
        for ex_price, color_mk, mk_label, marker_shape in [
            (ex1, "#d62728", "1回目", "v"),
            (ex2, "#ff7f0e", "2回目", "^"),
        ]:
            hit_time, hit_vol = None, None
            for t, p, v in zip(times, prices, volumes):
                if abs(p - ex_price) < 0.01:
                    hit_time, hit_vol = t, v
                    break
            if hit_time:
                ax_price.scatter(
                    [hit_time], [ex_price],
                    s=120, c=color_mk, marker=marker_shape,
                    edgecolors="black", linewidths=1, zorder=7,
                )
                time_str = hit_time.strftime("%H:%M:%S")
                ax_price.annotate(
                    f"{mk_label} {time_str}",
                    xy=(hit_time, ex_price),
                    xytext=(8, -18 if marker_shape == "v" else 14),
                    textcoords="offset points",
                    fontsize=8, color=color_mk, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=color_mk,
                                    lw=0.8),
                    zorder=7,
                )

        # ── 基準線: Open ──
        ax_price.axhline(
            open_p, color="#2ca02c", linewidth=2, linestyle="-", zorder=3,
        )

        # ── 実約定線 ──
        ax_price.axhline(
            ex1, color="#d62728", linewidth=2, linestyle="--", zorder=3,
            label=f"1回目約定 = {ex1:,.1f}円",
        )

        # 2回目: Openと重なる場合はラベルで示す
        open_eq_ex2 = abs(open_p - ex2) < 0.1
        if open_eq_ex2:
            ax_price.axhline(
                ex2, color="#ff7f0e", linewidth=2, linestyle=":",
                zorder=3,
                label=f"2回目約定 = {ex2:,.1f}円（= Open）",
            )
        else:
            ax_price.axhline(
                ex2, color="#ff7f0e", linewidth=2, linestyle="--",
                zorder=3,
                label=f"2回目約定 = {ex2:,.1f}円",
            )

        # ── スリッページ帯 ──
        ax_price.axhspan(
            min(ex1, ex2), max(ex1, ex2),
            color="#d62728", alpha=0.10, zorder=1,
        )

        # ── 注釈: スリッページ（右端） ──
        x_right = times[0] + timedelta(minutes=WINDOW_MINUTES * 0.92)
        diff = ex2 - ex1
        mid_slip = (ex1 + ex2) / 2

        ax_price.annotate(
            "", xy=(x_right, ex2), xytext=(x_right, ex1),
            arrowprops=dict(arrowstyle="<->", color="#d62728", lw=2.5),
            zorder=5,
        )
        ax_price.annotate(
            f" {diff:+.1f}円\n ({slip_bp:+.1f}bp)",
            xy=(x_right, mid_slip),
            xytext=(12, 0), textcoords="offset points",
            fontsize=11, fontweight="bold", color="#d62728",
            va="center", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#d62728",
                      alpha=0.9),
            zorder=5,
        )

        # ── 注釈: Open vs 1回目（左寄り） ──
        if abs(open_p - ex1) > 0.1:
            x_left = times[0] + timedelta(minutes=WINDOW_MINUTES * 0.35)
            open_diff = ex1 - open_p
            open_bp_val = bp(ex1, open_p)
            ax_price.annotate(
                "", xy=(x_left, ex1), xytext=(x_left, open_p),
                arrowprops=dict(arrowstyle="<->", color="#2ca02c", lw=2),
                zorder=5,
            )
            ax_price.annotate(
                f" Open比\n {open_diff:+.1f}円（{open_bp_val:+.1f}bp）",
                xy=(x_left, (open_p + ex1) / 2),
                xytext=(12, 0), textcoords="offset points",
                fontsize=10, color="#2ca02c",
                va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#2ca02c",
                          alpha=0.9),
                zorder=5,
            )

        # 軸設定
        ax_price.set_title(stock["name"], fontsize=13, fontweight="bold",
                           loc="left")
        ax_price.set_ylabel("約定価格（円）", fontsize=10)
        ax_price.legend(loc="upper right", fontsize=8, framealpha=0.95,
                        edgecolor="gray")
        ax_price.grid(True, alpha=0.3, linewidth=0.5)
        ax_price.tick_params(axis="x", labelbottom=False)

        # Y軸: tickデータ全体を見せつつ、約定ラインが中心
        tick_min, tick_max = min(prices), max(prices)
        margin = (tick_max - tick_min) * 0.08
        ax_price.set_ylim(tick_min - margin, tick_max + margin)

        # ────────── 出来高パネル ──────────

        # 出来高バー（色を価格変化で分ける）
        colors_vol = []
        for i in range(len(prices)):
            if i == 0:
                colors_vol.append("#2ca02c")  # 板寄せは緑
            elif prices[i] >= prices[i - 1]:
                colors_vol.append("#d62728")  # 上昇=赤
            else:
                colors_vol.append("#1f77b4")  # 下落=青
        # バーの幅を計算（秒単位）
        if len(times) > 1:
            bar_width = timedelta(seconds=0.3)
        ax_vol.bar(
            times, volumes,
            width=bar_width, color=colors_vol, alpha=0.6, edgecolor="none",
        )
        ax_vol.set_ylabel("出来高", fontsize=9)
        ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax_vol.tick_params(axis="x", rotation=30, labelsize=8)
        ax_vol.grid(True, alpha=0.2, linewidth=0.5)
        # 板寄せの出来高が巨大なので対数にする
        ax_vol.set_yscale("log")
        ax_vol.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda x, _: f"{x:,.0f}" if x >= 1 else ""
            )
        )

    plt.savefig(
        os.path.join(DATA_DIR, "slippage_tick_open.png"),
        dpi=150, bbox_inches="tight",
    )
    print("Saved: data/slippage/slippage_tick_open.png")
    plt.close()


if __name__ == "__main__":
    main()
