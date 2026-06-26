"""
一鍵式股票投資決策 App
手術室美學——白底、大數字、精準診斷
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from screener import render_stock_screener

st.set_page_config(
    page_title="Stock Verdict",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

tw_tz  = pytz.timezone("Asia/Taipei")
now_tw = datetime.now(tw_tz)

# ── 每 30 秒自動刷新（JS 計時器，避免 yfinance 限流）──
st.markdown(
    "<script>setTimeout(function(){window.parent.location.reload();}, 30000);</script>",
    unsafe_allow_html=True,
)

STOCK_NAMES = {
    "TSM":"台積電","NVDA":"輝達","AAPL":"蘋果","MSFT":"微軟",
    "AMZN":"亞馬遜","META":"Meta","GOOGL":"谷歌","AMD":"超微",
    "AVGO":"博通","TSLA":"特斯拉","INTC":"英特爾","QCOM":"高通",
    "2330.TW":"台積電","2317.TW":"鴻海","2454.TW":"聯發科",
    "2308.TW":"台達電","2881.TW":"富邦金","2882.TW":"國泰金",
    "2303.TW":"聯電","3008.TW":"大立光","2412.TW":"中華電",
    "2002.TW":"中鋼","1301.TW":"台塑","2886.TW":"兆豐金",
}

def get_cn_name(ticker):
    return STOCK_NAMES.get(ticker.upper(), "")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; background:#F7F8FA; color:#111; }
.stApp { background:#F7F8FA; }
.block-container { padding:1.25rem 1.25rem 4rem; max-width:960px; }
#MainMenu,footer,header { visibility:hidden; }
.stDeployButton { display:none; }
section[data-testid="stSidebar"] { display:none; }

/* 隱藏 Manage App 工具列 */
[data-testid="stToolbar"] { display:none !important; }
[data-testid="manage-app-button"] { display:none !important; }
iframe[title="streamlit_toolbar"] { display:none !important; }
.stAppToolbar { display:none !important; }
div[class*="Toolbar"] { display:none !important; }

/* 重新整理按鈕特殊樣式 */
.refresh-btn > button {
    background: #F0FDF4 !important;
    color: #166534 !important;
    border: 1.5px solid #00A86B !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
}

/* 搜尋框 */
.stTextInput>div>div>input {
    background:#fff !important; border:2px solid #E0E3E8 !important;
    border-radius:12px !important; color:#111 !important;
    font-size:1rem !important; font-family:'DM Mono',monospace !important;
    padding:0.75rem 1rem !important;
}
.stTextInput>div>div>input:focus { border-color:#0A66C2 !important; box-shadow:0 0 0 3px rgba(10,102,194,0.12) !important; }
.stTextInput>label { display:none !important; }

/* 按鈕 */
.stButton>button {
    background:#111 !important; color:#fff !important; border:none !important;
    border-radius:10px !important; font-weight:600 !important;
    font-size:0.88rem !important; padding:0.55rem 1rem !important;
    width:100% !important; font-family:'DM Sans',sans-serif !important;
}
.stButton>button:hover { background:#333 !important; }

/* Selectbox */
.stSelectbox>div>div { background:#fff !important; border:1.5px solid #E0E3E8 !important; border-radius:10px !important; color:#111 !important; }
.stSelectbox>label { font-size:0.75rem !important; color:#9CA3AF !important; font-weight:600 !important; letter-spacing:0.06em !important; }

/* Number input */
.stNumberInput>div>div>input { background:#fff !important; border:1.5px solid #E0E3E8 !important; border-radius:10px !important; color:#111 !important; font-family:'DM Mono',monospace !important; }
.stNumberInput>label { font-size:0.75rem !important; color:#9CA3AF !important; font-weight:600 !important; letter-spacing:0.06em !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:#EEEFF2; border-radius:12px; padding:5px; gap:4px; border:none; }
.stTabs [data-baseweb="tab"] { background:transparent; color:#6B7280; border-radius:9px; font-weight:500; font-size:0.9rem; padding:0.5rem 1.2rem !important; }
.stTabs [aria-selected="true"] { background:#fff !important; color:#111 !important; box-shadow:0 1px 4px rgba(0,0,0,0.10) !important; }

/* 卡片 */
.card { background:#fff; border:1px solid #E8EAED; border-radius:14px; padding:1.25rem 1.5rem; }
.card-sm { background:#fff; border:1px solid #E8EAED; border-radius:12px; padding:0.9rem 1rem; }

/* 大數字 */
.verdict-number { font-family:'DM Mono',monospace; font-size:4rem; font-weight:500; line-height:1; letter-spacing:-0.03em; }
.verdict-win  { color:#00A86B; }
.verdict-loss { color:#E53935; }
.verdict-label { font-size:0.68rem; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:#9CA3AF; margin-bottom:0.35rem; }
.verdict-sub { font-size:0.78rem; color:#6B7280; margin-top:0.3rem; font-family:'DM Mono',monospace; }

/* 警示 */
.alert-danger { background:#FFF5F5; border:1.5px solid #E53935; border-radius:10px; padding:0.85rem 1.1rem; color:#B91C1C; font-size:0.82rem; font-weight:500; line-height:1.6; }
.alert-safe   { background:#F0FDF4; border:1.5px solid #00A86B; border-radius:10px; padding:0.75rem 1rem; color:#166534; font-size:0.82rem; font-weight:500; }
.alert-warn   { background:#FFFBEB; border:1.5px solid #F59E0B; border-radius:10px; padding:0.85rem 1.1rem; color:#92400E; font-size:0.82rem; font-weight:500; line-height:1.6; }

/* 股票卡 */
.hot-chip { background:#fff; border:1px solid #E8EAED; border-radius:12px; padding:0.85rem 1rem; margin-bottom:0.1rem; }
.hot-ticker { font-family:'DM Mono',monospace; font-size:0.88rem; font-weight:600; color:#0A66C2; }
.hot-cn { font-size:0.72rem; color:#9CA3AF; }
.hot-price { font-size:1.05rem; font-weight:700; margin-top:0.25rem; }
.pos { color:#00A86B; } .neg { color:#E53935; }

/* 新聞 */
.news-item { padding:0.85rem 0; border-bottom:1px solid #F0F1F3; }
.news-title { font-size:0.85rem; font-weight:500; color:#111; line-height:1.5; }
.news-meta  { font-size:0.72rem; color:#9CA3AF; margin-top:0.2rem; }

.divider { border:none; border-top:1px solid #E8EAED; margin:1rem 0; }

/* Expander 投資參數 */
.streamlit-expanderHeader {
    background: #F0F4FF !important;
    border: 1.5px solid #DBEAFE !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #1D4ED8 !important;
    padding: 0.6rem 1rem !important;
}
.streamlit-expanderContent {
    border: 1.5px solid #DBEAFE !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    padding: 1rem !important;
    background: #FAFBFF !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 工具函數
# ═══════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def get_quote(ticker):
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
        prev  = info.get("previousClose", price) or price
        chg   = (price - prev) / prev * 100 if prev else 0
        return {
            "ok":True, "ticker":ticker.upper(),
            "name":info.get("longName", ticker.upper()),
            "cn_name":get_cn_name(ticker),
            "price":price, "chg_pct":chg, "chg_abs":price-prev,
            "volume":info.get("volume",0), "mkt_cap":info.get("marketCap",0),
            "pe":info.get("trailingPE"), "pb":info.get("priceToBook"),
            "eps":info.get("trailingEps"), "rev_growth":info.get("revenueGrowth"),
            "sector":info.get("sector",""), "currency":info.get("currency","USD"),
            "w52h":info.get("fiftyTwoWeekHigh",0), "w52l":info.get("fiftyTwoWeekLow",0),
            "beta":info.get("beta",1.0), "desc":info.get("longBusinessSummary",""),
            "target":info.get("targetMeanPrice"), "rec":info.get("recommendationKey",""),
        }
    except Exception as e:
        return {"ok":False,"error":str(e)}

@st.cache_data(ttl=60, show_spinner=False)
def get_history(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        df.index = pd.to_datetime(df.index).tz_localize(None)

        # ── 過濾 yfinance 台股除權息調整 bug 造成的極端跳價 ──
        # 單日 log return 超過 ±20% 視為資料異常，用前一日收盤填補
        if len(df) > 5:
            log_ret = np.log(df["Close"] / df["Close"].shift(1)).abs()
            bad = log_ret > 0.20
            df.loc[bad, "Close"] = np.nan
            df["Close"] = df["Close"].ffill()

        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_news(ticker):
    try:
        items = yf.Ticker(ticker).news or []
        return [{"title":n.get("title",""),"publisher":n.get("publisher",""),
                 "link":n.get("link","#"),
                 "time":datetime.fromtimestamp(n.get("providerPublishTime",0))}
                for n in items[:10]]
    except:
        return []

def run_mc(close, hold_days, n=8000):
    log_ret = np.log(close/close.shift(1)).dropna()
    # 過濾除權息 bug 造成的離群值（與 check_risks 一致）
    log_ret = log_ret[log_ret.abs() <= 0.15]
    mu, sigma = log_ret.mean(), log_ret.std()
    entry = float(close.iloc[-1])
    rands = np.random.standard_normal((n, hold_days))
    finals = entry * np.exp(np.cumsum((mu-0.5*sigma**2)+sigma*rands, axis=1)[:,-1])
    returns = (finals/entry-1)*100
    paths = entry * np.exp(np.cumsum(
        (mu-0.5*sigma**2)+sigma*np.random.standard_normal((80,hold_days)), axis=1))
    return {"win":float(np.mean(returns>0)*100), "loss":float(np.mean(returns<0)*100),
            "exp":float(np.mean(returns)), "p10":float(np.percentile(returns,10)),
            "p90":float(np.percentile(returns,90)),
            "vol":sigma*np.sqrt(252)*100, "entry":entry,
            "paths":paths, "mu":mu, "sigma":sigma}

MEME_STOCKS = {"GME", "AMC", "BBBY", "KOSS", "BB", "NOK", "EXPR", "CLOV", "WISH", "WKHS"}

def check_risks(quote, df):
    risks = []
    if df.empty or not quote.get("ok"): return risks
    close, volume = df["Close"], df["Volume"]

    # ══════════════════════════════════════════════════════
    # 防線 0：MEME 股黑名單（不依賴財務數字，直接強制警示）
    # ══════════════════════════════════════════════════════
    base_ticker = quote.get("ticker", "").upper().split(".")[0]
    if base_ticker in MEME_STOCKS:
        risks.append({"level": "danger",
            "msg": f"🚨 已知高度投機 MEME 股（{base_ticker}）：股價極易受社群媒體與市場情緒操縱，"
                   "與基本面嚴重脫鉤，請勿以正常估值邏輯判斷，風險極高"})
    eps = quote.get("eps")
    pe  = quote.get("pe")

    if eps is not None and eps < 0:
        risks.append({"level": "warn",
            "msg": f"⚠️ 基本面風險：EPS 為負（{eps:.2f}），公司目前尚未獲利"})
    elif pe is None or pe <= 0:
        risks.append({"level": "warn",
            "msg": "⚠️ 基本面風險：P/E Ratio 為 N/A 或負數，獲利能力存疑"})

    # ══════════════════════════════════════════════════════
    # 防線 2：高波動 / Beta
    # Beta > 2.0 觸發（台股 beta 普遍比美股高，1.5 太嚴格）
    # 年化波動率 > 60% 觸發（過濾離群值後再算，避免除權息 bug）
    # ══════════════════════════════════════════════════════
    beta = quote.get("beta") or 0

    ann_vol = 0.0
    if len(close) >= 30:
        log_ret = np.log(close / close.shift(1)).dropna()
        # 過濾單日超過 ±15% 的離群值（除權息調整 bug 保護）
        log_ret_clean = log_ret[log_ret.abs() <= 0.15]
        if len(log_ret_clean) >= 20:
            ann_vol = float(log_ret_clean.std() * np.sqrt(252) * 100)

    high_vol  = ann_vol > 60
    high_beta = beta > 2.0

    if high_beta or high_vol:
        detail_parts = []
        if high_beta: detail_parts.append(f"Beta {beta:.2f}")
        if high_vol:  detail_parts.append(f"年化波動率 {ann_vol:.1f}%")
        risks.append({"level": "danger",
            "msg": "🚨 極高波動風險：此為高風險/高波動標的，極易受市場情緒操縱，"
                   f"請嚴格控管資金（{' / '.join(detail_parts)}）"})

    # ══════════════════════════════════════════════════════
    # 防線 3：新上市 / 歷史數據不足
    # ══════════════════════════════════════════════════════
    days_of_data = len(close)
    if days_of_data < 30:
        risks.append({"level": "danger",
            "msg": f"⚠️ 新上市股票：僅有 {days_of_data} 天歷史數據，"
                   "模擬結果可靠度極低，風險極高，請謹慎"})
    elif days_of_data < 60:
        risks.append({"level": "danger",
            "msg": "新上市 / 資料不足：無法完整偵測籌碼異常，"
                   "建議等待上市滿 3 個月後再評估"})

    # ══════════════════════════════════════════════════════
    # 防線 4：高估值 IPO / P/E 過高
    # ══════════════════════════════════════════════════════
    mkt_cap = quote.get("mkt_cap", 0)
    if mkt_cap and mkt_cap > 1e12 and (pe is None or pe <= 0):
        risks.append({"level": "danger",
            "msg": "市值超過 1 兆美元但尚未獲利（P/E 為負），"
                   "屬於高風險成長股，估值泡沫風險高"})

    if pe and pe > 0:
        th = 80 if "Technology" in quote.get("sector", "") else 50
        if pe > th * 2:
            risks.append({"level": "danger",
                "msg": f"P/E {pe:.0f}x 極度高估（超過合理值 {int(th*2)}x），小心估值崩塌"})
        elif pe > th * 1.5:
            risks.append({"level": "danger", "msg": f"P/E {pe:.0f}x 嚴重高估"})
        elif pe > th:
            risks.append({"level": "warn",   "msg": f"P/E {pe:.0f}x 估值偏高"})

    # ══════════════════════════════════════════════════════
    # 防線 5：VIX 恐慌指數
    # ══════════════════════════════════════════════════════
    try:
        vix = float(yf.Ticker("^VIX").history(period="3d")["Close"].iloc[-1])
        if vix >= 30:
            risks.append({"level": "danger", "msg": f"VIX {vix:.1f} 極度恐慌，建議大幅降低投入"})
        elif vix >= 22:
            risks.append({"level": "warn",   "msg": f"VIX {vix:.1f} 市場警戒"})
    except:
        pass

    # ══════════════════════════════════════════════════════
    # 防線 6：成交量異常爆量
    # ══════════════════════════════════════════════════════
    if len(volume) >= 60:
        r = float(volume.tail(5).mean()) / float(volume.tail(60).mean())
        if r >= 3.5:
            risks.append({"level": "danger", "msg": f"成交量異常爆量 {r:.1f} 倍，疑似主力介入"})
        elif r >= 2.5:
            risks.append({"level": "warn",   "msg": f"成交量放大 {r:.1f} 倍，留意籌碼"})

    # ══════════════════════════════════════════════════════
    # 防線 7：短期暴漲
    # ══════════════════════════════════════════════════════
    if len(close) >= 11:
        ret5 = (float(close.iloc[-1]) / float(close.iloc[-6]) - 1) * 100
        if ret5 >= 30:
            risks.append({"level": "danger", "msg": f"5日暴漲 {ret5:.1f}%，小心追高接刀"})
        elif ret5 >= 18:
            risks.append({"level": "warn",   "msg": f"5日急漲 {ret5:.1f}%"})

    return risks

def fmt_cap(v, currency="USD"):
    sym = "NT$" if currency == "TWD" else "$"
    if v>=1e12: return f"{sym}{v/1e12:.2f}T"
    if v>=1e9:  return f"{sym}{v/1e9:.1f}B"
    if v>=1e6:  return f"{sym}{v/1e6:.1f}M"
    return f"{sym}{v:,.0f}"

US_TICKERS = ["TSM","NVDA","AAPL","MSFT","AMZN","META","AMD","TSLA"]
TW_TICKERS = ["2330.TW","2317.TW","2454.TW","2308.TW","2881.TW","2882.TW","2303.TW","3008.TW"]

@st.cache_data(ttl=60, show_spinner=False)
def load_stocks(tickers):
    out = []
    for t in tickers:
        q = get_quote(t)
        if q.get("ok") and q["price"]>0: out.append(q)
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_quick_risk_status(ticker: str) -> dict:
    """
    首頁燈號：直接複用 check_risks，與個股頁永遠一致。
    快取 1 小時，避免首頁重複打 API。
    回傳 {"emoji": "🔴/🟡/🟢", "label": "危險/中等/安全", "color": "..."}
    """
    try:
        quote = get_quote(ticker)
        df    = get_history(ticker)
        risks = check_risks(quote, df)

        if any(r["level"] == "danger" for r in risks):
            return {"emoji": "🔴", "label": "危險", "color": "#E53935"}
        if any(r["level"] == "warn"   for r in risks):
            return {"emoji": "🟡", "label": "中等", "color": "#F59E0B"}
        return     {"emoji": "🟢", "label": "安全", "color": "#00A86B"}

    except Exception:
        return     {"emoji": "🟡", "label": "中等", "color": "#F59E0B"}


# ═══════════════════════════════════════════
# 狀態管理
# ═══════════════════════════════════════════

if "active" not in st.session_state: st.session_state.active = ""
if "invest" not in st.session_state: st.session_state.invest = 10000
if "hold"   not in st.session_state: st.session_state.hold   = "3 個月"


# ═══════════════════════════════════════════
# 頂部：標題 + 搜尋列（永遠顯示）
# ═══════════════════════════════════════════

# ── 標題列：時間 + 自動更新提示 ──────────────────
st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.25rem'>
  <div style='font-size:1.3rem;font-weight:700;letter-spacing:-0.02em'>📋 Stock Verdict</div>
  <div style='text-align:right'>
    <div style='font-size:0.72rem;color:#9CA3AF;font-family:DM Mono,monospace'>🇹🇼 {now_tw.strftime('%H:%M:%S')}</div>
    <div style='font-size:0.62rem;color:#C4C9D4'>● 每 30 秒自動更新</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 搜尋列：輸入框 + 🔍分析 ──────────────────────
with st.form(key="search_form", clear_on_submit=False):
    fcols = st.columns([5.5, 1.5])
    with fcols[0]:
        search_val = st.text_input("搜尋", placeholder="美股：AAPL　台股直接輸入數字：2330",
                                    label_visibility="collapsed", key="search_box")
    with fcols[1]:
        search_btn = st.form_submit_button("🔍 分析", use_container_width=True)

def normalize_ticker(raw: str) -> str:
    """
    去空格、轉大寫；
    若輸入是純數字（台股代號），自動補 .TW（上市），
    後續若抓不到再 fallback 到 .TWO（上櫃）。
    """
    t = raw.replace(" ", "").upper()
    if t.isdigit():
        t = t + ".TW"
    return t

if search_btn and search_val.strip():
    st.session_state.active = normalize_ticker(search_val)
    st.rerun()

# ── 投資參數（可收合下拉）────────────────────────
with st.expander("⚙️ 投資參數設定", expanded=False):
    p1, p2 = st.columns(2)
    with p1:
        invest_amount = st.number_input("投入金額（USD $）", min_value=100, max_value=10_000_000,
                                         value=st.session_state.invest, step=1000, format="%d")
        st.session_state.invest = invest_amount
    with p2:
        hold_map = {"1 個月":21, "3 個月":63, "6 個月":126, "1 年":252}
        hold_choice = st.selectbox("預計持有時間", list(hold_map.keys()),
                                    index=list(hold_map.keys()).index(st.session_state.hold))
        st.session_state.hold = hold_choice
hold_map  = {"1 個月":21, "3 個月":63, "6 個月":126, "1 年":252}
hold_days = hold_map[st.session_state.hold]
invest_amount = st.session_state.invest

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 分支 A：首頁
# ═══════════════════════════════════════════

if not st.session_state.active:
    st.markdown("<div style='font-size:1.1rem;font-weight:700;margin-bottom:0.75rem'>今日市場總覽</div>", unsafe_allow_html=True)

    tab_tw, tab_us, tab_screen = st.tabs(["🇹🇼  台股熱門", "🇺🇸  美股熱門", "🎯  自己選啦"])

    def render_grid(tickers):
        with st.spinner("載入行情…"):
            stocks = load_stocks(tickers)
        for q in stocks:
            chg   = q["chg_pct"]
            color = "pos" if chg>=0 else "neg"
            arrow = "▲" if chg>=0 else "▼"
            cn    = q.get("cn_name","")
            cur   = q.get("currency","USD")
            risk  = get_quick_risk_status(q["ticker"])
            r_emoji = risk["emoji"]
            r_label = risk["label"]
            r_color = risk["color"]
            st.markdown(f"""
            <div class="hot-chip">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <span style="font-size:0.72rem;font-weight:700;color:{r_color};
                              background:{'rgba(0,168,107,0.08)' if r_label=='安全' else 'rgba(245,158,11,0.08)' if r_label=='中等' else 'rgba(229,57,53,0.08)'};
                              border-radius:4px;padding:1px 5px;margin-right:4px;white-space:nowrap">
                            {r_emoji} {r_label}
                        </span>
                        <span class="hot-ticker">{q['ticker']}</span>
                        {"&nbsp;<span class='hot-cn'>"+cn+"</span>" if cn else ""}
                    </div>
                    <div style="text-align:right">
                        <div class="hot-price {color}">{cur} {q['price']:,.2f}</div>
                        <div class="{color}" style="font-size:0.8rem;font-weight:600">{arrow} {abs(chg):.2f}%</div>
                    </div>
                </div>
                <div style="font-size:0.68rem;color:#C4C9D4;margin-top:0.3rem">{fmt_cap(q['mkt_cap'], q.get('currency','USD'))}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"分析 {q['ticker']}", key=f"btn_{q['ticker']}", use_container_width=True):
                st.session_state.active = q["ticker"]
                st.rerun()

    with tab_tw:
        render_grid(TW_TICKERS)
    with tab_us:
        render_grid(US_TICKERS)
    with tab_screen:
        render_stock_screener()

    st.stop()


