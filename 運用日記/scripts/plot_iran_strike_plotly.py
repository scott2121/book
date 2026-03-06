"""
Plotlyでイラン攻撃マーケットの価格推移を可視化する。
1. 全マーケット俯瞰（インタラクティブHTML + 静的PNG）
2. 2/28周辺ズーム
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "polymarket")

FILES = {
    "by Jan 15": ("iran_strike_Jan15_yes.csv", "No（不発）"),
    "by Jan 31": ("iran_strike_Jan31_yes.csv", "No（不発）"),
    "by Feb 28": ("iran_strike_Feb28_yes.csv", "Yes（攻撃発生）"),
    "by Mar 31": ("iran_strike_Mar31_yes.csv", "未解決"),
    "by Dec 31": ("iran_strike_Dec31_yes.csv", "未解決"),
}

COLORS = {
    "by Jan 15": "#636EFA",
    "by Jan 31": "#EF553B",
    "by Feb 28": "#00CC96",
    "by Mar 31": "#AB63FA",
    "by Dec 31": "#FFA15A",
}


def load_data():
    dfs = {}
    for label, (fname, _) in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["timestamp_iso"])
            df = df.rename(columns={"timestamp_iso": "datetime", "price": "price"})
            dfs[label] = df
    return dfs


def fig_all_markets(dfs):
    """全マーケットの推移。"""
    fig = go.Figure()

    for label, df in dfs.items():
        resolved = FILES[label][1]
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["price"],
            mode="lines",
            name=f"{label} ({resolved})",
            line=dict(color=COLORS.get(label), width=1.5),
            hovertemplate="%{x|%m/%d %H:%M}<br>Price: %{y:.3f}<extra>" + label + "</extra>",
        ))

    # 2/28マーカー
    fig.add_shape(type="line", x0="2026-02-28", x1="2026-02-28", y0=0, y1=1,
                  yref="paper", line=dict(color="red", dash="dash", width=1), opacity=0.5)
    fig.add_annotation(x="2026-02-28", y=1.03, yref="paper",
                       text="2/28 攻撃発生", showarrow=False, font=dict(size=10, color="red"))

    fig.update_layout(
        title="Polymarket: Iran Strike on Israel — 各日程マーケットのYes価格推移",
        xaxis_title="日時 (UTC)",
        yaxis_title="Yes価格（Implied Probability）",
        yaxis=dict(range=[-0.02, 1.05], tickformat=".0%"),
        hovermode="x unified",
        template="plotly_white",
        width=1200, height=600,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def fig_feb28_zoom(dfs):
    """2/20〜3/1のズーム。Feb28とMar31を比較。"""
    fig = go.Figure()

    for label in ["by Feb 28", "by Mar 31"]:
        if label not in dfs:
            continue
        df = dfs[label]
        mask = (df["datetime"] >= "2026-02-20") & (df["datetime"] <= "2026-03-01")
        df_zoom = df[mask].copy()
        resolved = FILES[label][1]
        fig.add_trace(go.Scatter(
            x=df_zoom["datetime"], y=df_zoom["price"],
            mode="lines",
            name=f"{label} ({resolved})",
            line=dict(color=COLORS.get(label), width=2),
            hovertemplate="%{x|%m/%d %H:%M}<br>Price: %{y:.3f}<extra>" + label + "</extra>",
        ))

    # イベントアノテーション
    fig.add_shape(type="line", x0="2026-02-28", x1="2026-02-28", y0=0, y1=1,
                  yref="paper", line=dict(color="red", dash="dash", width=1), opacity=0.5)

    # 主要な転換点にアノテーション
    fig.add_annotation(x="2026-02-26 12:00", y=0.04, text="Feb28マーケット<br>3.1%まで下落",
                       showarrow=True, arrowhead=2, ax=0, ay=-40,
                       font=dict(size=10))
    fig.add_annotation(x="2026-02-28 12:00", y=0.95, text="攻撃発生<br>→ 99.8%へ急騰",
                       showarrow=True, arrowhead=2, ax=40, ay=30,
                       font=dict(size=10, color="red"))

    fig.update_layout(
        title="Iran Strike — Feb 28マーケット ズーム（2/20〜3/1）",
        xaxis_title="日時 (UTC)",
        yaxis_title="Yes価格（Implied Probability）",
        yaxis=dict(range=[-0.02, 1.05], tickformat=".0%"),
        hovermode="x unified",
        template="plotly_white",
        width=1200, height=500,
        legend=dict(x=0.01, y=0.99),
    )
    return fig


def fig_predictability(dfs):
    """予測可能性の検討：全日程マーケットの最終週推移を重ねて比較。"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            "各日程マーケットのYes価格（全期間）",
            "Feb 28マーケット：最終1週間の1時間足（予測可能性の検討）"
        ],
        vertical_spacing=0.15,
    )

    # 上段：全マーケット
    for label, df in dfs.items():
        resolved = FILES[label][1]
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["price"],
            mode="lines", name=f"{label}",
            line=dict(color=COLORS.get(label), width=1.2),
            legendgroup=label, showlegend=True,
        ), row=1, col=1)

    # 下段：Feb28の最終1週間
    if "by Feb 28" in dfs:
        df = dfs["by Feb 28"]
        mask = (df["datetime"] >= "2026-02-21") & (df["datetime"] <= "2026-03-01")
        df_last = df[mask].copy()

        # 価格変化率を計算
        df_last["pct_change"] = df_last["price"].pct_change()

        fig.add_trace(go.Scatter(
            x=df_last["datetime"], y=df_last["price"],
            mode="lines+markers", name="Feb28 Yes（最終週）",
            line=dict(color="#00CC96", width=2),
            marker=dict(size=3),
            legendgroup="feb28_detail", showlegend=True,
        ), row=2, col=1)

        # 急騰タイミングをハイライト
        fig.add_shape(type="line", x0="2026-02-28", x1="2026-02-28", y0=0, y1=1,
                      yref="y2 domain", line=dict(color="red", dash="dash", width=1),
                      opacity=0.5, row=2, col=1)

    fig.update_yaxes(range=[-0.02, 1.05], tickformat=".0%", row=1, col=1)
    fig.update_yaxes(range=[-0.02, 1.05], tickformat=".0%", row=2, col=1)
    fig.update_xaxes(title_text="日時 (UTC)", row=2, col=1)

    fig.update_layout(
        height=900, width=1200,
        template="plotly_white",
        title="Polymarket: イラン攻撃の予測可能性分析",
        legend=dict(x=1.02, y=1),
    )
    return fig


