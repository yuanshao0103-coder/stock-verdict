"""
screener.py
「自己選啦」多條件選股器模組
獨立 function：render_stock_screener()
掛載方式：在 app.py 加 from screener import render_stock_screener
         並在首頁分頁呼叫 render_stock_screener()
"""

import streamlit as st
import pandas as pd
import numpy as np
import random
import hashlib
from datetime import datetime, timedelta

import os
import pickle

import yfinance as yf
try:
    from FinMind.data import DataLoader as _FMDataLoader
    _FINMIND_OK = True
except ImportError:
    _FINMIND_OK = False

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def _load_cache(filename: str):
    """讀取本地快取，不存在回傳 None。"""
    path = os.path.join(_CACHE_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


def get_cache_timestamp() -> str:
    """回傳快取最後更新時間字串，供 UI 顯示。"""
    path = os.path.join(_CACHE_DIR, "last_update.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "尚無快取"


# ═══════════════════════════════════════════════════════════
# 條件定義
# ═══════════════════════════════════════════════════════════

SCREENER_OPTIONS = {
    "基本": {
        "成長": [
            "月營收成長", "月營收年增率連續 3 月成長", "月營收創近 6 月新高",
            "月營收 3MA 穿越 12MA", "近 1 個月，營收年增率大於 10%",
            "短期營收年增率大於長期營收年增率 10% 以上", "連續 2 年，稅前淨利成長率大於 5%",
        ],
        "獲利": [
            "近 1 季，EPS 大於 0.5 元", "連續 3 年，平均 EPS 大於 1 元",
            "連續 2 年，毛利率大於 5%", "連續 2 年，營業利益率大於 5%",
            "連續 2 年，稅後淨利率大於 5%", "連續 2 年，稅前淨利率大於 5%",
            "毛利率、營業利益率、純益率增加 1%", "連續 2 年，平均股東權益報酬率大於 2%",
            "連續 2 年，資產報酬率大於 2%",
        ],
        "價值": [
            "連續 1 年發放現金股利", "連續 1 年，現金股利發放率大於 50%",
            "連續 2 年，現金股利大於 1 元", "連續 1 年，現金殖利率大於 5%",
            "連續 1 年，股票及現金股利殖利率大於 5%", "近 1 日，現金殖利率大於 5%",
            "股價淨值比小於 1.2 倍", "本益比小於 15 倍", "市值大於 10 億",
            "股本大於 2 億", "淨值大於 15 元", "市值營收比小於 1.5",
        ],
        "個股資料": [
            "市值排名前 50 名", "上市櫃超過 3 年",
        ],
        "安全": [
            "負債比率(年)小於 50%", "長期負債率(年)小於 30%", "流動比率(年)大於 100%",
            "速動比率(年)大於 100%", "連續 2 年，自由現金流量大於 0 元(百萬)",
            "連續 2 年，利息保障倍數大於 40 倍", "研發費用率(年)大於 5%",
        ],
    },
    "技術": {
        "價量": [
            "股價(前一日)大於 10 元", "連續 3 日成交量大於 300 張",
            "連 3 日收紅 K 棒", "連 3 日收黑 K 棒",
            "股價站上 5MA", "股價跌破 5MA",
            "近 1 日，漲幅大於 5%", "近 1 日，跌幅大於 5%",
        ],
    },
    "籌碼": {
        "股權分佈": [
            "千張大戶持股比率大於 50%", "董監持股比率大於 10%",
            "投信持股比率大於 5%", "投信持股比率大於 20 日前投信持股比率",
            "外資持股比率大於 10%", "外資持股比率大於 20 日前外資持股比率",
        ],
        "法人": [
            "連續 3 日投信買超", "連續 3 日自營商買超", "連續 3 日主力買超",
            "外資買超大於 500 張", "投信買超大於 500 張", "自營商買超大於 500 張",
            "外資賣超大於 500 張", "投信賣超大於 500 張", "自營商賣超大於 500 張",
            "連續 3 日三大法人賣超", "連續 3 日外資賣超", "連續 3 日投信賣超",
            "連續 3 日自營商賣超", "連續 3 日主力賣超",
        ],
    },
    "即時": {
        "價量": [
            "當日漲停",
            "當日跌停",
            "股價創 240 日新高",
            "股價創 240 日新低",
        ],
    },
}

# ── 已實作條件集合 ──────────────────────────────────────────

# 第一批：技術面（yfinance）
TECHNICAL_LABELS: set = {
    "股價(前一日)大於 10 元",
    "連續 3 日成交量大於 300 張",
    "連 3 日收紅 K 棒",
    "連 3 日收黑 K 棒",
    "股價站上 5MA",
    "股價跌破 5MA",
    "近 1 日，漲幅大於 5%",
    "近 1 日，跌幅大於 5%",
    "當日漲停",
    "當日跌停",
    "股價創 240 日新高",
    "股價創 240 日新低",
}

# 第二批：法人籌碼（FinMind）
INSTITUTIONAL_LABELS: set = {
    "連續 3 日外資買超",
    "連續 3 日投信買超",
    "連續 3 日自營商買超",
    "連續 3 日外資賣超",
    "連續 3 日投信賣超",
    "連續 3 日自營商賣超",
    "連續 3 日三大法人賣超",
    "外資買超大於 500 張",
    "投信買超大於 500 張",
    "自營商買超大於 500 張",
    "外資賣超大於 500 張",
    "投信賣超大於 500 張",
    "自營商賣超大於 500 張",
}

REAL_LABELS: set = TECHNICAL_LABELS | INSTITUTIONAL_LABELS


def _label_to_key(label: str) -> str:
    return "c_" + hashlib.md5(label.encode()).hexdigest()[:8]


def _build_key_label_map() -> dict:
    mapping = {}
    for sub_dict in SCREENER_OPTIONS.values():
        for labels in sub_dict.values():
            for lbl in labels:
                mapping[_label_to_key(lbl)] = lbl
    return mapping


KEY_TO_LABEL: dict = _build_key_label_map()


# ═══════════════════════════════════════════════════════════
# Universe
# ═══════════════════════════════════════════════════════════

_MOCK_POOL = [
    ("2330.TW", "台積電"), ("2317.TW", "鴻海"),      ("2454.TW", "聯發科"),
    ("2308.TW", "台達電"), ("2382.TW", "廣達"),      ("3008.TW", "大立光"),
    ("2412.TW", "中華電"), ("1301.TW", "台塑"),      ("2881.TW", "富邦金"),
    ("2882.TW", "國泰金"), ("2603.TW", "長榮"),      ("3034.TW", "聯詠"),
    ("2891.TW", "中信金"), ("3711.TW", "日月光投控"), ("2357.TW", "華碩"),
    ("2379.TW", "瑞昱"),   ("4938.TW", "和碩"),      ("2207.TW", "和泰車"),
]


# ═══════════════════════════════════════════════════════════
# 第一批：技術面（yfinance）
# ═══════════════════════════════════════════════════════════

def _fetch_universe_ohlcv(tickers: tuple) -> dict:
    # 優先讀本地快取
    cached = _load_cache("ohlcv.pkl")
    if cached is not None:
        return cached

    # 快取不存在，個別下載（批次下載 TW 股票常 timeout）
    result = {}
    for ticker in tickers:
        for attempt in range(2):
            try:
                df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
                if hasattr(df.index, "tz") and df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                if not df.empty:
                    result[ticker] = df
                break
            except Exception:
                if attempt == 0:
                    import time; time.sleep(1)
    return result


def _check_technical(label: str, df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    close  = df["Close"].dropna()
    open_  = df["Open"].dropna()
    high   = df["High"].dropna()
    low    = df["Low"].dropna()
    volume = df["Volume"].dropna()
    if len(close) < 3:
        return False

    if label == "股價(前一日)大於 10 元":
        return len(close) >= 2 and float(close.iloc[-2]) > 10
    if label == "連續 3 日成交量大於 300 張":
        return len(volume) >= 3 and bool((volume.iloc[-3:] > 300_000).all())
    if label == "連 3 日收紅 K 棒":
        n = min(len(close), len(open_))
        return n >= 3 and bool((close.iloc[-3:].values > open_.iloc[-3:].values).all())
    if label == "連 3 日收黑 K 棒":
        n = min(len(close), len(open_))
        return n >= 3 and bool((close.iloc[-3:].values < open_.iloc[-3:].values).all())
    if label == "股價站上 5MA":
        if len(close) < 6: return False
        return float(close.iloc[-1]) > float(close.iloc[-6:-1].mean())
    if label == "股價跌破 5MA":
        if len(close) < 6: return False
        return float(close.iloc[-1]) < float(close.iloc[-6:-1].mean())
    if label == "近 1 日，漲幅大於 5%":
        if len(close) < 2: return False
        return (float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100 > 5.0
    if label == "近 1 日，跌幅大於 5%":
        if len(close) < 2: return False
        return (float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100 < -5.0
    if label == "當日漲停":
        if len(close) < 2: return False
        return (float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100 >= 9.5
    if label == "當日跌停":
        if len(close) < 2: return False
        return (float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100 <= -9.5
    if label == "股價創 240 日新高":
        w = high.iloc[-240:] if len(high) >= 240 else high
        return float(close.iloc[-1]) >= float(w.max())
    if label == "股價創 240 日新低":
        w = low.iloc[-240:] if len(low) >= 240 else low
        return float(close.iloc[-1]) <= float(w.min())
    return False


# ═══════════════════════════════════════════════════════════
# 第二批：法人籌碼（FinMind）
# ═══════════════════════════════════════════════════════════

def _fetch_institutional_data(stock_id: str) -> pd.DataFrame:
    """優先讀本地快取；快取不存在才即時打 FinMind API。"""
    # 優先讀本地快取
    cached = _load_cache("institutional.pkl")
    if cached is not None:
        return cached.get(stock_id, pd.DataFrame())

    # 快取不存在，即時從 FinMind 下載
    if not _FINMIND_OK:
        return pd.DataFrame()
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d")
    try:
        dl  = _FMDataLoader()
        raw = dl.taiwan_stock_institutional_investors(
            stock_id=stock_id, start_date=start_date, end_date=end_date
        )
        if raw is None or raw.empty:
            return pd.DataFrame()
        raw["date"] = pd.to_datetime(raw["date"])
        raw["buy"]  = pd.to_numeric(raw["buy"],  errors="coerce").fillna(0)
        raw["sell"] = pd.to_numeric(raw["sell"], errors="coerce").fillna(0)
        raw["net"]  = raw["buy"] - raw["sell"]
        return raw
    except Exception:
        return pd.DataFrame()


def _latest_net(raw: pd.DataFrame, names: set, days: int = 3) -> pd.Series:
    """過濾指定法人，彙總每日淨買賣超，回傳最近 N 天的 net Series（新→舊）。"""
    subset = raw[raw["name"].isin(names)]
    if subset.empty:
        return pd.Series(dtype=float)
    daily = (subset.groupby("date")["net"].sum()
             .sort_index(ascending=False)
             .head(days))
    return daily


_FOREIGN  = {"Foreign_Investor", "外資及陸資(不含外資自營商)", "外資及陸資", "外資"}
_TRUST    = {"Investment_Trust", "投信"}
_DEALER   = {"Dealer_self", "Dealer_Hedging", "自營商"}
_ALL_3    = _FOREIGN | _TRUST | _DEALER


def _check_institutional(label: str, raw: pd.DataFrame) -> bool:
    if raw.empty:
        return False

    if label == "連續 3 日外資買超":
        s = _latest_net(raw, _FOREIGN)
        return len(s) >= 3 and bool((s > 0).all())

    if label == "連續 3 日外資賣超":
        s = _latest_net(raw, _FOREIGN)
        return len(s) >= 3 and bool((s < 0).all())

    if label == "連續 3 日投信買超":
        s = _latest_net(raw, _TRUST)
        return len(s) >= 3 and bool((s > 0).all())

    if label == "連續 3 日投信賣超":
        s = _latest_net(raw, _TRUST)
        return len(s) >= 3 and bool((s < 0).all())

    if label == "連續 3 日自營商買超":
        s = _latest_net(raw, _DEALER)
        return len(s) >= 3 and bool((s > 0).all())

    if label == "連續 3 日自營商賣超":
        s = _latest_net(raw, _DEALER)
        return len(s) >= 3 and bool((s < 0).all())

    if label == "連續 3 日三大法人賣超":
        # 外資、投信、自營商三者當日合計淨賣超，連 3 天
        daily_all = (raw[raw["name"].isin(_ALL_3)]
                     .groupby("date")["net"].sum()
                     .sort_index(ascending=False).head(3))
        return len(daily_all) >= 3 and bool((daily_all < 0).all())

    # 500 張 = 500,000 股
    if label == "外資買超大於 500 張":
        s = _latest_net(raw, _FOREIGN, days=1)
        return len(s) >= 1 and float(s.iloc[0]) > 500_000

    if label == "外資賣超大於 500 張":
        s = _latest_net(raw, _FOREIGN, days=1)
        return len(s) >= 1 and float(s.iloc[0]) < -500_000

    if label == "投信買超大於 500 張":
        s = _latest_net(raw, _TRUST, days=1)
        return len(s) >= 1 and float(s.iloc[0]) > 500_000

    if label == "投信賣超大於 500 張":
        s = _latest_net(raw, _TRUST, days=1)
        return len(s) >= 1 and float(s.iloc[0]) < -500_000

    if label == "自營商買超大於 500 張":
        s = _latest_net(raw, _DEALER, days=1)
        return len(s) >= 1 and float(s.iloc[0]) > 500_000

    if label == "自營商賣超大於 500 張":
        s = _latest_net(raw, _DEALER, days=1)
        return len(s) >= 1 and float(s.iloc[0]) < -500_000

    return False


# ═══════════════════════════════════════════════════════════
# 真實篩選主函數
# ═══════════════════════════════════════════════════════════

def real_stock_screener(selected_keys: list) -> tuple:
    """
    回傳 (result_df, real_labels, mock_labels)
    real_labels  = 本次實際驗證的條件
    mock_labels  = 尚未串接的條件
    """
    all_labels   = [KEY_TO_LABEL.get(k, k) for k in selected_keys]
    tech_labels  = [l for l in all_labels if l in TECHNICAL_LABELS]
    inst_labels  = [l for l in all_labels if l in INSTITUTIONAL_LABELS]
    mock_labels  = [l for l in all_labels if l not in REAL_LABELS]
    real_labels  = tech_labels + inst_labels

    # ── 批次下載技術面資料 ──
    tickers      = tuple(t for t, _ in _MOCK_POOL)
    universe_data = _fetch_universe_ohlcv(tickers) if tech_labels else {}

    rows = []
    total = len(_MOCK_POOL)
    progress = st.progress(0, text="篩選中…")

    for idx, (ticker, name) in enumerate(_MOCK_POOL):
        progress.progress((idx + 1) / total, text=f"檢查 {ticker}（{idx+1}/{total}）")

        # 1. 技術面篩選
        if tech_labels:
            df = universe_data.get(ticker)
            if not all(_check_technical(lbl, df) for lbl in tech_labels):
                continue

        # 2. 法人籌碼篩選（通過技術面才呼叫 FinMind，減少 API 次數）
        if inst_labels:
            stock_id = ticker.replace(".TW", "").replace(".TWO", "")
            raw = _fetch_institutional_data(stock_id)
            if not all(_check_institutional(lbl, raw) for lbl in inst_labels):
                continue

        # 3. 取最新報價
        df_ohlcv = universe_data.get(ticker) if tech_labels else None
        if df_ohlcv is not None and not df_ohlcv.empty:
            close = df_ohlcv["Close"].dropna()
            price = float(close.iloc[-1]) if not close.empty else 0.0
            prev  = float(close.iloc[-2]) if len(close) >= 2 else price
        else:
            # 無技術面資料時，用 yfinance 快速取價
            try:
                info  = yf.Ticker(ticker).fast_info
                price = float(info.last_price or 0)
                prev  = float(info.previous_close or price)
            except Exception:
                price, prev = 0.0, 0.0

        chg = (price / prev - 1) * 100 if prev else 0.0
        rows.append({
            "代號":       ticker,
            "名稱":       name,
            "最新股價":   round(price, 2),
            "當日漲跌%":  round(chg, 2),
            "符合條件數": f"{len(real_labels)} / {len(all_labels)}",
        })

    progress.empty()

    df_result = pd.DataFrame(rows).reset_index(drop=True)
    return df_result, real_labels, mock_labels


# ═══════════════════════════════════════════════════════════
# 假選股（所有條件都未串接時的 fallback）
# ═══════════════════════════════════════════════════════════

def mock_stock_screener(selected_keys: list) -> pd.DataFrame:
    n_cond = len(selected_keys)
    if n_cond == 0:
        return pd.DataFrame()
    picks = random.sample(_MOCK_POOL, min(random.randint(3, 5), len(_MOCK_POOL)))
    rows  = []
    for ticker, name in picks:
        rows.append({
            "代號": ticker, "名稱": name,
            "最新股價":  round(random.uniform(30, 1200), 2),
            "當日漲跌%": round(random.uniform(-5, 5), 2),
            "符合條件數": f"{random.randint(max(1,n_cond-1), n_cond)} / {n_cond}",
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════
# 樣式
# ═══════════════════════════════════════════════════════════

def _inject_screener_css():
    st.markdown("""
    <style>
    .screener-sub div[role="radiogroup"] { flex-direction:row !important; flex-wrap:wrap !important; gap:0.4rem !important; }
    .cond-count { display:inline-block; background:#DBEAFE; color:#1D4ED8; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; }
    .cond-mock  { display:inline-block; background:#FEF3C7; color:#92400E; border-radius:20px; padding:2px 10px; font-size:0.72rem; font-weight:600; }
    .cond-real  { display:inline-block; background:#D1FAE5; color:#065F46; border-radius:20px; padding:2px 10px; font-size:0.72rem; font-weight:600; }
    .run-screen button { background:linear-gradient(135deg,#2563EB,#1D4ED8) !important; color:#FFF !important; font-size:1rem !important; font-weight:700 !important; padding:0.85rem !important; border-radius:12px !important; box-shadow:0 4px 16px rgba(37,99,235,0.25) !important; }
    .result-head { font-size:0.95rem; font-weight:700; margin:1.25rem 0 0.75rem; display:flex; align-items:center; gap:0.5rem; }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 主渲染函數
# ═══════════════════════════════════════════════════════════

def render_stock_screener():
    _inject_screener_css()

    if "screener_selected" not in st.session_state:
        st.session_state.screener_selected = set()
    if "my_watchlist" not in st.session_state:
        st.session_state.my_watchlist = []
    if "screener_gen" not in st.session_state:
        st.session_state.screener_gen = 0

    n_selected   = len(st.session_state.screener_selected)
    has_screened = st.session_state.get("has_screened", False)

    label = f"🔍 選股篩選（已選 {n_selected} 項）" if n_selected else "🔍 選股篩選"
    with st.expander(label, expanded=(not has_screened)):
        main_tabs = st.tabs([f"  {name}  " for name in SCREENER_OPTIONS.keys()])
        for tab, (main_name, sub_dict) in zip(main_tabs, SCREENER_OPTIONS.items()):
            with tab:
                _render_main_category(main_name, sub_dict)

        n_selected = len(st.session_state.screener_selected)
        st.markdown("<hr style='border-color:#E8EAED;margin:1rem 0 0.75rem'>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='text-align:center;margin-bottom:0.6rem'>"
            f"目前已勾選 <span class='cond-count'>{n_selected}</span> 項條件</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="run-screen">', unsafe_allow_html=True)
        run = st.button("執行篩選 🚀", use_container_width=True, key="run_screener")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("清除所有條件", use_container_width=True, key="clear_screener"):
            # 保留自選股和目前分析中的股票，其餘全清（包含所有 toggle 狀態）
            watchlist = st.session_state.get("my_watchlist", [])
            active    = st.session_state.get("active", None)
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.my_watchlist = watchlist
            if active is not None:
                st.session_state.active = active
            st.rerun()

        if run:
            if n_selected == 0:
                st.warning("請先至少勾選一項條件再執行篩選。")
            else:
                st.session_state.has_screened = True
                st.session_state.active_screen_conditions = list(st.session_state.screener_selected)
                st.rerun()

        if st.session_state.get("has_screened") and st.session_state.get("active_screen_conditions"):
            st.markdown("<hr style='border-color:#E8EAED;margin:1rem 0 0.75rem'>", unsafe_allow_html=True)
            _render_results(st.session_state.active_screen_conditions)
        elif not has_screened:
            st.markdown("""
            <div style="text-align:center;padding:1.5rem 1rem;color:#9CA3AF">
                <div style="font-size:0.8rem;margin-top:0.4rem">勾選條件後按執行篩選，結果會顯示在這裡</div>
            </div>
            """, unsafe_allow_html=True)

    _render_watchlist()


def _render_main_category(main_name: str, sub_dict: dict):
    sub_names = list(sub_dict.keys())
    sub_key   = f"sub_{main_name}"

    if hasattr(st, "pills"):
        chosen_sub = st.pills("次分類", sub_names, selection_mode="single",
                              default=sub_names[0], key=sub_key, label_visibility="collapsed")
    else:
        st.markdown('<div class="screener-sub">', unsafe_allow_html=True)
        chosen_sub = st.radio("次分類", sub_names, horizontal=True,
                              key=sub_key, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

    if not chosen_sub:
        chosen_sub = sub_names[0]

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    for lbl in sub_dict[chosen_sub]:
        key     = _label_to_key(lbl)
        current = key in st.session_state.screener_selected
        if lbl in TECHNICAL_LABELS:
            display = f"✅ {lbl}"
        elif lbl in INSTITUTIONAL_LABELS:
            display = f"📊 {lbl}"
        else:
            display = lbl
        new_val = st.toggle(display, value=current, key=f"tg_{key}")
        if new_val:
            st.session_state.screener_selected.add(key)
        else:
            st.session_state.screener_selected.discard(key)


_SCREENER_VERSION = "v2"  # 版本號，每次更新邏輯時遞增，強制清除舊快取


def _render_results(selected_keys: list):
    sig = _SCREENER_VERSION + "|" + "|".join(sorted(selected_keys))

    if st.session_state.get("last_screen_sig") != sig:
        all_labels = [KEY_TO_LABEL.get(k, k) for k in selected_keys]
        has_real   = any(l in REAL_LABELS for l in all_labels)

        if has_real:
            df, real_labels_used, mock_labels_pending = real_stock_screener(selected_keys)
        else:
            df = mock_stock_screener(selected_keys)
            real_labels_used    = []
            mock_labels_pending = all_labels

        st.session_state.last_screen_df           = df
        st.session_state.last_screen_real_labels  = real_labels_used
        st.session_state.last_screen_mock_labels  = mock_labels_pending
        st.session_state.last_screen_sig          = sig
    else:
        df                  = st.session_state.last_screen_df
        real_labels_used    = st.session_state.get("last_screen_real_labels", [])
        mock_labels_pending = st.session_state.get("last_screen_mock_labels", [])

    # 快取時間提示
    ts = get_cache_timestamp()
    if ts != "尚無快取":
        st.caption(f"📦 資料快取：{ts}　執行 `python update_cache.py` 可更新")
    else:
        st.caption("⚠️ 尚無本地快取，正在即時打 API（較慢）。執行 `python update_cache.py` 可建立快取")

    # 條件來源標籤
    if real_labels_used:
        st.markdown(
            f"<span class='cond-real'>✅ 真實驗證 {len(real_labels_used)} 條</span>&nbsp;"
            + (f"<span class='cond-mock'>⏳ 待串接 {len(mock_labels_pending)} 條</span>"
               if mock_labels_pending else ""),
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<span class='cond-mock'>⏳ 全部條件尚未串接，顯示示範資料</span>",
                    unsafe_allow_html=True)

    st.markdown(
        f"<div class='result-head'>🎯 篩選結果<span class='cond-count'>{len(df)} 檔符合</span></div>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("沒有符合條件的股票，試著放寬一些條件。")
        return

    all_labels = [KEY_TO_LABEL.get(k, k) for k in selected_keys]
    st.markdown(
        f"<div style='font-size:0.75rem;color:#9CA3AF;margin-bottom:0.75rem'>"
        f"套用條件：{'、'.join(all_labels)}</div>",
        unsafe_allow_html=True,
    )

    watchlist_tickers = {s["ticker"] for s in st.session_state.my_watchlist}

    for _, row in df.iterrows():
        ticker  = row["代號"]
        name    = row["名稱"]
        price   = row["最新股價"]
        chg     = row["當日漲跌%"]
        color   = "pos" if chg >= 0 else "neg"
        arrow   = "▲" if chg >= 0 else "▼"
        in_list = ticker in watchlist_tickers

        left, right = st.columns([5, 1.5])
        with left:
            st.markdown(f"""
            <div class="hot-chip" style="margin-bottom:0.1rem">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div><span class="hot-ticker">{ticker}</span>&nbsp;<span class="hot-cn">{name}</span></div>
                    <div style="text-align:right">
                        <div class="hot-price {color}">{price:,.2f}</div>
                        <div class="{color}" style="font-size:0.8rem;font-weight:600">{arrow} {abs(chg):.2f}%</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with right:
            if in_list:
                st.markdown("<div style='text-align:center;padding:0.7rem 0;font-size:0.8rem;"
                            "color:#00A86B;font-weight:700'>✓ 已加入</div>", unsafe_allow_html=True)
            else:
                if st.button("＋ 加入", key=f"add_{ticker}", use_container_width=True):
                    st.session_state.my_watchlist.append({"ticker": ticker, "name": name})
                    st.rerun()

    if mock_labels_pending:
        st.caption(f"⏳ 尚未串接：{'、'.join(mock_labels_pending)}")


def _render_watchlist():
    wl = st.session_state.my_watchlist
    if not wl:
        return

    st.markdown("<hr style='border-color:#E8EAED;margin:1.25rem 0 0.75rem'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='result-head'>📌 我的自選股<span class='cond-count'>{len(wl)} 檔</span></div>",
        unsafe_allow_html=True,
    )

    for i, stock in enumerate(wl):
        ticker = stock["ticker"]
        name   = stock["name"]
        try:
            info  = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev  = info.get("previousClose", price) or price
            chg   = (price - prev) / prev * 100 if prev else 0.0
        except Exception:
            price, chg = 0.0, 0.0

        color = "pos" if chg >= 0 else "neg"
        arrow = "▲" if chg >= 0 else "▼"

        col_info, col_analyze, col_remove = st.columns([5, 1.5, 1.5])
        with col_info:
            st.markdown(f"""
            <div class="hot-chip" style="margin-bottom:0.1rem">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div><span class="hot-ticker">{ticker}</span>&nbsp;<span class="hot-cn">{name}</span></div>
                    <div style="text-align:right">
                        <div class="hot-price {color}">{price:,.2f}</div>
                        <div class="{color}" style="font-size:0.8rem;font-weight:600">{arrow} {abs(chg):.2f}%</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_analyze:
            if st.button("🔍 分析", key=f"analyze_{ticker}_{i}", use_container_width=True):
                st.session_state.active = ticker
                st.rerun()
        with col_remove:
            if st.button("移除", key=f"remove_{ticker}_{i}", use_container_width=True):
                st.session_state.my_watchlist = [s for s in wl if s["ticker"] != ticker]
                st.rerun()