# ═══════════════════════════════════════════
# 分支 B：個股分析
# ═══════════════════════════════════════════

active = st.session_state.active

# 返回按鈕
if st.button("← 返回首頁"):
    st.session_state.active = ""
    st.rerun()

with st.spinner(f"分析 {active} 中…"):
    quote = get_quote(active)
    df    = get_history(active)

    # ── 智慧後備：.TW 抓不到時自動試 .TWO（上櫃股票）──
    need_fallback = (
        active.endswith(".TW") and
        (not quote.get("ok") or quote.get("price", 0) == 0 or df.empty)
    )
    if need_fallback:
        two_ticker = active[:-3] + ".TWO"
        quote_two  = get_quote(two_ticker)
        df_two     = get_history(two_ticker)
        if quote_two.get("ok") and quote_two.get("price", 0) > 0:
            quote  = quote_two
            df     = df_two
            active = two_ticker
            st.session_state.active = two_ticker
            st.toast(f"自動切換為上櫃代號 {two_ticker}", icon="💡")

if not quote.get("ok") or df.empty or quote["price"]==0:
    st.error(f"找不到「{active}」。美股請輸入代號如 AAPL，台股直接輸入數字如 2330")
    st.stop()

# 風險偵測
risks = check_risks(quote, df)
danger = [r for r in risks if r["level"]=="danger"]
warns  = [r for r in risks if r["level"]=="warn"]