def main():
    dfs = load_data()
    print(f"Loaded {len(dfs)} markets")

    # 1. 全マーケット
    fig1 = fig_all_markets(dfs)
    path1_html = os.path.join(DATA_DIR, "iran_strike_all_plotly.html")
    path1_png = os.path.join(DATA_DIR, "iran_strike_all_plotly.png")
    fig1.write_html(path1_html)
    fig1.write_image(path1_png, scale=2)
    print(f"Saved: {path1_html}")
    print(f"Saved: {path1_png}")

    # 2. Feb28ズーム
    fig2 = fig_feb28_zoom(dfs)
    path2_html = os.path.join(DATA_DIR, "iran_strike_feb28_zoom_plotly.html")
    path2_png = os.path.join(DATA_DIR, "iran_strike_feb28_zoom_plotly.png")
    fig2.write_html(path2_html)
    fig2.write_image(path2_png, scale=2)
    print(f"Saved: {path2_html}")
    print(f"Saved: {path2_png}")

    # 3. 予測可能性分析
    fig3 = fig_predictability(dfs)
    path3_html = os.path.join(DATA_DIR, "iran_strike_predictability.html")
    path3_png = os.path.join(DATA_DIR, "iran_strike_predictability.png")
    fig3.write_html(path3_html)
    fig3.write_image(path3_png, scale=2)
    print(f"Saved: {path3_html}")
    print(f"Saved: {path3_png}")


if __name__ == "__main__":
    main()
