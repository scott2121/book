"""
J-Quants API v2 を使って対象銘柄の日足データを取得する。
スリッページ検証用：パンパシHD（7532）、東北電（9506）の 2/24 データ。

認証: x-api-key ヘッダーに API キーを直接渡す（v2 方式）。
エンドポイント: https://api.jquants.com/v2/equities/bars/daily

出力:
  data/daily_slippage_targets.csv   — 日足 OHLCV + VWAP
  data/daily_7532_history.csv       — 7532 の直近出来高推移
  data/daily_9506_history.csv       — 9506 の直近出来高推移
"""

import json
import csv
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "slippage")
os.makedirs(DATA_DIR, exist_ok=True)

# .env から JQUANTS_V2_API_KEY を読む（dotenv なしで対応）
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("JQUANTS_V2_API_KEY", "")
if not API_KEY:
    raise RuntimeError("JQUANTS_V2_API_KEY が .env に設定されていません")

BASE_URL = "https://api.jquants.com/v2"

# 対象銘柄（J-Quants は5桁コード: 末尾0を付与）
TARGETS = {
    "75320": "パンパシHD",
    "95060": "東北電",
}
TARGET_DATE = "20260224"

# 出来高推移を取得する期間
HISTORY_FROM = "20260210"
HISTORY_TO = "20260228"


def api_get(path, params):
    """J-Quants API v2 に GET リクエストを送る。"""
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}{path}?{qs}"
    req = Request(url)
    req.add_header("x-api-key", API_KEY)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {body}")
        return {}


def fetch_daily_quotes(code, date):
    """指定日の日足データを取得する。"""
    data = api_get("/equities/bars/daily", {"code": code, "date": date})
    return data.get("data", [])


def fetch_daily_range(code, from_date, to_date):
    """期間指定で日足データを取得する。"""
    data = api_get("/equities/bars/daily", {
        "code": code, "from": from_date, "to": to_date,
    })
    return data.get("data", [])


def code_4digit(code):
    """5桁コードを4桁に変換する。"""
    return code[:4] if len(code) == 5 else code


def save_target_day_csv(all_quotes):
    """対象日の OHLCV データを CSV に保存する。"""
    filepath = os.path.join(DATA_DIR, "daily_slippage_targets.csv")
    fields = [
        "Code", "Date", "Name",
        "Open", "High", "Low", "Close",
        "Volume", "TurnoverValue", "VWAP",
    ]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for q in all_quotes:
            code = str(q.get("Code", ""))
            volume = q.get("Vo", 0)
            turnover = q.get("Va", 0)
            row = {
                "Code": code_4digit(code),
                "Date": q.get("Date", ""),
                "Name": TARGETS.get(code, code_4digit(code)),
                "Open": q.get("O", ""),
                "High": q.get("H", ""),
                "Low": q.get("L", ""),
                "Close": q.get("C", ""),
                "Volume": volume,
                "TurnoverValue": turnover,
                "VWAP": turnover / volume if volume else "",
            }
            writer.writerow(row)
    print(f"  Saved: {filepath} ({len(all_quotes)} rows)")


def save_history_csv(quotes, code):
    """出来高推移を CSV に保存する。"""
    filepath = os.path.join(DATA_DIR, f"daily_{code_4digit(code)}_history.csv")
    fields = ["Date", "Open", "High", "Low", "Close", "Volume", "TurnoverValue"]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for q in quotes:
            row = {
                "Date": q.get("Date", ""),
                "Open": q.get("O", ""),
                "High": q.get("H", ""),
                "Low": q.get("L", ""),
                "Close": q.get("C", ""),
                "Volume": q.get("Vo", ""),
                "TurnoverValue": q.get("Va", ""),
            }
            writer.writerow(row)
    print(f"  Saved: {filepath} ({len(quotes)} rows)")


def main():
    print("=== J-Quants API v2: スリッページ検証データ取得 ===\n")

    # 対象日の日足データ取得
    print(f"--- 対象日 {TARGET_DATE} の日足データ ---")
    all_target_quotes = []
    for code, name in TARGETS.items():
        print(f"\n  {name}（{code_4digit(code)}）:")
        quotes = fetch_daily_quotes(code, TARGET_DATE)
        if quotes:
            q = quotes[0]
            volume = q.get("Vo", 0)
            turnover = q.get("Va", 0)
            vwap = turnover / volume if volume else None
            open_p = q.get("O", "")
            high_p = q.get("H", "")
            low_p = q.get("L", "")
            close_p = q.get("C", "")
            print(f"    Open={open_p}  High={high_p}  Low={low_p}  Close={close_p}")
            if vwap:
                print(f"    Volume={volume:,}  VWAP≈{vwap:.1f}")
            all_target_quotes.extend(quotes)
        else:
            print("    データなし")

    if all_target_quotes:
        save_target_day_csv(all_target_quotes)

    # 出来高推移（流動性比較用）
    print(f"\n--- 出来高推移 {HISTORY_FROM}〜{HISTORY_TO} ---")
    for code, name in TARGETS.items():
        print(f"\n  {name}（{code_4digit(code)}）:")
        history = fetch_daily_range(code, HISTORY_FROM, HISTORY_TO)
        if history:
            save_history_csv(history, code)
            volumes = [q.get("Vo", 0) for q in history]
            avg_vol = sum(volumes) / len(volumes) if volumes else 0
            print(f"    期間平均出来高: {avg_vol:,.0f}")
        else:
            print("    データなし")

    print("\nDone.")


if __name__ == "__main__":
    main()