if danger:
    st.markdown(f'<div class="alert-danger">🚨 <b>高風險警示</b><br>{"<br>".join("⚠️ "+r["msg"] for r in danger)}</div>', unsafe_allow_html=True)
if warns:
    st.markdown(f'<div class="alert-warn" style="margin-top:0.5rem">⚠️ <b>注意</b><br>{"<br>".join("• "+r["msg"] for r in warns)}</div>', unsafe_allow_html=True)
if not risks:
    st.markdown('<div class="alert-safe">✅ 未偵測到明顯風險</div>', unsafe_allow_html=True)

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

# 股票標題
cn   = quote.get("cn_name","")
name = quote["name"]
price= quote["price"]
chg  = quote["chg_pct"]
cur  = quote.get("currency","USD")
pc   = "#00A86B" if chg>=0 else "#E53935"
arrow= "▲" if chg>=0 else "▼"

st.markdown(f"""
<div style="margin-bottom:0.75rem">
    <div style="font-size:0.72rem;color:#9CA3AF;font-weight:600;letter-spacing:0.06em;text-transform:uppercase">{quote.get('sector','') or '股票'} · {cur}</div>
    <div style="font-size:1.2rem;font-weight:700">{name}{"（"+cn+"）" if cn else ""}</div>
    <div style="display:flex;align-items:baseline;gap:0.75rem;margin-top:0.25rem">
        <span style="font-family:'DM Mono',monospace;font-size:1.8rem;font-weight:600;color:{pc}">{cur} {price:,.2f}</span>
        <span style="font-size:0.9rem;font-weight:600;color:{pc}">{arrow} {abs(chg):.2f}%</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# 蒙地卡羅
close_s = df["Close"].dropna()
with st.spinner("模擬計算中…"):
    mc = run_mc(close_s, hold_days)

win_rate = mc["win"]
loss_rate= mc["loss"]
exp_pct  = mc["exp"]
exp_gain = invest_amount * exp_pct / 100
p10_amt  = invest_amount * mc["p10"] / 100
p90_amt  = invest_amount * mc["p90"] / 100

# 三大數字
st.markdown("<div style='font-size:0.68rem;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;color:#9CA3AF;margin-bottom:0.75rem'>決策核心 — 8,000 次模擬</div>", unsafe_allow_html=True)

v1, v2, v3 = st.columns(3)
with v1:
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:1.5rem 0.5rem">
        <div class="verdict-label">勝率</div>
        <div class="verdict-number verdict-win">{win_rate:.0f}<span style="font-size:2rem">%</span></div>
        <div class="verdict-sub">賺錢的機率</div>
    </div>""", unsafe_allow_html=True)
