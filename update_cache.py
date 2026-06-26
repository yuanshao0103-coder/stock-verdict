"""
update_cache.py
每天收盤後執行一次，把所有 universe 的行情與法人資料存成本地快取。
建議排程時間：每天 15:30（台股法人資料約 15:00 後上傳 FinMind）

執行方式：
    python update_cache.py
"""

import os
import pickle
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

try:
    from FinMind.data import DataLoader as _FMDataLoader
    _FINMIND_OK = True
except ImportError:
    _FINMIND_OK = False
    print("⚠️  FinMind 未安裝，法人資料將跳過")

# ── Universe（與 screener.py 保持一致）──────────────────────
UNIVERSE = [
    ("2330.TW", "台積電"), ("2317.TW", "鴻海"),      ("2454.TW", "聯發科"),
    ("2308.TW", "台達電"), ("2382.TW", "廣達"),      ("3008.TW", "大立光"),
    ("2412.TW", "中華電"), ("1301.TW", "台塑"),      ("2881.TW", "富邦金"),
    ("2882.TW", "國泰金"), ("2603.TW", "長榮"),      ("3034.TW", "聯詠"),
    ("2891.TW", "中信金"), ("3711.TW", "日月光投控"), ("2357.TW", "華碩"),
    ("2379.TW", "瑞昱"),   ("4938.TW", "和碩"),      ("2207.TW", "和泰車"),
]

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _save(obj, filename: str):
    path = os.path.join(CACHE_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"  ✅ 已儲存 {filename}（{os.path.getsize(path) / 1024:.1f} KB）")


# ═══════════════════════════════════════════════════════════
# 1. yfinance OHLCV
# ═══════════════════════════════════════════════════════════

def update_ohlcv():
    print("\n📈 更新技術面 OHLCV（yfinance）…")
    result = {}

    for ticker, name in UNIVERSE:
        for attempt in range(3):  # 最多重試 3 次
            try:
                df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
                df.index = df.index.tz_localize(None)
                if not df.empty:
                    result[ticker] = df
                    print(f"  ✅ {ticker} {name}: {len(df)} 筆")
                else:
                    print(f"  ⚠️  {ticker} {name}: 無資料")
                break
            except Exception as e:
                if attempt < 2:
                    print(f"  ⟳  {ticker} 重試（{attempt+1}/3）…")
                    time.sleep(2)
                else:
                    print(f"  ❌ {ticker} 失敗：{e}")

    _save(result, "ohlcv.pkl")
    print(f"  共 {len(result)} 檔成功")


# ═══════════════════════════════════════════════════════════
# 2. FinMind 法人買賣超
# ═══════════════════════════════════════════════════════════

def update_institutional():
    if not _FINMIND_OK:
        print("\n⚠️  跳過法人資料（FinMind 未安裝）")
        return

    print("\n📊 更新法人買賣超（FinMind）…")
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d")

    dl     = _FMDataLoader()
    result = {}

    for ticker, name in UNIVERSE:
        stock_id = ticker.replace(".TW", "").replace(".TWO", "")
        try:
            raw = dl.taiwan_stock_institutional_investors(
                stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            if raw is not None and not raw.empty:
                raw["date"] = pd.to_datetime(raw["date"])
                raw["buy"]  = pd.to_numeric(raw["buy"],  errors="coerce").fillna(0)
                raw["sell"] = pd.to_numeric(raw["sell"], errors="coerce").fillna(0)
                raw["net"]  = raw["buy"] - raw["sell"]
                result[stock_id] = raw
                print(f"  {stock_id} {name}: {len(raw)} 筆")
            else:
                print(f"  {stock_id} {name}: 無資料")
        except Exception as e:
            print(f"  {stock_id} {name}: 失敗（{e}）")

        time.sleep(0.3)  # 避免打太快被 FinMind 限流

    _save(result, "institutional.pkl")
    print(f"  共 {len(result)} 檔成功")


# ═══════════════════════════════════════════════════════════
# 3. 寫入更新時間戳
# ═══════════════════════════════════════════════════════════

def write_timestamp():
    path = os.path.join(CACHE_DIR, "last_update.txt")
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ts)
    print(f"\n🕒 快取更新時間：{ts}")


# ═══════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  Stock Verdict 快取更新器")
    print("=" * 50)

    _ensure_cache_dir()
    update_ohlcv()
    update_institutional()
    write_timestamp()

    print("\n✅ 全部完成！重新啟動 app.py 即可使用最新資料。")
