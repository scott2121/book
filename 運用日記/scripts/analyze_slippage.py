"""
スリッページ分析スクリプト。
fetch_tick_data.py で取得した日足データと、実約定データを比較・可視化する。

出力:
  data/slippage_analysis.png  — 分析チャート
  stdout                      — 統計サマリー（week1.typ 転記用）
"""

import csv
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "slippage")

# ── 実約定データ（2/24） ──────────────────────────────────
EXECUTIONS = {
    "7532": {
        "name": "パンパシHD",
        "exec_1": 1012.5,
        "exec_2": 1013.5,
        "qty": 100,  # 各回の株数
    },
    "9506": {
        "name": "東北電",
        "exec_1": 1301.0,
        "exec_2": 1305.0,
        "qty": 100,
    },
}


def load_daily_data():
    """daily_slippage_targets.csv から対象日の OHLCV を読む。"""
    filepath = os.path.join(DATA_DIR, "daily_slippage_targets.csv")
    if not os.path.exists(filepath):
        print(f"[WARN] {filepath} が見つかりません。fetch_tick_data.py を先に実行してください。")
        print("[INFO] ハードコード値で分析を続行します。")
        return None

    data = {}
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Code"].replace("0", "", 1) if len(row["Code"]) == 5 else row["Code"]
            # 4桁コードに正規化
            code = row["Code"][:4] if len(row["Code"]) >= 4 else row["Code"]
            data[code] = row
    return data


def load_volume_history(code):
    """出来高推移 CSV を読む。"""
    filepath = os.path.join(DATA_DIR, f"daily_{code}_history.csv")
    if not os.path.exists(filepath):
        return None
    rows = []
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def bp(price, ref):
    """基準価格に対する乖離を bp で計算する。"""
    if ref == 0:
        return 0
    return (price - ref) / ref * 10000


def analyze():
    """メイン分析。"""
    print("=" * 60)
    print("スリッページ分析レポート（2/24 約定分）")
    print("=" * 60)

    daily = load_daily_data()

    results = []

    for code, ex in EXECUTIONS.items():
        print(f"\n{'─' * 50}")
        print(f"■ {ex['name']}（{code}）")
        print(f"{'─' * 50}")

        # 日足データがあれば使う、なければスキップ
        open_price = None
        vwap = None
        close_price = None
        high_price = None
        low_price = None
        volume = None

        if daily and code in daily:
            d = daily[code]
            open_price = float(d["Open"]) if d.get("Open") else None
            close_price = float(d["Close"]) if d.get("Close") else None
            high_price = float(d["High"]) if d.get("High") else None
            low_price = float(d["Low"]) if d.get("Low") else None
            volume = int(float(d["Volume"])) if d.get("Volume") else None
            vwap_str = d.get("VWAP", "")
            vwap = float(vwap_str) if vwap_str else None

        # 約定データ
        exec_1 = ex["exec_1"]
        exec_2 = ex["exec_2"]
        split_diff = exec_2 - exec_1
        split_bp = bp(exec_2, exec_1)

        print(f"\n  約定価格:  1回目 = {exec_1:,.1f}円  /  2回目 = {exec_2:,.1f}円")
        print(f"  分割差:    {split_diff:+,.1f}円（{split_bp:+.1f}bp）")

        if open_price:
            bp_1_vs_open = bp(exec_1, open_price)
            bp_2_vs_open = bp(exec_2, open_price)
            print(f"\n  Open価格:  {open_price:,.1f}円")
            print(f"  1回目 vs Open: {exec_1 - open_price:+,.1f}円（{bp_1_vs_open:+.1f}bp）")
            print(f"  2回目 vs Open: {exec_2 - open_price:+,.1f}円（{bp_2_vs_open:+.1f}bp）")
        else:
            bp_1_vs_open = None
            bp_2_vs_open = None

        if vwap:
            bp_1_vs_vwap = bp(exec_1, vwap)
            bp_2_vs_vwap = bp(exec_2, vwap)
            print(f"\n  VWAP:      {vwap:,.1f}円")
            print(f"  1回目 vs VWAP: {exec_1 - vwap:+,.1f}円（{bp_1_vs_vwap:+.1f}bp）")
            print(f"  2回目 vs VWAP: {exec_2 - vwap:+,.1f}円（{bp_2_vs_vwap:+.1f}bp）")
        else:
            bp_1_vs_vwap = None
            bp_2_vs_vwap = None

        if high_price and low_price:
            day_range = high_price - low_price
            day_range_bp = bp(high_price, low_price)
            print(f"\n  日中レンジ: {low_price:,.1f}〜{high_price:,.1f}円（{day_range:,.1f}円 / {day_range_bp:.0f}bp）")
            # 約定価格がレンジのどのあたりか
            if day_range > 0:
                pos_1 = (exec_1 - low_price) / day_range * 100
                pos_2 = (exec_2 - low_price) / day_range * 100
                print(f"  1回目のレンジ内位置: {pos_1:.0f}%（0%=安値, 100%=高値）")
                print(f"  2回目のレンジ内位置: {pos_2:.0f}%")

        if volume:
            turnover_per_trade = ex["qty"]
            pct_of_volume = turnover_per_trade / volume * 100
            print(f"\n  当日出来高: {volume:,}株")
            print(f"  1注文({ex['qty']}株)の出来高比: {pct_of_volume:.3f}%")

        # 出来高推移
        history = load_volume_history(code)
        if history:
            vols = [int(float(r["Volume"])) for r in history if r.get("Volume")]
            avg_vol = sum(vols) / len(vols) if vols else 0
            print(f"  期間平均出来高: {avg_vol:,.0f}株")

        results.append({
            "code": code,
            "name": ex["name"],
            "exec_1": exec_1,
            "exec_2": exec_2,
            "split_diff": split_diff,
            "split_bp": split_bp,
            "open": open_price,
            "vwap": vwap,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
            "bp_1_vs_open": bp_1_vs_open,
            "bp_2_vs_open": bp_2_vs_open,
        })

    # ── サマリーテーブル ──
    print(f"\n{'=' * 60}")
    print("サマリー（week1.typ 転記用）")
    print(f"{'=' * 60}")

    print(f"\n{'銘柄':<12} {'1回目':>10} {'2回目':>10} {'差':>10} {'差(bp)':>8}", end="")
    if results[0].get("open"):
        print(f" {'Open':>10} {'1回目vsOpen':>12} {'2回目vsOpen':>12}", end="")
    print()
    print("-" * 96)

    for r in results:
        line = f"{r['name']:<10} {r['exec_1']:>10,.1f} {r['exec_2']:>10,.1f} {r['split_diff']:>+10,.1f} {r['split_bp']:>+8.1f}"
        if r.get("open"):
            line += f" {r['open']:>10,.1f} {r['bp_1_vs_open']:>+12.1f} {r['bp_2_vs_open']:>+12.1f}"
        print(line)

    # ── チャート生成 ──
    try:
        generate_chart(results)
    except ImportError:
        print("\n[WARN] matplotlib が見つかりません。チャート生成をスキップします。")
        print("  pip install matplotlib でインストールしてください。")
    except Exception as e:
        print(f"\n[ERROR] チャート生成に失敗: {e}")


