"""
Polymarket「Iran Strike on Israel by...?」イベントの各日程マーケットの価格推移を取得する。
2/28周辺のベッティング推移を確認するためのスクリプト。
"""

import json
import time
import csv
import os
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "polymarket")
os.makedirs(DATA_DIR, exist_ok=True)

# 各マーケットのYesトークンID
MARKETS = {
    "Jan15": {
        "question": "Iran Strike on Israel by January 15?",
        "yes_token": "69473156453348430651596379523885436847743391152379480022525016646485252721374",
        "resolved": "No",
    },
    "Jan31": {
        "question": "Iran Strike on Israel by January 31?",
        "yes_token": "14563704170707092754225166829668039264860512279269689408027999291687006154046",
        "resolved": "No",
    },
    "Feb28": {
        "question": "Iran Strike on Israel by February 28?",
        "yes_token": "40785716512154576515459243689202568309525193875518923120378208451954796944952",
        "resolved": "Yes",
    },
    "Mar31": {
        "question": "Iran Strike on Israel by March 31?",
        "yes_token": "53678394846365317670846972110394788870968223234044254776486112890217851253789",
        "resolved": None,
    },
    "Dec31": {
        "question": "Iran Strike on Israel by December 31?",
        "yes_token": "75546909271998255299028334017428147658881195662320802511067239369571422978901",
        "resolved": None,
    },
}


def fetch_prices_history(token_id, interval="1h", fidelity=60, start_ts=None, end_ts=None):
    """CLOB APIから価格履歴を取得する。15日制限があるため分割取得に対応。"""
    base = "https://clob.polymarket.com/prices-history"
    params = f"market={token_id}&interval={interval}&fidelity={fidelity}"
    if start_ts:
        params += f"&startTs={start_ts}"
    if end_ts:
        params += f"&endTs={end_ts}"
    url = f"{base}?{params}"

    req = Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")

    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data.get("history", [])
        except HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP Error {e.code}: {e.reason}")
                return []
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(1)
    return []


def fetch_full_history(token_id, start_date, end_date, interval="1h"):
    """15日制限を考慮して期間分割で取得し結合する。"""
    all_history = []
    chunk_days = 14  # 15日未満で安全マージン
    chunk_seconds = chunk_days * 86400

    current_start = int(start_date.timestamp())
    final_end = int(end_date.timestamp())

    while current_start < final_end:
        current_end = min(current_start + chunk_seconds, final_end)
        print(f"  Fetching {datetime.fromtimestamp(current_start, tz=timezone.utc).strftime('%Y-%m-%d')} "
              f"-> {datetime.fromtimestamp(current_end, tz=timezone.utc).strftime('%Y-%m-%d')}...")
        history = fetch_prices_history(token_id, interval=interval,
                                       start_ts=current_start, end_ts=current_end)
        all_history.extend(history)
        current_start = current_end
        time.sleep(0.5)  # レート制限回避

    # 重複除去（タイムスタンプでソート）
    seen = set()
    unique = []
    for h in all_history:
        if h["t"] not in seen:
            seen.add(h["t"])
            unique.append(h)
    unique.sort(key=lambda x: x["t"])
    return unique


def save_csv(history, filename):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_unix", "timestamp_iso", "price"])
        for h in history:
            ts = datetime.fromtimestamp(h["t"], tz=timezone.utc)
            writer.writerow([h["t"], ts.isoformat(), h["p"]])
    print(f"  Saved: {filepath} ({len(history)} rows)")
    return filepath


def main():
    # イベント開始日: 2026-01-12
    start_date = datetime(2026, 1, 12, tzinfo=timezone.utc)
    # 取得終了: 2026-03-01（十分なマージン）
    end_date = datetime(2026, 3, 1, tzinfo=timezone.utc)

    for label, info in MARKETS.items():
        print(f"\n=== {label}: {info['question']} (resolved={info['resolved']}) ===")
        history = fetch_full_history(info["yes_token"], start_date, end_date, interval="1h")
        if history:
            save_csv(history, f"iran_strike_{label}_yes.csv")
        else:
            print("  No data returned.")

    print("\nDone. CSV files saved to:", DATA_DIR)


if __name__ == "__main__":
    main()