with v2:
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:1.5rem 0.5rem">
        <div class="verdict-label">賠錢機率</div>
        <div class="verdict-number verdict-loss">{loss_rate:.0f}<span style="font-size:2rem">%</span></div>
        <div class="verdict-sub">波動率 {mc['vol']:.1f}%</div>
    </div>""", unsafe_allow_html=True)
with v3:
    gc = "#00A86B" if exp_gain>=0 else "#E53935"
    gs = "+" if exp_gain>=0 else ""
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:1.5rem 0.5rem">
        <div class="verdict-label">預測收益</div>
        <div class="verdict-number" style="color:{gc}">{gs}{exp_pct:.1f}<span style="font-size:2rem">%</span></div>
        <div class="verdict-sub">{gs}${abs(exp_gain):,.0f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center;font-size:0.72rem;color:#9CA3AF;margin-top:0.5rem">
    投入 {cur} {invest_amount:,} · 持有 {hold_choice} · 90% 落在 {p10_amt:+,.0f} ~ {p90_amt:+,.0f} {cur}
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# 次要指標
m1,m2,m3,m4 = st.columns(4)
_cur_sym = cur
_cur_sign = "NT$" if cur == "TWD" else "$"
for col,(label,val) in zip([m1,m2,m3,m4],[
    ("市值",   fmt_cap(quote["mkt_cap"], cur) if quote["mkt_cap"] else "N/A"),
    ("本益比", f"{quote['pe']:.1f}x"     if quote["pe"]      else "N/A"),
    ("52W高",  f"{_cur_sym} {quote['w52h']:,.2f}"  if quote["w52h"] else "N/A"),
    ("52W低",  f"{_cur_sym} {quote['w52l']:,.2f}"  if quote["w52l"] else "N/A"),
]):
    with col:
        st.markdown(f"""
        <div class="card-sm" style="text-align:center">
            <div style="font-size:0.65rem;color:#9CA3AF;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">{label}</div>
            <div style="font-family:'DM Mono',monospace;font-size:1rem;font-weight:600;margin-top:0.2rem">{val}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# Tabs