def generate_chart(results):
    """分析チャートを生成する。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # 日本語フォント設定
    jp_fonts = [f.name for f in fm.fontManager.ttflist if "Hiragino" in f.name or "Gothic" in f.name]
    if jp_fonts:
        plt.rcParams["font.family"] = jp_fonts[0]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("スリッページ分析（2/24 約定分）", fontsize=14, fontweight="bold")

    names = [r["name"] for r in results]
    colors = ["#4C72B0", "#DD8452"]

    # ── Chart 1: 約定価格の比較（1回目 vs 2回目） ──
    ax1 = axes[0]
    x = range(len(results))
    width = 0.3
    for i, r in enumerate(results):
        ax1.bar(i - width / 2, r["exec_1"], width, color=colors[0], label="1回目" if i == 0 else "")
        ax1.bar(i + width / 2, r["exec_2"], width, color=colors[1], label="2回目" if i == 0 else "")
        # 差を注釈
        ax1.annotate(f"+{r['split_diff']:.1f}円\n({r['split_bp']:+.1f}bp)",
                     xy=(i + width / 2, r["exec_2"]),
                     xytext=(i + width / 2 + 0.15, r["exec_2"]),
                     fontsize=8, ha="left", va="bottom")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(names)
    ax1.set_ylabel("約定価格（円）")
    ax1.set_title("1回目 vs 2回目 約定価格")
    ax1.legend(fontsize=8)
    # Y軸をゼロから始めない
    all_prices = [r["exec_1"] for r in results] + [r["exec_2"] for r in results]
    margin = (max(all_prices) - min(all_prices)) * 0.3 + 5
    ax1.set_ylim(min(all_prices) - margin, max(all_prices) + margin)

    # ── Chart 2: スリッページ（bp） ──
    ax2 = axes[1]
    split_bps = [r["split_bp"] for r in results]
    bars = ax2.bar(names, split_bps, color=colors, width=0.5)
    for bar, val in zip(bars, split_bps):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val:+.1f}bp", ha="center", va="bottom", fontsize=9)
    ax2.set_ylabel("スリッページ（bp）")
    ax2.set_title("2分割によるスリッページ")
    ax2.axhline(y=0, color="gray", linewidth=0.5)

    # ── Chart 3: 日中レンジ内の約定位置 ──
    ax3 = axes[2]
    for i, r in enumerate(results):
        if r.get("high") and r.get("low"):
            low, high = r["low"], r["high"]
            # レンジを棒で表示
            ax3.barh(i, high - low, left=low, height=0.4, color="lightgray", edgecolor="gray")
            # 約定位置
            ax3.plot(r["exec_1"], i, "o", color=colors[0], markersize=10, label="1回目" if i == 0 else "")
            ax3.plot(r["exec_2"], i, "s", color=colors[1], markersize=10, label="2回目" if i == 0 else "")
            if r.get("open"):
                ax3.plot(r["open"], i, "D", color="green", markersize=8, label="Open" if i == 0 else "")
            if r.get("vwap"):
                ax3.plot(r["vwap"], i, "^", color="red", markersize=8, label="VWAP" if i == 0 else "")
        else:
            # 日足データがない場合は約定価格のみ
            ax3.plot(r["exec_1"], i, "o", color=colors[0], markersize=10, label="1回目" if i == 0 else "")
            ax3.plot(r["exec_2"], i, "s", color=colors[1], markersize=10, label="2回目" if i == 0 else "")

    ax3.set_yticks(range(len(results)))
    ax3.set_yticklabels(names)
    ax3.set_xlabel("価格（円）")
    ax3.set_title("日中レンジ内の約定位置")
    ax3.legend(fontsize=7, loc="upper right")

    plt.tight_layout()
    outpath = os.path.join(DATA_DIR, "slippage_analysis.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    print(f"\n  チャート保存: {outpath}")
    plt.close()


if __name__ == "__main__":
    analyze()