tab_chart, tab_news = st.tabs(["📈  走勢與預測", "📰  新聞與財報"])

with tab_chart:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=2,cols=1,row_heights=[0.72,0.28],
                            shared_xaxes=True,vertical_spacing=0.04)
        fig.add_trace(go.Scatter(x=df.index,y=df["Close"],name="收盤價",
            line=dict(color="#111",width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>" + cur + " %{y:,.2f}<extra></extra>"),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["Close"].rolling(200).mean(),name="200MA",
            line=dict(color="#9CA3AF",width=1.5,dash="dot")),row=1,col=1)

        last_date    = df.index[-1]
        future_dates = pd.date_range(start=last_date+timedelta(days=1),periods=hold_days,freq="B")
        for path in mc["paths"][:50]:
            fig.add_trace(go.Scatter(x=future_dates,y=path,mode="lines",
                line=dict(color="rgba(10,102,194,0.07)",width=1),
                showlegend=False,hoverinfo="skip"),row=1,col=1)

        t = np.arange(1,hold_days+1)
        mu,sigma,entry = mc["mu"],mc["sigma"],mc["entry"]
        fig.add_trace(go.Scatter(x=future_dates,y=entry*np.exp((mu-0.5*sigma**2)*t+sigma*np.sqrt(t)*1.28),
            name="樂觀P90",line=dict(color="#00A86B",width=2,dash="dash")),row=1,col=1)
        fig.add_trace(go.Scatter(x=future_dates,y=entry*np.exp((mu-0.5*sigma**2)*t),
            name="中性P50",line=dict(color="#0A66C2",width=2)),row=1,col=1)
        fig.add_trace(go.Scatter(x=future_dates,y=entry*np.exp((mu-0.5*sigma**2)*t+sigma*np.sqrt(t)*(-1.28)),
            name="悲觀P10",line=dict(color="#E53935",width=2,dash="dash"),
            fill="tonexty",fillcolor="rgba(10,102,194,0.04)"),row=1,col=1)
        fig.add_vline(x=str(last_date),line_color="#E8EAED",line_width=1.5)

        vc = ["#00A86B" if c>=o else "#E53935" for c,o in zip(df["Close"],df["Open"])]
        fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="成交量",marker_color=vc,opacity=0.6),row=2,col=1)

        fig.update_layout(height=480,paper_bgcolor="#fff",plot_bgcolor="#fff",
            font=dict(family="DM Sans",color="#6B7280",size=11),hovermode="x unified",
            legend=dict(orientation="h",yanchor="bottom",y=1.01,bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(gridcolor="#F0F1F3"),yaxis=dict(gridcolor="#F0F1F3"),
            xaxis2=dict(gridcolor="#F0F1F3"),yaxis2=dict(gridcolor="#F0F1F3"),
            xaxis_rangeslider_visible=False)
        st.plotly_chart(fig,use_container_width=True)
    except Exception as e:
        st.warning(f"圖表錯誤：{e}")

with tab_news:
    col_n, col_f = st.columns([3,2])
    with col_n:
        st.markdown("<div style='font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#9CA3AF;margin-bottom:0.75rem'>近期新聞</div>", unsafe_allow_html=True)
        with st.spinner("抓取新聞…"):
            news_list = get_news(active)
        if news_list:
            for n in news_list:
                st.markdown(f"""
                <div class="news-item">
                    <a href="{n['link']}" target="_blank" style="text-decoration:none">
                        <div class="news-title">{n['title']}</div>
                    </a>
                    <div class="news-meta">{n['publisher']} · {n['time'].strftime('%m/%d %H:%M')}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#9CA3AF;font-size:0.85rem">暫無新聞</div>', unsafe_allow_html=True)

    with col_f:
        st.markdown("<div style='font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#9CA3AF;margin-bottom:0.75rem'>財報指標</div>", unsafe_allow_html=True)
        def fin_row(k,v,pos=None):
            c = "#9CA3AF" if v in (None,"N/A") else "#00A86B" if pos is True else "#E53935" if pos is False else "#111"
            return f'<div style="display:flex;justify-content:space-between;padding:0.65rem 0;border-bottom:1px solid #F0F1F3"><span style="font-size:0.8rem;color:#6B7280">{k}</span><span style="font-family:DM Mono,monospace;font-size:0.85rem;font-weight:500;color:{c}">{v}</span></div>'

        pe=quote.get("pe"); pb=quote.get("pb"); eps=quote.get("eps")
        rev=quote.get("rev_growth"); beta=quote.get("beta"); tgt=quote.get("target")
        rev_s = f"+{rev*100:.1f}%" if rev and rev>0 else (f"{rev*100:.1f}%" if rev else "N/A")
        up = (tgt/price-1)*100 if tgt and price else None
        up_s = f"{_cur_sign}{tgt:.2f} ({up:+.1f}%)" if up else "N/A"

        html = (fin_row("本益比 P/E", f"{pe:.1f}x" if pe else "N/A") +
                fin_row("股價淨值比", f"{pb:.2f}x" if pb else "N/A") +
                fin_row("EPS",        f"{_cur_sign}{eps:.2f}" if eps else "N/A") +
                fin_row("營收成長",   rev_s, pos=(rev>0) if rev else None) +
                fin_row("Beta",       f"{beta:.2f}" if beta else "N/A") +
                fin_row("目標價",     up_s, pos=(up>0) if up else None) +
                fin_row("分析師評級", quote.get("rec","").upper() or "N/A"))
        st.markdown(f'<div class="card">{html}</div>', unsafe_allow_html=True)

        desc = quote.get("desc","")
        if desc:
            with st.expander("公司簡介"):
                st.markdown(f'<div style="font-size:0.8rem;color:#6B7280;line-height:1.8">{desc[:500]}…</div>', unsafe_allow_html=True)
