import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns
import quantstats as qs
from datetime import datetime, timedelta, date
from itertools import combinations
from collections import defaultdict
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator
import colorsys as _colorsys
import warnings
import io
import os
import tempfile
import requests
import gc
import database as db

warnings.filterwarnings('ignore')

import my_portfolio as _p
import json

# 1. Create a session that looks like a regular browser
@st.cache_resource
def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

# 2. Create a function that loads data and caches it (e.g. for 1 hour)
@st.cache_data(ttl=3600)
def download_data(tickers, start, end):
    try:
        session = get_session()
        data = yf.download(tickers, start=start, end=end, session=session, group_by='column')
        if data.empty:
            return None
        return data
    except Exception as e:
        st.error(f"Data loading failed: {e}")
        return None

# ── Load user config (overrides my_portfolio.py without touching it) ──────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _find_config_file():
    """Return path of the first .json file found next to the script, or None."""
    for f in sorted(os.listdir(_SCRIPT_DIR)):
        if f.endswith(".json"):
            return os.path.join(_SCRIPT_DIR, f)
    return None

def _load_config(path=None):
    """Load config from path (or auto-detected file). Falls back to {} if not found."""
    target = path or _find_config_file()
    if target and os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

_active_config_file = _find_config_file()
_cfg = _load_config(_active_config_file)

# Helper: pick from saved config, else fall back to my_portfolio attribute
def _cv(key, default):
    return _cfg.get(key, default)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Matplotlib dark theme ─────────────────────────────────────────────────────
plt.style.use('dark_background')
plt.close('all')  # free any figures left open from previous rerun
plt.rcParams['figure.max_open_warning'] = 0  # suppress warning noise

def apply_style(fig, ax_list=None):
    fig.patch.set_facecolor(db.PLOT_BG)
    if ax_list is None:
        ax_list = fig.get_axes()
    for ax in ax_list:
        ax.set_facecolor(db.PLOT_BG)
        ax.tick_params(colors=db.PLOT_FG, labelsize=9)
        ax.xaxis.label.set_color(db.PLOT_FG)
        ax.yaxis.label.set_color(db.PLOT_FG)
        ax.title.set_color(db.PLOT_FG)
        for spine in ax.spines.values():
            spine.set_edgecolor(db.DARKER)
        ax.grid(True, color=db.DARKER, linewidth=0.5, alpha=0.8)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
            
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background-color: {db.ACCENT2};
    color: {db.PLOT_FG};
    border: 1px solid {db.ACCENT2};
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    background-color: {db.BUTTONHOVER};
    color: {db.PLOT_FG};
    border: 1px solid {db.BUTTONHOVER};
}}

.stSlider [data-baseweb="slider"] [role="slider"] {{
    background-color: {db.ACCENT2};
}}

.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {{
    color: {db.ACCENT2};
}}

.stSlider [data-baseweb="slider"] div[data-testid="stSlider"] {{
    color: {db.ACCENT2};
}}

st-ct {{
    background-color: {db.ACCENT} !important;
}}

html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
}}

h1, h2, h3 {{
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: -0.02em;
}}

.stApp {{
    background-color: {'#0f0f0f'};
    color: {db.PLOT_FG};
}}

section[data-testid="stSidebar"] {{
    background-color: {'#161616'};
    border-right: 1px solid {db.DARKER};
}}

.metric-card {{
    background: {db.PLOT_BG};
    border: 1px solid {db.DARKER};
    border-left: 3px solid {db.ACCENT};
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}}

.metric-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: {db.DARK};
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}}

.metric-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem;
    font-weight: 600;
    color: {db.PLOT_FG};
}}

.metric-value.positive {{ color: {db.ACCENT}; }}
.metric-value.negative {{ color: {db.ACCENT2}; }}

.section-header {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: {db.DARK};
    text-transform: uppercase;
    letter-spacing: 0.15em;
    border-bottom: 1px solid {db.DARKER};
    padding-bottom: 0.5rem;
    margin: 2rem 0 1rem 0;
}}

.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
}}

div[data-testid="stMetric"] {{
    background: {db.PLOT_BG};
    border: 1px solid {db.DARKER};
    padding: 1rem;
}}

.stDataFrame {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
}}
/* Target buttons that contain bold (strong) text */
div[data-testid="stColumn"] button:has(strong) {{
    background-color: {db.ACCENT2} !important; /* Streamlit red or your custom color */
    border-color: {db.ACCENT2} !important;
    color: {db.PLOT_FG} !important;
}}

/* Style for bold text inside the button (size and weight) */
div[data-testid="stColumn"] button strong {{
    font-weight: 900 !important;
    font-size: 1.2rem !important;
    color: {db.PLOT_FG} !important;
}}

/* Hover-efekti aktiiviselle napille (pysyy punaisena) */
div[data-testid="stColumn"] button:has(strong):hover {{
    background-color: {db.ACCENT2} !important;
    border-color: {db.ACCENT2} !important;
}}

/* Remove rounded corners from chart containers */
[data-testid="stImage"] img,
[data-testid="stPlotlyChart"] > div,
[data-testid="element-container"] iframe {{
    border-radius: 0 !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Global dollar formatter ───────────────────────────────────────────────────

def fmt_dollar(value):
    """Format an actual dollar value into a readable string."""
    a = abs(value)
    if a < 10_000:
        return f"${value:,.0f}"
    elif a < 1_000_000:
        return f"${value/1_000:,.0f}k"
    elif a < 1_000_000_000:
        return f"${value/1_000_000:,.2f}M"
    elif a < 1_000_000_000_000:
        return f"${value/1_000_000_000:,.2f}B"
    else:
        return f"${value/1_000_000_000_000:,.2f}T"

def dollar_axis(ax):
    """Apply smart dollar formatting to a matplotlib Y axis."""
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_dollar(x)))

def pct_axis(ax, decimals=1, multiply=False):
    """Apply % suffix to Y axis tick labels.
    multiply=True: values are in decimal form (0.05) and need ×100 first.
    multiply=False: values are already in percent form (5.0).
    """
    if multiply:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x*100:.{decimals}f}%"))
    else:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.{decimals}f}%"))


# ── Sidebar – Portfolio Configuration ────────────────────────────────────────
with st.sidebar:
    st.markdown("## Portfolio Analysis")
    st.markdown('<div class="section-header">Holdings</div>', unsafe_allow_html=True)

    tickers_input  = st.text_input("Tickers (comma-separated)", _cv("tickers_input", ",".join(_p.tickers)))
    weights_input  = st.text_input("Weights (comma-separated)", _cv("weights_input", ",".join(str(w) for w in _p.weights)))
    asset_class_input = st.text_input(
        "Asset classes (comma-separated)",
        _cv("asset_class_input", ",".join(_p.asset_classes.values()))
    )

    st.markdown('<div class="section-header">Date Range</div>', unsafe_allow_html=True)
    start_date = st.date_input("Start date", date.fromisoformat(_cv("start_date", _p.start_date)), min_value=date(1980, 1, 1), max_value=date.today()).strftime('%Y-%m-%d')
    end_date   = st.date_input("End date",   date.today() - timedelta(days=1), min_value=date(1980, 1, 1), max_value=date.today()).strftime('%Y-%m-%d')

    st.markdown('<div class="section-header">Parameters</div>', unsafe_allow_html=True)
    risk_free_rate           = st.slider("Risk-free rate",           0.0, 10.0, float(_cv("risk_free_rate", _p.risk_free_rate) * 100), 0.1, format="%.1f%%") / 100
    benchmark_ticker         = st.text_input("Benchmark ticker", _cv("benchmark_ticker", ""))
    initial_investment       = st.number_input("Initial investment", 0.01, 10_000_000.0, float(_cv("initial_investment", _p.initial_investment)), step=0.01)
    monthly_investment       = st.number_input("Monthly contribution", 0.0, 50_000.0, float(_cv("monthly_investment", _p.monthly_investment)), step=0.01)
    _car_options = ["Historical"] + [f"{v/10:.1f}%" for v in range(0, 301)]  # 0.0%..30.0%
    _car_saved = _cv("custom_annualized_return", _p.custom_annualized_return or 0)
    _car_default = "Historical" if _car_saved == 0 else f"{_car_saved*100:.1f}%"
    if _car_default not in _car_options:
        _car_default = "Historical"
    _car_sel = st.select_slider(
        "Custom annual return (forecast)",
        options=_car_options,
        value=_car_default,
        help="Select 'Historical' to use the portfolio's own annualised return from the data. Otherwise pick a fixed forecast rate."
    )
    custom_annualized_return = 0.0 if _car_sel == "Historical" else float(_car_sel.replace("%", "")) / 100
    safe_withdrawal_rate     = st.slider("Safe withdrawal rate (SWR)", 0.0, 10.0, float(_cv("safe_withdrawal_rate", _p.safe_withdrawal_rate) * 100), 0.1, format="%.1f%%") / 100

    st.markdown('<div class="section-header">Currency</div>', unsafe_allow_html=True)
    _CURRENCIES = ["USD", "EUR", "GBP", "SEK", "NOK", "DKK", "CHF", "JPY", "CAD", "AUD"]
    _CURRENCY_SYMBOLS = {"USD":"$","EUR":"€","GBP":"£","SEK":"kr","NOK":"kr","DKK":"kr","CHF":"Fr","JPY":"¥","CAD":"C$","AUD":"A$"}
    purchase_currency = st.selectbox(
        "Purchase currency",
        _CURRENCIES,
        index=_CURRENCIES.index(_cv("purchase_currency", "EUR")),
        help="The currency you used to buy your positions. Initial investment is entered in this currency."
    )
    display_currency = st.selectbox(
        "Display currency",
        _CURRENCIES,
        index=_CURRENCIES.index(_cv("display_currency", _cv("purchase_currency", "EUR"))),
        help="The currency to display current value in."
    )

    st.markdown('<div class="section-header">Configuration Management</div>', unsafe_allow_html=True)

    # ── Download current settings (above upload) ──────────────────────────────
    current_config = {
        "tickers_input":           tickers_input,
        "weights_input":           weights_input,
        "asset_class_input":       asset_class_input,
        "start_date":              str(start_date),
        "risk_free_rate":          risk_free_rate,
        "benchmark_ticker":        benchmark_ticker,
        "initial_investment":      initial_investment,
        "monthly_investment":      monthly_investment,
        "custom_annualized_return":custom_annualized_return,
        "safe_withdrawal_rate":    safe_withdrawal_rate,
        "purchase_currency":       purchase_currency,
        "display_currency":        display_currency,
        "etf_custom_db":           st.session_state.get("etf_custom_db", {}),
    }
    _dl_name = os.path.basename(_active_config_file) if _active_config_file else "portfolio.json"
    config_json_bytes = json.dumps(current_config, indent=2, ensure_ascii=False).encode('utf-8')
    st.download_button(
        label="Download configuration",
        data=config_json_bytes,
        file_name=_dl_name,
        mime="application/json",
        width='stretch',
    )

    # ── Upload any .json config file ──────────────────────────────────────────
    _uploaded = st.file_uploader(
        "Load config (.json)",
        type="json",
        help="Upload any .json portfolio config file. Saved next to the script and loaded immediately.",
    )
    if _uploaded is not None:
        _upload_id = f"{_uploaded.name}_{_uploaded.size}"
        if st.session_state.get("_last_upload_id") != _upload_id:
            _save_path = os.path.join(_SCRIPT_DIR, _uploaded.name)
            for _old_f in os.listdir(_SCRIPT_DIR):
                if _old_f.endswith(".json"):
                    os.remove(os.path.join(_SCRIPT_DIR, _old_f))
            with open(_save_path, "wb") as _fh:
                _fh.write(_uploaded.getbuffer())
            st.session_state["_last_upload_id"] = _upload_id
            st.rerun()

    # Show which file is active
    if _active_config_file:
        st.caption(f"Active config: `{os.path.basename(_active_config_file)}`")
    else:
        st.caption("No config file — using defaults from my_portfolio.py")

    # ── Reset: delete the active config file ──────────────────────────────────
    if _active_config_file and os.path.exists(_active_config_file):
        if st.button("Reset to defaults", width='stretch'):
            os.remove(_active_config_file)
            st.rerun()


# ── Parse inputs ─────────────────────────────────────────────────────────────
tickers      = [t.strip() for t in tickers_input.split(",") if t.strip()]
weights_raw  = [float(w.strip()) for w in weights_input.split(",") if w.strip()]
asset_classes_raw = [a.strip() for a in asset_class_input.split(",") if a.strip()]

n_tickers = len(tickers)
n_weights = len(weights_raw)


weight_sum = sum(weights_raw)

portfolio     = dict(zip(tickers, weights_raw))
# If only one asset class is given, apply it to all tickers
if len(asset_classes_raw) == 1:
    asset_classes_raw = asset_classes_raw * len(tickers)
asset_classes = dict(zip(tickers, asset_classes_raw))

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("# Portfolio Analysis")
st.caption(f"Period: {start_date} to {end_date}  |  Benchmark: {benchmark_ticker if benchmark_ticker.strip() else 'None'}  |  Risk-free rate: {risk_free_rate:.2%}")

if n_tickers == 0:
    st.error("No tickers entered.")
    st.stop()
elif n_weights != n_tickers:
    st.error("Number of tickers do not match the number of weights.")
    st.stop()
elif len(asset_classes_raw) > 1 and len(asset_classes_raw) != n_tickers:
    st.error("Number of asset classes do not match the number of tickers.")
    st.stop()
elif abs(weight_sum - 1.0) > 1e-4:
    st.error(f"Weights do not add up to 1 (current sum: {weight_sum:.4f}).")
    st.stop()


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    return data

@st.cache_data(show_spinner=False, ttl=3600)
def load_benchmark(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df["Close"]
    return df.squeeze()

with st.spinner("Fetching market data..."):
    data      = load_data(tickers, start_date, end_date)
    bench_raw = load_benchmark(benchmark_ticker, start_date, end_date) if benchmark_ticker.strip() else None

# ── Per-ticker currency detection & FX conversion ────────────────────────────
@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False, ttl=86400)
def get_ticker_currency(ticker):
    """Return the currency yFinance reports for this ticker (e.g. 'EUR', 'USD')."""
    try:
        info = yf.Ticker(ticker).info
        return info.get("currency", "USD").upper()
    except Exception:
        return "USD"

@st.cache_data(show_spinner=False)
def get_fx_rate(from_currency, to_currency, date_str):
    """Return rate: 1 from_currency = X to_currency, on or near date_str."""
    if from_currency == to_currency:
        return 1.0
    pair = f"{from_currency}{to_currency}=X"
    target = pd.Timestamp(date_str)
    start  = (target - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    end    = (target + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    try:
        s = yf.download(pair, start=start, end=end, auto_adjust=True, progress=False)
        if isinstance(s.columns, pd.MultiIndex):
            s = s["Close"]
        s = s.squeeze().dropna()
        if s.empty:
            return 1.0
        idx = s.index.get_indexer([target], method="nearest")[0]
        return float(s.iloc[idx])
    except Exception:
        return 1.0

# Detect each ticker's native currency
with st.spinner("Detecting ticker currencies..."):
    ticker_currencies = {t: get_ticker_currency(t) for t in tickers}

# Weighted portfolio currency: majority currency by weight
_weighted_currencies = {}
for t, w in zip(tickers, weights_raw):
    c = ticker_currencies.get(t, "USD")
    _weighted_currencies[c] = _weighted_currencies.get(c, 0) + w
portfolio_native_currency = max(_weighted_currencies, key=_weighted_currencies.get)

# Convert initial_investment (purchase_currency) → portfolio native currency at start_date
fx_purchase_to_native = get_fx_rate(purchase_currency, portfolio_native_currency, start_date)
initial_investment_native = initial_investment * fx_purchase_to_native

# Convert portfolio native currency → display currency at end_date
fx_native_to_display = get_fx_rate(portfolio_native_currency, display_currency, end_date)

# Symbol for display currency
disp_sym = _CURRENCY_SYMBOLS.get(display_currency, display_currency + " ")

# Align columns to ticker order -- available always defined
if isinstance(data, pd.Series):
    data = data.to_frame(name=tickers[0])

available = [t for t in tickers if t in data.columns]

if len(available) == 0:
    st.error("No tickers could be loaded. Check the connection and ticker names.")
    st.stop()

data      = data[available]
w_aligned = np.array([weights_raw[tickers.index(t)] for t in available])
w_aligned = w_aligned / w_aligned.sum()

# Returns
returns = data.pct_change(fill_method=None).dropna(how='all').fillna(0)

if returns.shape[1] != len(w_aligned):
    st.warning("Number of tickers do not match the number of weights.")
    st.stop()

portfolio_returns = returns.dot(w_aligned)
portfolio_returns = pd.Series(portfolio_returns, name="Portfolio")

p_ret = portfolio_returns  # aina täysi historia — ei koskaan leikata benchmarkin mukaan

if bench_raw is not None and not bench_raw.empty:
    bench_returns = bench_raw.pct_change(fill_method=None).dropna()
    common_idx    = p_ret.index.intersection(bench_returns.index)
    p_ret_c       = p_ret.loc[common_idx]   # leikattu versio vain benchmark-vertailuun
    b_ret         = bench_returns.loc[common_idx]
else:
    p_ret_c = p_ret
    b_ret   = None


# ── Helper functions ──────────────────────────────────────────────────────────
def ann_return(r):
    return (1 + r).prod() ** (252 / len(r)) - 1

def ann_vol(r):
    return r.std() * np.sqrt(252)

def sharpe(r, rf=risk_free_rate):
    excess = ann_return(r) - rf
    vol    = ann_vol(r)
    return excess / vol if vol > 0 else np.nan

def sortino(r, rf=risk_free_rate):
    excess = ann_return(r) - rf
    downside_returns = np.where(r < 0, r, 0)
    downside_vol = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
    return excess / downside_vol if downside_vol > 0 else np.nan

def max_drawdown(r):
    cum  = (1 + r).cumprod()
    roll = cum.cummax()
    dd   = (cum - roll) / roll
    return dd.min()

def calmar(r):
    md = max_drawdown(r)
    return ann_return(r) / abs(md) if md != 0 else np.nan

def var_95(r):
    return np.percentile(r.dropna(), 5)

def cvar_95(r):
    v = var_95(r)
    return r[r <= v].mean()

def beta(p, b):
    cov = np.cov(p, b)
    return cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else np.nan

def alpha_jensen(p, b, rf=risk_free_rate):
    b_val   = beta(p, b)
    p_ann   = ann_return(p)
    b_ann   = ann_return(b)
    return p_ann - (rf + b_val * (b_ann - rf))

def tracking_error(p, b):
    return (p - b).std() * np.sqrt(252)

def information_ratio(p, b):
    active = ann_return(p) - ann_return(b)
    te     = tracking_error(p, b)
    return active / te if te > 0 else np.nan

def up_capture(p, b):
    mask = b > 0
    if mask.sum() == 0: return np.nan
    return p[mask].mean() / b[mask].mean() * 100

def down_capture(p, b):
    mask = b < 0
    if mask.sum() == 0: return np.nan
    return p[mask].mean() / b[mask].mean() * 100


# ── Compute all metrics ────────────────────────────────────────────────────────
# Portfolio-only metrics → p_ret (täysi historia, ei riipu benchmarkista)
# Cross/benchmark metrics → p_ret_c (leikattu yhteiselle aikavälille)
_has_bench = b_ret is not None
_corr_coef = float(np.corrcoef(p_ret_c, b_ret)[0, 1]) if _has_bench else np.nan
m = {
    "Annual Return":       ann_return(p_ret),
    "Annual Volatility":   ann_vol(p_ret),
    "Sharpe Ratio":        sharpe(p_ret),
    "Sortino Ratio":       sortino(p_ret),
    "Max Drawdown":        max_drawdown(p_ret),
    "Calmar Ratio":        calmar(p_ret),
    "VaR 95%":             var_95(p_ret),
    "CVaR 95%":            cvar_95(p_ret),
    "Beta":                beta(p_ret_c.values, b_ret.values)          if _has_bench else np.nan,
    "Alpha (Jensen)":      alpha_jensen(p_ret_c.values, b_ret.values)  if _has_bench else np.nan,
    "Tracking Error":      tracking_error(p_ret_c, b_ret)              if _has_bench else np.nan,
    "Information Ratio":   information_ratio(p_ret_c, b_ret)           if _has_bench else np.nan,
    "Up Capture":          up_capture(p_ret_c, b_ret)                  if _has_bench else np.nan,
    "Down Capture":        down_capture(p_ret_c, b_ret)                if _has_bench else np.nan,
    "Bench Annual Return": ann_return(b_ret)                           if _has_bench else np.nan,
    "Bench Volatility":    ann_vol(b_ret)                              if _has_bench else np.nan,
    "Bench Sharpe":        sharpe(b_ret)                               if _has_bench else np.nan,
    "Bench Max Drawdown":  max_drawdown(b_ret)                         if _has_bench else np.nan,
}


# ── Pre-computed cumulative series (reused in Overview, Risk, Benchmark tabs) ──
cum_p = (1 + p_ret).cumprod() * initial_investment_native
cum_b = (1 + b_ret).cumprod() * initial_investment_native if _has_bench else None

# ── Tabs ──────────────────────────────────────────────────────────────────────
_TAB_NAMES = ["Overview", "Performance", "Risk", "Benchmark", "Distribution",
              "Correlations", "FI Forecast", "Optimization", "Report"]
(tab_overview, tab_perf, tab_risk, tab_bench, tab_alloc,
 tab_corr, tab_fi, tab_opt, tab_report) = st.tabs(_TAB_NAMES)



# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

current_portfolio_value_native = (1 + p_ret).cumprod().iloc[-1] * initial_investment_native
current_portfolio_value_disp   = current_portfolio_value_native * fx_native_to_display
initial_investment_disp        = initial_investment if purchase_currency == display_currency \
                                    else initial_investment * fx_purchase_to_native * fx_native_to_display
total_gain_disp = current_portfolio_value_disp - initial_investment_disp
current_portfolio_value = current_portfolio_value_native  # alias used in FI tab

with tab_overview:
        col1, col2, col3, col4 = st.columns(4)

        def metric_html(label, value, fmt=".2%", positive_good=True):
            if isinstance(value, float) and not np.isnan(value):
                display = f"{value:{fmt}}"
                if positive_good:
                    cls = "positive" if value > 0 else "negative"
                else:
                    cls = "negative"
            else:
                display = "N/A"
                cls = ""
            return f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value {cls}">{display}</div>
            </div>"""

        with col1:
            st.markdown(metric_html("Annual Return",     m["Annual Return"]),     unsafe_allow_html=True)
            st.markdown(metric_html("Annual Volatility", m["Annual Volatility"]), unsafe_allow_html=True)
        with col2:
            st.markdown(metric_html("Sharpe Ratio",  m["Sharpe Ratio"],  fmt=".3f"), unsafe_allow_html=True)
            st.markdown(metric_html("Sortino Ratio", m["Sortino Ratio"], fmt=".3f"), unsafe_allow_html=True)
        with col3:
            st.markdown(metric_html("Max Drawdown", m["Max Drawdown"], positive_good=False), unsafe_allow_html=True)
            st.markdown(metric_html("Calmar Ratio", m["Calmar Ratio"], fmt=".3f"),           unsafe_allow_html=True)
        with col4:
            st.markdown(metric_html("VaR 95%",  m["VaR 95%"],  positive_good=False), unsafe_allow_html=True)
            st.markdown(metric_html("CVaR 95%", m["CVaR 95%"], positive_good=False), unsafe_allow_html=True)

        st.markdown('<div class="section-header">Portfolio Value - Rough Estimate</div>', unsafe_allow_html=True)
        _tc_str = ", ".join(f"{t} - {c}" for t,c in ticker_currencies.items() if t in available)
        _fx_note = ""
        if purchase_currency != portfolio_native_currency:
            _fx_note += f" {purchase_currency} → {portfolio_native_currency} @ {fx_purchase_to_native:.4f}"
        if portfolio_native_currency != display_currency:
            _fx_note += f" {portfolio_native_currency} → {display_currency} @ {fx_native_to_display:.4f}"
        st.caption(f"Ticker currencies: {_tc_str} | Portfolio native: {portfolio_native_currency} | Display: {display_currency} | {_fx_note}")
        pv_col1, pv_col2, pv_col3 = st.columns(3)
        with pv_col1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Current Value ({display_currency})</div>
                <div class="metric-value positive">{disp_sym}{current_portfolio_value_disp:,.2f}</div>
            </div>""", unsafe_allow_html=True)
        with pv_col2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Initial Investment ({purchase_currency})</div>
                <div class="metric-value">{_CURRENCY_SYMBOLS.get(purchase_currency, purchase_currency + ' ')}{initial_investment:,.2f}</div>
            </div>""", unsafe_allow_html=True)
        with pv_col3:
            gain_cls = "positive" if total_gain_disp >= 0 else "negative"
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Total Gain / Loss ({display_currency})</div>
                <div class="metric-value {gain_cls}">{disp_sym}{total_gain_disp:,.2f}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Holdings - Links to Yahoo Finance</div>', unsafe_allow_html=True)

        # Yahoo Finance links
        links_html = f'''
        <style>
        .yf-link {{
            font-family: IBM Plex Mono, monospace;
            font-size: 0.8rem;
            color: {db.PLOT_FG} !important;
            background: {db.PLOT_BG} !important;
            border: 1px solid {db.DARKER} !important;
            padding: 0.35rem 0.75rem;
            text-decoration: none !important;
            letter-spacing: 0.05em;
            border-radius: 0;
            outline: none;
        }}
        .yf-link:hover {{
            color: {db.ACCENT2} !important;
        }}
        </style>
        <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:1.5rem;">
        '''
        for t in tickers:
            url = f'https://finance.yahoo.com/quote/{t}'
            links_html += f'<a href="{url}" target="_blank" class="yf-link">{t}</a>'
        links_html += '</div>'
        st.markdown(links_html, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Cumulative Growth</div>', unsafe_allow_html=True)

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(cum_p.index, cum_p.values, color=db.ACCENT,  linewidth=2,   label="Portfolio")
        if cum_b is not None:
            ax.plot(cum_b.index, cum_b.values, color=db.ACCENT3,
                    linewidth=1.5, label=benchmark_ticker, alpha=0.7)
        ax.fill_between(cum_p.index, initial_investment_native,
                        cum_p.values, alpha=0.1, color=db.ACCENT)
        ax.set_ylabel("Value")
        ax.legend(fontsize=9, loc='upper left')
        date_min = cum_p.index.min()
        date_max = cum_p.index.max()
        date_range = date_max - date_min
        ax.set_xlim(date_min, date_max + (date_range * 0.01))
        dollar_axis(ax)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

        # ── Per-ticker cumulative growth chart ────────────────────────────────
        st.markdown('<div class="section-header">Per-Ticker Cumulative Growth</div>', unsafe_allow_html=True)

        _ticker_colors = [db.ACCENT, db.ACCENT3, db.ACCENT4, db.ACCENT2,
                          '#b19cd9', '#f4a261', '#e9c46a', '#2a9d8f']
        fig, ax = plt.subplots(figsize=(12, 4))
        for _i, _t in enumerate(available):
            _r = returns[_t].dropna()
            if len(_r) < 2:
                continue
            _cum_t = (1 + _r).cumprod() * initial_investment_native
            _color = _ticker_colors[_i % len(_ticker_colors)]
            ax.plot(_cum_t.index, _cum_t.values, linewidth=1.5,
                    color=_color, label=_t, alpha=0.9)
        ax.set_ylabel("Value")
        ax.legend(fontsize=8, loc='upper left')
        _date_min = returns.index.min()
        _date_max = returns.index.max()
        ax.set_xlim(_date_min, _date_max + (_date_max - _date_min) * 0.01)
        dollar_axis(ax)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

gc.collect()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab_perf:
        st.markdown('<div class="section-header">Daily Returns</div>', unsafe_allow_html=True)

        fig, axes = plt.subplots(3, 1, figsize=(12, 9))

        # 1. Daily returns bar
        axes[0].bar(p_ret.index, p_ret.values,
                    color=np.where(p_ret.values >= 0, db.ACCENT, db.ACCENT2), width=1, alpha=0.8)
        axes[0].set_xlim(left=p_ret.index.min() + ((p_ret.index.max() - p_ret.index.min()) * -0.003),
                         right=p_ret.index.max() + ((p_ret.index.max() - p_ret.index.min()) * 0.003))
        axes[0].set_ylabel("Daily Return")
        axes[0].set_title("Daily Returns")
        pct_axis(axes[0], decimals=1, multiply=True)

        # 2. Cumulative returns
        cum = (1 + p_ret).cumprod() - 1
        axes[1].plot(cum.index, cum.values * 100, color=db.ACCENT, linewidth=2)
        axes[1].fill_between(cum.index, 0, cum.values * 100, alpha=0.15, color=db.ACCENT)
        axes[1].set_xlim(left=cum.index.min() + ((cum.index.max() - cum.index.min()) * -0.001),
                         right=cum.index.max() + ((cum.index.max() - cum.index.min()) * 0.001))
        axes[1].set_ylabel("Cumulative Return")
        axes[1].set_title("Cumulative Return")
        pct_axis(axes[1], decimals=0)

        # 3. Rolling 30-day volatility
        roll_vol        = p_ret.rolling(30).std() * np.sqrt(252) * 100
        roll_vol_valid  = roll_vol.dropna()
        axes[2].plot(roll_vol.index, roll_vol.values, color=db.ACCENT4, linewidth=1.5)
        axes[2].fill_between(roll_vol.index, 0, roll_vol.values, alpha=0.2, color=db.ACCENT4)
        _rv_min, _rv_max = roll_vol_valid.index.min(), roll_vol_valid.index.max()
        axes[2].set_xlim(left=_rv_min + ((_rv_max - _rv_min) * -0.001),
                         right=_rv_max + ((_rv_max - _rv_min) * 0.001))
        axes[2].set_ylabel("Annualized Vol")
        axes[2].set_title("30-Day Rolling Volatility")
        pct_axis(axes[2], decimals=1)

        apply_style(fig, axes)
        fig.tight_layout(pad=2)
        st.pyplot(fig)
        plt.close("all")

        # Monthly returns heatmap
        st.markdown('<div class="section-header">Monthly Returns Heatmap</div>', unsafe_allow_html=True)
        monthly = p_ret.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        monthly_df = pd.DataFrame({
            'Year':  monthly.index.year,
            'Month': monthly.index.month,
            'Return': monthly.values
        })
        if not monthly_df.empty:
            pivot = monthly_df.pivot(index='Year', columns='Month', values='Return')
            month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            pivot.columns = [month_names[m-1] for m in pivot.columns]

            fig, ax = plt.subplots(figsize=(12, max(3, len(pivot) * 0.5 + 1)))
            sns.heatmap(pivot * 100, annot=True, fmt=".1f", cmap='RdYlGn',
                        center=0, linewidths=0.5, linecolor='#0f0f0f',
                        annot_kws={'size': 8}, ax=ax,
                        cbar_kws={'label': 'Return', 'format': mticker.FuncFormatter(lambda x, _: f"{x:.1f}%")})
            # Add % suffix to each annotated cell
            for t in ax.texts:
                t.set_text(t.get_text() + "%")
            ax.set_title("Monthly Returns")
            ax.set_xlabel("")
            apply_style(fig, [ax])
            st.pyplot(fig)
            plt.close("all")

        # Annual returns
        st.markdown('<div class="section-header">Annual Returns</div>', unsafe_allow_html=True)
        annual = p_ret.resample('YE').apply(lambda x: (1 + x).prod() - 1)
        fig, ax = plt.subplots(figsize=(12, 3))
        colors_bar = [db.ACCENT if v >= 0 else db.ACCENT2 for v in annual.values]
        ax.bar(annual.index.year, annual.values * 100, color=colors_bar, width=0.6)
        ax.axhline(0, color='#555', linewidth=0.8)
        ax.set_ylabel("Return")
        ax.set_title("Annual Returns")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        pct_axis(ax, decimals=0)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

gc.collect()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – RISK
# ══════════════════════════════════════════════════════════════════════════════
with tab_risk:
        st.markdown('<div class="section-header">Risk Metrics</div>', unsafe_allow_html=True)

        risk_df = pd.DataFrame({
            "Metric": ["Annual Volatility", "Max Drawdown", "VaR 95%", "CVaR 95%",
                       "Calmar Ratio", "Sharpe Ratio", "Sortino Ratio"],
            "Portfolio": [
                f"{m['Annual Volatility']:.2%}",
                f"{m['Max Drawdown']:.2%}",
                f"{m['VaR 95%']:.2%}",
                f"{m['CVaR 95%']:.2%}",
                f"{m['Calmar Ratio']:.3f}",
                f"{m['Sharpe Ratio']:.3f}",
                f"{m['Sortino Ratio']:.3f}",
            ],
            "Benchmark": [
                f"{m['Bench Volatility']:.2%}"  if _has_bench else "N/A",
                f"{m['Bench Max Drawdown']:.2%}" if _has_bench else "N/A",
                f"{var_95(b_ret):.2%}"           if _has_bench else "N/A",
                f"{cvar_95(b_ret):.2%}"          if _has_bench else "N/A",
                f"{calmar(b_ret):.3f}"           if _has_bench else "N/A",
                f"{m['Bench Sharpe']:.3f}"       if _has_bench else "N/A",
                f"{sortino(b_ret):.3f}"          if _has_bench else "N/A",
            ],
        })
        st.dataframe(risk_df, width='stretch', hide_index=True)

        # Drawdown chart
        st.markdown('<div class="section-header">Drawdown</div>', unsafe_allow_html=True)
        _cum_p_dd = (1 + p_ret).cumprod()
        roll      = _cum_p_dd.cummax()
        dd        = (_cum_p_dd - roll) / roll

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.fill_between(dd.index,   dd.values   * 100, 0, color=db.ACCENT2, alpha=0.6, label="Portfolio")
        if _has_bench:
            _cum_b_dd = (1 + b_ret).cumprod()
            roll_b    = _cum_b_dd.cummax()
            dd_b      = (_cum_b_dd - roll_b) / roll_b
            ax.fill_between(dd_b.index, dd_b.values * 100, 0, color=db.ACCENT3, alpha=0.3, label=benchmark_ticker)
        ax.set_xlim(left=dd.index.min() + (dd.index.max() - dd.index.min()) * -0.0015,
                    right=dd.index.max() + (dd.index.max() - dd.index.min()) * 0.0015)
        ax.set_ylabel("Drawdown")
        ax.set_title("Drawdown Chart")
        ax.legend(fontsize=9, loc='lower left', framealpha=0.5)
        pct_axis(ax, decimals=1)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

        # Return distribution
        st.markdown('<div class="section-header">Return Distribution</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(12, 3.5))
        ax.hist(p_ret.values * 100, bins=80, color=db.ACCENT, alpha=0.75, edgecolor='none', label="Portfolio")
        if _has_bench:
            ax.hist(b_ret.values * 100, bins=80, color=db.ACCENT3, alpha=0.4, edgecolor='none', label=benchmark_ticker)
        v95 = var_95(p_ret) * 100
        ax.axvline(v95, color=db.ACCENT2, linewidth=1.5, linestyle='--', label=f"VaR 95%: {v95:.2f}%")
        ax.set_xlabel("Daily Return")
        ax.set_ylabel("Frequency")
        ax.set_title("Return Distribution")
        ax.legend(fontsize=9, loc='upper left', framealpha=0.5)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

        # Rolling Sharpe
        st.markdown('<div class="section-header">252-Day Rolling Sharpe Ratio</div>', unsafe_allow_html=True)
        roll_sharpe = p_ret.rolling(252).apply(lambda x: sharpe(pd.Series(x)), raw=False)
        if roll_sharpe.dropna().empty:
            st.caption("Not enough data for 252-day rolling Sharpe.")
        else:
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.plot(roll_sharpe.index, roll_sharpe.values, color=db.ACCENT, linewidth=1.5)
            ax.axhline(0, color='#555', linewidth=0.8)
            ax.axhline(1, color=db.ACCENT, linewidth=0.6, linestyle='--', alpha=0.5)
            ax.set_ylabel("Sharpe Ratio")
            apply_style(fig, [ax])
            st.pyplot(fig)
            plt.close("all")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
with tab_bench:
    if not _has_bench:
        st.info("No benchmark selected. Enter a ticker (e.g. **SPY**) in the sidebar to enable benchmark comparison.")
    else:
        st.markdown('<div class="section-header">Benchmark Comparison</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        bench_metrics = pd.DataFrame({
            "Metric": ["Annual Return", "Annual Volatility", "Sharpe Ratio", "Max Drawdown",
                       "Beta", "Alpha (Jensen)", "Tracking Error", "Information Ratio",
                       "Up Capture", "Down Capture", "Correlation"],
            "Portfolio": [
                f"{m['Annual Return']:.2%}",
                f"{m['Annual Volatility']:.2%}",
                f"{m['Sharpe Ratio']:.3f}",
                f"{m['Max Drawdown']:.2%}",
                f"{m['Beta']:.3f}",
                f"{m['Alpha (Jensen)']:.2%}",
                f"{m['Tracking Error']:.2%}",
                f"{m['Information Ratio']:.3f}",
                f"{m['Up Capture']:.1f}%",
                f"{m['Down Capture']:.1f}%",
                f"{_corr_coef:.3f}",
            ],
            f"Benchmark ({benchmark_ticker})": [
                f"{m['Bench Annual Return']:.2%}",
                f"{m['Bench Volatility']:.2%}",
                f"{m['Bench Sharpe']:.3f}",
                f"{m['Bench Max Drawdown']:.2%}",
                "1.000", "0.00%", "0.00%", "———", "100.0%", "100.0%", "1.000",
            ],
        })
        st.dataframe(bench_metrics, width='stretch', hide_index=True)

        # Cumulative comparison
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(cum_p.index, cum_p.values, color=db.ACCENT,  linewidth=2,   label="Portfolio")
        ax.plot(cum_b.index, cum_b.values, color=db.ACCENT3, linewidth=1.5, label=benchmark_ticker, alpha=0.8)
        ax.set_xlim(left=cum_p.index.min(), 
                    right=cum_p.index.max() + (cum_p.index.max() - cum_p.index.min()) * 0.01)
        ax.set_ylabel("Value")
        ax.set_title("Cumulative Growth Comparison")

        ax.legend(fontsize=9, framealpha=0.5)
        dollar_axis(ax)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close("all")

        # Rolling Beta
        st.markdown('<div class="section-header">252-Day Rolling Beta</div>', unsafe_allow_html=True)

        import statsmodels.api as sm

        def rolling_beta_ols(p_ret, b_ret, window=252, min_obs=100):
            """
            Compute rolling beta using OLS regression (most accurate / standard method)
            
            Parameters:
            -----------
            p_ret : pd.Series
                Portfolio / asset daily returns (indexed by date)
            b_ret : pd.Series
                Benchmark / market daily returns (same index)
            window : int, default 252
                Rolling window length in trading days (~1 year)
            min_obs : int, default 100
                Minimum number of observations required to fit regression
            
            Returns:
            --------
            pd.Series
                Rolling beta values, indexed by the end date of each window
            """
            if len(p_ret) == 0 or len(b_ret) == 0:
                return pd.Series(dtype=float, name='rolling_beta')
            
            # Align series and remove rows where either is NaN
            df = pd.DataFrame({'port': p_ret, 'mkt': b_ret}).dropna()
            
            if len(df) < min_obs:
                return pd.Series(dtype=float, name='rolling_beta')
            
            p_ret = df['port']
            b_ret = df['mkt']
            
            betas = []
            dates = []
            
            for i in range(window - 1, len(p_ret)):
                # Take exactly the same time window from both series
                window_port = p_ret.iloc[i - window + 1 : i + 1]
                window_mkt  = b_ret.iloc[i - window + 1 : i + 1]
                
                if len(window_port) < min_obs:
                    betas.append(np.nan)
                else:
                    # OLS: port_return = alpha + beta * market_return + error
                    X = sm.add_constant(window_mkt.values)      # add intercept (alpha)
                    y = window_port.values
                    
                    try:
                        model = sm.OLS(y, X).fit()
                        beta = model.params[1]                  # slope = beta
                        betas.append(beta)
                    except:
                        betas.append(np.nan)
                
                dates.append(p_ret.index[i])
            
            return pd.Series(betas, index=dates, name='rolling_beta')
        
        rb = rolling_beta_ols(p_ret, b_ret)
        if rb.dropna().empty:
            st.caption("Not enough data for 252-day rolling Beta.")
        else:
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.plot(rb.index, rb.values, color=db.ACCENT4, linewidth=1.5)
            ax.axhline(1, color='#555', linewidth=0.8, linestyle='--')
            ax.axhline(0, color='#333', linewidth=0.5)
            ax.set_ylabel("Beta")
            apply_style(fig, [ax])
            st.pyplot(fig)
            plt.close("all")

        # Scatter
        st.markdown('<div class="section-header">Excess Returns Scatter</div>', unsafe_allow_html=True)
        _sc_size = 7
        fig, ax = plt.subplots(figsize=(_sc_size, _sc_size))
        ax.scatter(b_ret.values * 100, p_ret_c.values * 100,
                   color=db.ACCENT, alpha=0.5, s=4, linewidths=0)
        xlim = max(abs(b_ret.values).max() * 100, 1)
        x_line = np.linspace(-xlim, xlim, 100)
        b_val  = m["Beta"]
        a_val  = (np.mean(p_ret_c.values) - b_val * np.mean(b_ret.values)) * 100
        ax.plot(x_line, b_val * x_line + a_val, color=db.ACCENT2, linewidth=1.5,
                label=f"Regression (β={b_val:.2f})", alpha=0.4)
        ax.axhline(0, color='#505050', linewidth=1, alpha=0.5)
        ax.axvline(0, color='#505050', linewidth=1, alpha=0.5)
        ax.set_xlabel(f"{benchmark_ticker} Daily Return (%)")
        ax.set_ylabel("Portfolio Daily Return")
        ax.set_title("Portfolio vs Benchmark")
        leg = ax.legend(fontsize=10, loc='upper left', framealpha=0.5)
        for text in leg.get_texts():
            text.set_alpha(0.75)
        ax.set_xlim(-xlim, xlim)
        ax.set_ylim(-xlim, xlim)
        pct_axis(ax, decimals=1)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        apply_style(fig, [ax])
        ax.grid(True, color='#505050', linewidth=0.5, alpha=0.5)
        fig.tight_layout()
        _sc_gap = max(1, 12 - _sc_size)
        _col = st.columns([_sc_size, _sc_gap])[0]
        with _col: st.pyplot(fig, use_container_width=False)
        plt.close("all")


# ── Shared pie chart color helpers & draw_pie (used in Allocation + Optimization) ──
def _get_group_color(label):
    l = label.lower()
    for keywords, color in db.ASSET_GROUP_COLORS:
        if any(kw in l for kw in keywords):
            return color
    return '#7f8c8d'

def get_ticker_colors_global(ticker_list, asset_classes_dict, sizes):
    """Each ticker gets its own shade derived from its asset group color."""
    groups = {}
    for t in ticker_list:
        ac_label = asset_classes_dict.get(t, '')
        color = _get_group_color(ac_label)
        if color == '#7f8c8d':
            color = _get_group_color(t)
        groups.setdefault(color, []).append(t)
    ticker_color_map = {}
    for base_hex, group_tickers in groups.items():
        r = int(base_hex[1:3], 16) / 255
        g = int(base_hex[3:5], 16) / 255
        b = int(base_hex[5:7], 16) / 255
        h, s, v = _colorsys.rgb_to_hsv(r, g, b)
        n = len(group_tickers)
        group_tickers_sorted = sorted(group_tickers, key=lambda t: ticker_list.index(t))
        weights_in_group = [sizes[ticker_list.index(t)] for t in group_tickers_sorted]
        group_tickers_sorted = [t for _, t in sorted(
            zip(weights_in_group, group_tickers_sorted), reverse=True)]
        for idx, t in enumerate(group_tickers_sorted):
            if n == 1:
                new_h, new_s, new_v = h, s, v
            else:
                new_h = h
                new_s = max(0.25, s - idx * 0.20)
                new_v = min(1.0, v + idx * 0.22)
            nr, ng, nb = _colorsys.hsv_to_rgb(new_h, new_s, new_v)
            ticker_color_map[t] = '#{:02x}{:02x}{:02x}'.format(
                int(nr * 255), int(ng * 255), int(nb * 255))
    return [ticker_color_map[t] for t in ticker_list]

def draw_pie(ax, sizes, labels, colors, title, filter_zero=False):
    """Draw a pie chart with labels+percentages in a legend, no overlapping text.
    If filter_zero=True, slices with 0% weight are excluded from the legend."""
    if filter_zero:
        filtered = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0.0005]
        if filtered:
            sizes, labels, colors = zip(*filtered)
            sizes, labels, colors = list(sizes), list(labels), list(colors)
    wedges, _ = ax.pie(
        sizes,
        colors=colors,
        startangle=140,
        wedgeprops=dict(linewidth=0.5 if len(sizes) > 1 else 0, edgecolor="#0f0f0f"),
        explode=[0.00] * len(sizes),
    )
    legend_labels = [f"{lbl}  {sz:.1%}" for lbl, sz in zip(labels, sizes)]
    ax.legend(
        wedges, legend_labels,
        loc='center left',
        bbox_to_anchor=(-0.45, 0.5),
        fontsize=9,
        frameon=True,
        facecolor=db.PLOT_BG,
        edgecolor=db.DARKER,
        labelcolor=db.PLOT_FG,
    )
    ax.set_title(title, color=db.PLOT_FG, pad=12, loc='center')
    ax.set_facecolor(db.PLOT_BG)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – DISTRIBUTION  (helpers defined at module level so cache works)
# ══════════════════════════════════════════════════════════════════════════════

def _normalise_sectors(d):
    out = {}
    for k, v in d.items():
        canon = db._SECTOR_NORM.get(k, k)
        out[canon] = out.get(canon, 0) + v
    return out

@st.cache_data(show_spinner=False, ttl=86400)
def _get_etf_data_cached(ticker):
    """
    Priority:
    1. Hardcoded built-in template (if ticker is known) — always wins, guaranteed correct
    2. yfinance sectorWeightings/countryWeightings — for unknown tickers only
    Does NOT check session_state overrides.
    """
    # 1. Known ticker → use hardcoded template, skip yfinance entirely
    tmpl = db._TICKER_TO_TEMPLATE.get(ticker.upper())
    if tmpl:
        return (db._KNOWN_ETF_COUNTRIES.get(tmpl, {}),
                db._KNOWN_ETF_SECTORS.get(tmpl, {}),
                None, None)

    # 2. Unknown ticker → try yfinance
    try:
        info    = yf.Ticker(ticker).info
        country = info.get("country")
        sector  = None
        raw_sec = info.get("sectorWeightings") or []
        raw_cty = info.get("countryWeightings") or []
        sec_w   = {}
        for d in raw_sec:
            for k, v in d.items():
                sec_w[k.title()] = sec_w.get(k.title(), 0) + float(v)
        cty_w   = {}
        for d in raw_cty:
            for k, v in d.items():
                cty_w[k.title()] = cty_w.get(k.title(), 0) + float(v)
        if sec_w or cty_w or country or sector:
            return cty_w, _normalise_sectors(sec_w), country, sector
    except Exception:
        pass

    return {}, {}, None, None

def _get_etf_data(ticker):
    """
    Returns (country_weights_dict, sector_weights_dict, home_country, home_sector).
    Priority: Ticker Database (user-saved) → yfinance → built-in template.
    """
    key = ticker.upper()
    custom = st.session_state.get("etf_custom_db", {})
    if key in custom:
        entry = custom[key]
        return entry.get("countries", {}), entry.get("sectors", {}), None, None
    return _get_etf_data_cached(ticker)

def _agg_exposure(tickers_list, weights_list, idx):
    """Aggregate country (idx=0) or sector (idx=1) weighted exposure."""
    totals = defaultdict(float)
    per_ticker = {}
    for t, w in zip(tickers_list, weights_list):
        cty_w, sec_w, country, sector = _get_etf_data(t)
        breakdown = [cty_w, sec_w][idx]
        fallback  = [country, sector][idx]
        if breakdown:
            for k, v in breakdown.items():
                totals[k] += v * w
            per_ticker[t] = breakdown
        elif fallback:
            totals[fallback] += w
            per_ticker[t] = {fallback: 1.0}
        else:
            per_ticker[t] = {}
    if not totals:
        return pd.Series(dtype=float), {}
    s = pd.Series(totals).sort_values(ascending=False)
    return s / s.sum(), per_ticker

# ── Plotly chart helpers ──────────────────────────────────────────────────────
def _plotly_country_bar(series):
    import plotly.graph_objects as go
    top = series.head(20)
    fig = go.Figure(go.Bar(
        x=top.values * 100,
        y=top.index,
        orientation='h',
        marker_color=db.ACCENT3,
        text=[f"{v*100:.1f}%" for v in top.values],
        textposition='outside',
    ))
    fig.update_layout(
        title="   Country Weight",
        xaxis=dict(title="Weight", ticksuffix="%"),
        yaxis=dict(autorange="reversed"),
        template="plotly_dark",
        paper_bgcolor=db.PLOT_BG,
        plot_bgcolor=db.PLOT_BG,
        font=dict(color=db.PLOT_FG),
        height=max(350, len(top) * 28 + 80),
        margin=dict(l=140, r=80, t=50, b=40),
    )
    return fig

def _plotly_choropleth(series):
    import plotly.graph_objects as go
    iso3   = [db._COUNTRY_ISO3.get(c, None) for c in series.index]
    mask   = [i is not None for i in iso3]
    vals   = [v * 100 for v, m in zip(series.values, mask) if m]
    codes  = [c for c, m in zip(iso3, mask) if m]
    names  = [n for n, m in zip(series.index, mask) if m]
    fig = go.Figure(go.Choropleth(
        locations=codes,
        z=vals,
        text=names,
        colorscale=[[0, "#C1CCDA"], [0.4, "#3E5980"], [1, "#092544"]],
        colorbar=dict(title="Weight %", ticksuffix="%",
                      bgcolor=db.PLOT_BG, tickfont=dict(color=db.PLOT_FG)),
        hovertemplate="%{text}: %{z:.2f}%<extra></extra>",
        marker_line_color="#333",
        marker_line_width=0.5,
    ))
    fig.update_layout(
        geo=dict(
            showframe=False, showcoastlines=True,
            coastlinecolor="#333",
            showland=True,  landcolor=db.PLOT_BG,
            showocean=True, oceancolor="#0f0f0f",
            showcountries=True, countrycolor="#333",
            bgcolor=db.PLOT_BG,
            projection_type="natural earth",
        ),
        paper_bgcolor=db.PLOT_BG,
        font=dict(color=db.PLOT_FG),
        margin=dict(l=0, r=0, t=10, b=10),
        height=500,
    )
    return fig

def _plotly_sector_bar(series, ticker_detail=None):
    import plotly.graph_objects as go
    colors = [db.SECTOR_COLORS.get(s, db.ACCENT) for s in series.index]
    fig = go.Figure(go.Bar(
        x=series.values * 100,
        y=series.index,
        orientation='h',
        marker_color=colors,
        text=[f"{v*100:.1f}%" for v in series.values],
        textposition='outside',
    ))
    fig.update_layout(
        title="   Sector Weight",
        xaxis=dict(title="Weight (%)", ticksuffix="%", range=[0, (series.values.max() * 100) + 2.5]),
        yaxis=dict(autorange="reversed"),
        template="plotly_dark",
        paper_bgcolor=db.PLOT_BG,
        plot_bgcolor=db.PLOT_BG,
        font=dict(color=db.PLOT_FG),
        height=max(480, len(series) * 32 + 80),
        margin=dict(l=150, r=50, t=50, b=40),
    )
    return fig

def _plotly_sector_sunburst(series, ticker_detail, ticker_weights):
    """
    series: pd.Series {sector: portfolio_weight}
    ticker_detail: {ticker: {sector: raw_sector_fraction}}  (sums to ~1 per ticker)
    ticker_weights: dict {ticker: portfolio_weight}
    Uses branchvalues='remainder' so parent arc = sum of children (no spikes).
    """
    import plotly.graph_objects as go
    ids, labels, parents, vals, colors_sb = [], [], [], [], []

    for sector, sv in series.items():
        # Parent node — value=0 so arc = sum of children (remainder mode)
        ids.append(sector)
        labels.append(f"{sector}<br>{sv*100:.1f}%")
        parents.append("")
        vals.append(0.0)
        colors_sb.append(db.SECTOR_COLORS.get(sector, db.ACCENT))

        for t, breakdown in ticker_detail.items():
            total_t = sum(breakdown.values()) or 1
            sec_frac = breakdown.get(sector, 0) / total_t   # fraction of THIS ticker in this sector
            port_w   = ticker_weights.get(t, 0)             # this ticker's portfolio weight
            child_val = sec_frac * port_w                   # actual portfolio contribution
            if child_val > 0:
                node_id = f"{sector}|{t}"
                ids.append(node_id)
                labels.append(f"{t}<br>{child_val*100:.1f}%")
                parents.append(sector)
                vals.append(float(child_val))
                colors_sb.append(db.SECTOR_COLORS.get(sector, db.ACCENT))

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=vals,
        marker=dict(colors=colors_sb, line=dict(width=1.0, color="#0f0f0f")),
        hovertemplate="%{label}<extra></extra>",
        branchvalues="remainder",
        textfont=dict(size=11),
        insidetextorientation="radial",
    ))
    fig.update_layout(
        paper_bgcolor=db.PLOT_BG,
        font=dict(color=db.PLOT_FG),
        margin=dict(l=10, r=10, t=10, b=10),
        height=480,
    )
    return fig

with tab_alloc:
    dist_subtabs = st.tabs(["Allocations", "Country Distribution", "Sector Distribution", "Ticker Database"])

    # ── Subtab 1: Allocations ────────────────────────────────────────────────
    with dist_subtabs[0]:
        st.markdown('<div class="section-header">Portfolio Weights</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ticker_colors = get_ticker_colors_global(tickers, asset_classes, weights_raw)
            fig, ax = plt.subplots(figsize=(6, 5))
            fig.patch.set_facecolor(db.PLOT_BG)
            draw_pie(ax, weights_raw, tickers, ticker_colors, "By Ticker")
            fig.subplots_adjust(left=0.35)
            st.pyplot(fig)
            plt.close("all")
        with col2:
            class_weights = defaultdict(float)
            for ticker, weight in portfolio.items():
                if ticker in asset_classes:
                    class_weights[asset_classes[ticker]] += weight
            if class_weights:
                labels_ac = list(class_weights.keys())
                sizes_ac  = list(class_weights.values())
                ac_colors = [_get_group_color(l) for l in labels_ac]
                fig, ax = plt.subplots(figsize=(6, 5))
                fig.patch.set_facecolor(db.PLOT_BG)
                draw_pie(ax, sizes_ac, labels_ac, ac_colors, "By Asset Class")
                fig.subplots_adjust(left=0.35)
                st.pyplot(fig)
                plt.close("all")

        st.markdown('<div class="section-header">Holdings</div>', unsafe_allow_html=True)
        holdings_df = pd.DataFrame({
            "Ticker":       tickers,
            "Weight":       [f"{w:.2%}" for w in weights_raw],
            "Asset Class":  [asset_classes.get(t, "———") for t in tickers],
        })
        st.dataframe(holdings_df, width='stretch', hide_index=True)

        st.markdown('<div class="section-header">Individual Asset Performance</div>', unsafe_allow_html=True)
        ind_rows = []
        for t in available:
            r = returns[t].dropna()
            if len(r) == 0:
                continue
            ind_rows.append({
                "Ticker":       t,
                "Annual Return": f"{ann_return(r):.2%}",
                "Volatility":    f"{ann_vol(r):.2%}",
                "Sharpe":        f"{sharpe(r):.3f}",
                "Max DD":        f"{max_drawdown(r):.2%}",
            })
        if ind_rows:
            st.dataframe(pd.DataFrame(ind_rows), width='stretch', hide_index=True)

    # ── Subtab 2: Country Distribution ───────────────────────────────────────
    with dist_subtabs[1]:
        st.markdown('<div class="section-header">Country Distribution</div>', unsafe_allow_html=True)

        with st.spinner("Calculating country exposure..."):
            country_exp, country_per_ticker = _agg_exposure(available, list(w_aligned), 0)

        if country_exp.empty:
            st.warning("Could not determine country exposure. Check the ticker database.")
        else:
            threshold = 0.003
            # 1. Filter countries above threshold and remove potential "Other" duplicates
            main_c = country_exp[country_exp >= threshold].copy()
            other_w = country_exp[country_exp < threshold].sum()

            # 2. Merge small countries into "Other" category
            if other_w > 0.001:
                if "Other" in main_c.index:
                    main_c["Other"] += other_w
                else:
                    main_c = pd.concat([main_c, pd.Series({"Other": other_w})])

            # 3. Sort by weight descending, keeping "Other" at the end
            if "Other" in main_c.index:
                other_val = main_c["Other"]
                # Temporarily drop Other, sort the rest, then append Other at the end
                main_c = main_c.drop("Other").sort_values(ascending=False)
                main_c["Other"] = other_val
            else:
                main_c = main_c.sort_values(ascending=False)

            # Choropleth map
            st.plotly_chart(_plotly_choropleth(main_c), width='stretch', key="country_map_unique")

            # Bar
            st.plotly_chart(_plotly_country_bar(main_c), width='stretch', key="country_bar_unique")


    # ── Subtab 3: Sector Distribution ─────────────────────────────────────────
    with dist_subtabs[2]:
        st.markdown('<div class="section-header">Sector Distribution</div>', unsafe_allow_html=True)

        with st.spinner("Calculating sector exposure..."):
            sector_exp, sector_per_ticker = _agg_exposure(available, list(w_aligned), 1)

        if sector_exp.empty:
            st.warning("Could not determine sector exposure. Check the ticker database.")
        else:
            threshold = 0.003
            main_s  = sector_exp[sector_exp >= threshold]
            other_w = sector_exp[sector_exp < threshold].sum()
            if other_w > 0.001:
                main_s = pd.concat([main_s, pd.Series({"Other": other_w})])

            # Bar + Sunburst side by side
            s_bar, s_sun = st.columns([3, 2])
            with s_bar:
                st.plotly_chart(_plotly_sector_bar(main_s), width='stretch', key="sector_bar_unique")
            with s_sun:
                _ticker_weights_map = dict(zip(available, list(w_aligned)))
                st.plotly_chart(
                    _plotly_sector_sunburst(main_s, sector_per_ticker, _ticker_weights_map),
                    width='stretch', key="sector_sunburst_unique",
                )

            st.markdown('<div class="section-header">Sector Weights Table</div>', unsafe_allow_html=True)
            all_sectors = list(main_s.index)
            tbl = {
                "Sector":    all_sectors,
                "Portfolio": [f"{main_s.get(s, 0)*100:.1f}%" for s in all_sectors],
            }
            for t in available:
                detail  = sector_per_ticker.get(t, {})
                total_t = sum(detail.values()) or 1
                tbl[t]  = [f"{detail.get(s, 0) / total_t * 100:.1f}%" for s in all_sectors]
            st.dataframe(pd.DataFrame(tbl), width='stretch', hide_index=True)

    # __ Subtab 4: Ticker Database ______________________________________________
    with dist_subtabs[3]:
        if "etf_custom_db" not in st.session_state:
            # Load from config file if present, else empty dict
            st.session_state["etf_custom_db"] = _cfg.get("etf_custom_db", {})

        def _parse_weights(df, key_col):
            result = {}
            for _, row in df.iterrows():
                k = str(row.get(key_col, "")).strip()
                w = float(row.get("Weight %", 0) or 0)
                if k and w > 0:
                    result[k] = w / 100.0
            total = sum(result.values())
            if total > 0:
                result = {k: v / total for k, v in result.items()}
            return result

        def _build_initial_df(ticker, kind):
            """
            Build initial DataFrame for the editor.
            kind: 'countries' or 'sectors'
            Uses: custom db -> yfinance/built-in cache.
            Stored in session_state so editor doesn't reset on every Streamlit rerun.
            Only refreshed when Save or Clear is pressed.
            """
            ss_key = f"etf_init_{kind}_{ticker.upper()}"
            if ss_key in st.session_state:
                return st.session_state[ss_key]
            custom = st.session_state["etf_custom_db"].get(ticker.upper(), {})
            src = custom.get(kind) if custom else None
            if not src:
                cty_w, sec_w, country, sector = _get_etf_data_cached(ticker)
                if kind == "countries":
                    src = cty_w or ({country: 1.0} if country else {})
                else:
                    sec_w = _normalise_sectors(sec_w)
                    src = sec_w or ({sector: 1.0} if sector else {})
            if kind == "countries":
                rows = [{"Country": k, "Weight %": round(v * 100, 1)}
                        for k, v in sorted(src.items(), key=lambda x: -x[1])]
                if not rows:
                    rows = [{"Country": "", "Weight %": 0.0}]
                df = pd.DataFrame(rows)
            else:
                rows = [{"Sector": k, "Weight %": round(v * 100, 1)}
                        for k, v in sorted(src.items(), key=lambda x: -x[1])]
                if not rows:
                    rows = [{"Sector": "", "Weight %": 0.0}]
                df = pd.DataFrame(rows)
            st.session_state[ss_key] = df
            return df

        def _reset_editor_cache(ticker):
            """Delete the cached initial DataFrames so they rebuild on next render."""
            tkey = ticker.upper()
            for kind in ("countries", "sectors"):
                k = f"etf_init_{kind}_{tkey}"
                if k in st.session_state:
                    del st.session_state[k]

        def _resolve_editor_df(ticker, kind):
            """
            Return a proper DataFrame from the data_editor state.
            Streamlit stores data_editor state as a dict of changes
            {"edited_rows": {...}, "added_rows": [...], "deleted_rows": [...]},
            not as a DataFrame. Apply those changes to the initial df.
            """
            tkey = ticker.upper()
            key = f"etf_cty_{tkey}" if kind == "countries" else f"etf_sec_{tkey}"
            initial_df = _build_initial_df(ticker, kind)
            state = st.session_state.get(key)
            if state is None or isinstance(state, pd.DataFrame):
                return state if isinstance(state, pd.DataFrame) else initial_df
            if isinstance(state, dict):
                df = initial_df.copy()
                for row_idx_str, changes in state.get("edited_rows", {}).items():
                    row_idx = int(row_idx_str)
                    for col, val in changes.items():
                        if row_idx < len(df):
                            df.at[row_idx, col] = val
                for row in state.get("added_rows", []):
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                deleted = sorted(state.get("deleted_rows", []), reverse=True)
                for row_idx in deleted:
                    if row_idx < len(df):
                        df = df.drop(index=row_idx).reset_index(drop=True)
                return df
            return initial_df

        # ── Single Save All button ────────────────────────────────────────────
        _save_col, _gap_col = st.columns([2, 10])
        with _save_col:
            if st.button("Save All", key="etf_save_all", type="primary", width=200):
                _saved = []
                for _t in available:
                    _tkey = _t.upper()
                    _cty_df = _resolve_editor_df(_t, "countries")
                    _sec_df = _resolve_editor_df(_t, "sectors")
                    _cty_parsed = _parse_weights(_cty_df, "Country")
                    _sec_parsed = _parse_weights(_sec_df, "Sector")
                    if _cty_parsed or _sec_parsed:
                        _entry = {}
                        if _cty_parsed:
                            _entry["countries"] = _cty_parsed
                        if _sec_parsed:
                            _entry["sectors"] = _normalise_sectors(_sec_parsed)
                        st.session_state["etf_custom_db"][_tkey] = _entry
                        _reset_editor_cache(_t)
                        _saved.append(_t)
                if _saved:
                    st.success(f"Saved: {', '.join(_saved)}")
                    st.rerun(scope="app")
                else:
                    st.warning("No data to save — add at least one country or sector weight.")

        def _render_ticker_editor(ticker):
            tkey = ticker.upper()
            in_custom = tkey in st.session_state["etf_custom_db"]

            hdr_col, _gap, clr_col = st.columns([4, 6, 2])
            with hdr_col:
                st.markdown(
                    f'<div class="section-header">{ticker}</div>',
                    unsafe_allow_html=True,
                )
            with clr_col:
                if st.button(f"Clear {ticker}", key=f"etf_clr_{tkey}", width=200, disabled=not in_custom):
                    del st.session_state["etf_custom_db"][tkey]
                    _reset_editor_cache(ticker)
                    for ek in (f"etf_cty_{tkey}", f"etf_sec_{tkey}"):
                        if ek in st.session_state:
                            del st.session_state[ek]
                    st.rerun(scope="app")

            col_cty, col_sec = st.columns(2)

            with col_cty:
                st.caption("Country weights")
                st.data_editor(
                    _build_initial_df(ticker, "countries"),
                    num_rows="dynamic",
                    width='stretch',
                    key=f"etf_cty_{tkey}",
                    column_config={
                        "Country":  st.column_config.TextColumn("Country", width="medium"),
                        "Weight %": st.column_config.NumberColumn("Weight %", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"),
                    },
                    hide_index=True,
                )

            with col_sec:
                st.caption("Sector weights")
                st.data_editor(
                    _build_initial_df(ticker, "sectors"),
                    num_rows="dynamic",
                    width='stretch',
                    key=f"etf_sec_{tkey}",
                    column_config={
                        "Sector":   st.column_config.SelectboxColumn("Sector", options=db._SECTOR_OPTIONS, width="medium"),
                        "Weight %": st.column_config.NumberColumn("Weight %", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"),
                    },
                    hide_index=True,
                )

            st.write("---")

        for _t in available:
            _render_ticker_editor(_t)

gc.collect()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 – CORRELATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_corr:

        @st.fragment
        def render_correlations():
            st.markdown('<div class="section-header">Correlation Matrix</div>', unsafe_allow_html=True)
            cm_size = max(7, len(tickers))  # chart size in inches (square)

            custom_cmap = LinearSegmentedColormap.from_list(
                "coolwarm_white",
                [
                    (0.0,   "#3b4cc0"),      # -1    sininen
                    (0.5,   "#f7f7f7"),      #  0    neutraali
                    (0.9999999, "#b40426"),  #  0.99 punainen
                    (1.0,   "#333333"),      #  1    harmaa
                ]
            )

            monthly_r = (1 + returns).resample('ME').prod() - 1
            corr_mat  = round(monthly_r.corr(), 2)

            annot = corr_mat.copy().astype(object)
            for i, ticker in enumerate(corr_mat.index):
                annot.iloc[i, i] = f"{ticker}\n1.00"

            fig, ax = plt.subplots(figsize=(cm_size + 1.3, cm_size))
            sns.heatmap(corr_mat, annot=annot, fmt="", cmap=custom_cmap,
                        vmin=-1, vmax=1, linewidths=0.5, linecolor='#0f0f0f',
                        annot_kws={'size': 13}, ax=ax,
                        cbar_kws={'label': 'Correlation'})
            ax.set_title("Monthly Return Correlation")
            ax.set_aspect('equal')
            ax.set_xlabel("")
            ax.set_ylabel("")
            apply_style(fig, [ax])
            fig.tight_layout()
            _cm_gap = max(1, 12 - cm_size)
            _col = st.columns([cm_size, _cm_gap])[0]
            with _col: st.pyplot(fig, use_container_width=False)
            plt.close("all")

            if len(tickers) >= 2:
                st.markdown('<div class="section-header">Rolling Correlation</div>', unsafe_allow_html=True)
                default_window = min(36, len(monthly_r) - 1)
                window_size = st.slider("Rolling window (months)", 6, 60, max(6, default_window))

                if len(monthly_r) - 1 < window_size:
                    st.warning(f"Only {len(monthly_r) - 1} months of data available.")
                else:
                    fig, ax = plt.subplots(figsize=(12, 4))
                    color_cycle = [db.ACCENT, db.ACCENT3, db.ACCENT4, db.ACCENT2, '#b19cd9']

                    # Track the first valid data point (excluding NaN values)
                    first_valid_date = None

                    for i, (t1, t2) in enumerate(combinations(available, 2)):
                        rc = monthly_r[t1].rolling(window_size).corr(monthly_r[t2])

                        # Update first valid date
                        if first_valid_date is None:
                            first_valid_date = rc.dropna().index.min()

                        ax.plot(rc, label=f"{t1} vs {t2}",
                                linewidth=2, color=color_cycle[i % len(color_cycle)])

                    # MARGINAALIEN KORJAUS:
                    # Left edge aligned to first computed correlation
                    if first_valid_date and pd.notnull(first_valid_date):
                        date_max = monthly_r.index.max()
                        if pd.notnull(date_max) and date_max > first_valid_date:
                            ax.set_xlim(left=first_valid_date, right=date_max)

                    ax.axhline(0,  color='#555', linewidth=0.5)
                    ax.axhline(1,  color='#333', linewidth=0.5, linestyle='--')
                    ax.axhline(-1, color='#333', linewidth=0.5, linestyle='--')
                    ax.set_ylim(-1.05, 1.05)
                    ax.set_ylabel("Correlation")
                    ax.set_title(f"{window_size}-Month Rolling Correlation")
                    leg = ax.legend(fontsize=6, loc='best', framealpha=0.5)
                    for text in leg.get_texts():
                        text.set_alpha(0.75)
                    for line in leg.get_lines():
                        line.set_alpha(0.75)
                    apply_style(fig, [ax])
                    st.pyplot(fig)
                    plt.close("all")

        render_correlations()

gc.collect()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 – FI FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab_fi:
        @st.fragment
        def render_fi():
            st.markdown('<div class="section-header">Financial Independence Forecast Settings</div>', unsafe_allow_html=True)

            # ── Spend targets ───────────────────────────────────────────────────
            col1, col2, col3 = st.columns(3)
            with col1:
                lean_fi = st.number_input("Lean FI annual spend ($k)",  10, 500, 36)
            with col2:
                safe_fi = st.number_input("Safe FI annual spend ($k)",  10, 500, 50)
            with col3:
                cozy_fi = st.number_input("Cozy FI annual spend ($k)",  10, 500, 100)

            # ── Withdrawal start slider ─────────────────────────────────────────

            w_col1, w_col2 = st.columns([2, 1])
            with w_col1:
                _wy_options = ["Accumulation only"] + [str(v) for v in range(0, 101)]
                _wy_sel = st.select_slider(
                    "Start withdrawals after (years from today)",
                    options=_wy_options,
                    value="20",
                    help="Select 'Accumulation only' to disable withdrawals entirely (pure accumulation). Otherwise, contributions stop and spending begins from this year onward."
                )
                withdrawal_start_year = 0 if _wy_sel == "Accumulation only" else int(_wy_sel)
            with w_col2:
                total_horizon_years = st.slider(
                    "Total forecast horizon (years)",
                    min_value=max(withdrawal_start_year + 1, 1), max_value=80, value=max(40, withdrawal_start_year + 20), step=1
                )
            st.markdown('<div class="section-header"></div>', unsafe_allow_html=True)
            no_withdrawals = _wy_sel == "Accumulation only"

            hist_return  = ann_return(p_ret)
            use_return   = custom_annualized_return if custom_annualized_return > 0 else hist_return
            return_label = f"{use_return:.1%} (historical)" if custom_annualized_return == 0 else f"{use_return:.1%} (custom)"
            monthly_ret  = (1 + use_return) ** (1/12) - 1

            if no_withdrawals:
                st.caption(
                    f"**Accumulation only** - contributing ${monthly_investment}/month for {total_horizon_years} years, "
                    f"growing at {return_label}/yr. No withdrawals."
                )
            else:
                st.caption(
                    f"**Accumulation:** years 0–{withdrawal_start_year} - contributing ${monthly_investment}/month, "
                    f"growing at {return_label}/yr   |   "
                    f"**Withdrawal:** years {withdrawal_start_year}–{total_horizon_years} - contributions stop, spending begins"
                )

            total_months         = total_horizon_years * 12
            # If withdrawal_start_year == 0, set start beyond total so withdrawal phase never triggers
            withdrawal_start_mo  = total_months if no_withdrawals else withdrawal_start_year * 12
            proj_dates           = pd.date_range(datetime.today(), periods=total_months + 1, freq='MS')

            # ── Helper: simulate one full path with two phases ──────────────────
            def simulate(annual_spend_k, deterministic=True, sig_m=0.0):
                """
                Phase 1 (accumulation):  value grows + monthly_investment added each month.
                Phase 2 (withdrawal):    value grows - monthly_withdrawal deducted, no contributions.
                Starts from current_portfolio_value (initial_investment grown through the historical period).
                Returns list of length total_months+1.
                """
                monthly_withdrawal = annual_spend_k / 12  # $k per month
                values = [current_portfolio_value / 1000]
                for mo in range(total_months):
                    prev = values[-1]
                    r = monthly_ret if deterministic else np.random.normal(monthly_ret, sig_m)
                    grown = max(prev, 0) * (1 + r)   # can't grow negative principal
                    if mo < withdrawal_start_mo:
                        # Accumulation phase: add contribution
                        next_val = grown + monthly_investment / 1000
                    else:
                        # Withdrawal phase: deduct spending
                        next_val = grown - monthly_withdrawal
                    values.append(next_val)
                return values

            # ── FI target NW for each spend level ──────────────────────────────
            # Target = annual_spend / SWR  (only meaningful when SWR > 0)
            has_swr = safe_withdrawal_rate > 0

            scenarios = [
                (lean_fi, "Lean FI",  db.ACCENT3),
                (safe_fi, "Safe FI",  db.ACCENT),
                (cozy_fi, "Cozy FI",  db.ACCENT4),
            ]

            # ── Main chart ──────────────────────────────────────────────────────
            fig, ax = plt.subplots(figsize=(12, 5))

            # Shade accumulation vs withdrawal regions
            acc_end_date = proj_dates[withdrawal_start_mo] if not no_withdrawals else proj_dates[-1]
            ax.axvspan(proj_dates[0], acc_end_date, alpha=0.04, color=db.ACCENT, zorder=0)
            if not no_withdrawals:
                ax.axvspan(acc_end_date, proj_dates[-1], alpha=0.04, color=db.ACCENT2, zorder=0)
                ax.axvline(acc_end_date, color="white", linewidth=1.2, linestyle=':', alpha=0.6)

            # Axis formatter: values are in $k, display as fmt_dollar units
            fi_dollar_fmt = mticker.FuncFormatter(lambda x, _: fmt_dollar(x * 1000))

            # Pre-simulate all scenarios to determine Y axis range from data only
            all_sim_data = {}
            for spend_k, label, color in scenarios:
                all_sim_data[(spend_k, label, color)] = simulate(spend_k)

            # Set Y axis limits based on simulated data (not target lines)
            all_vals_flat = [v for vals in all_sim_data.values() for v in vals]
            y_max_data = max(v for v in all_vals_flat if np.isfinite(v))
            y_min_data = min(v for v in all_vals_flat if np.isfinite(v))
            y_margin   = (y_max_data - y_min_data) * 0.08
            y_top      = y_max_data + y_margin
            y_bot      = min(y_min_data - y_margin, -y_margin * 0.5)
            ax.set_ylim(y_bot, y_top)

            for spend_k, label, color in scenarios:
                vals   = all_sim_data[(spend_k, label, color)]
                series = pd.Series(vals, index=proj_dates)

                # Accumulation portion (solid)
                ax.plot(proj_dates[:withdrawal_start_mo + 1],
                        [v for v in vals[:withdrawal_start_mo + 1]],
                        color=color, linewidth=2)

                # Withdrawal portion (dashed)
                ax.plot(proj_dates[withdrawal_start_mo:],
                        [v for v in vals[withdrawal_start_mo:]],
                        color=color, linewidth=2, linestyle='--',
                        label=f"{label} (${spend_k}k/yr spend)")

                # Mark if/when portfolio is exhausted
                withdrawal_vals = vals[withdrawal_start_mo:]
                exhausted = [i for i, v in enumerate(withdrawal_vals) if v <= 0]
                if exhausted:
                    ex_mo   = withdrawal_start_mo + exhausted[0]
                    ex_year = ex_mo / 12
                    ax.scatter([proj_dates[ex_mo]], [0],
                               color=color, s=80, zorder=6, marker='X')
                    ax.annotate(f"Exhausted\nyr {ex_year:.0f}",
                                xy=(proj_dates[ex_mo], 0),
                                xytext=(0, 18), textcoords='offset points',
                                fontsize=7, color=color, ha='center')
                else:
                    final_val = vals[-1]
                    ax.scatter([proj_dates[-1]], [final_val],
                               color=color, s=50, zorder=6)

                # FI required NW target line (only if SWR set)
                if has_swr:
                    target = spend_k / safe_withdrawal_rate
                    legend_label = f"{label} target: {fmt_dollar((target) * 1000)}"
                    if target <= y_top:
                        # Target is within chart range - draw horizontal line
                        ax.axhline(target, color=color, linewidth=0.8, linestyle=':',
                                   alpha=0.5, label=legend_label)
                        # Mark first crossing during accumulation
                        acc_series = series.iloc[:withdrawal_start_mo + 1]
                        cross = acc_series[acc_series >= target]
                        if not cross.empty:
                            ax.scatter([cross.index[0]], [cross.iloc[0]],
                                       color=color, s=60, zorder=5, marker='*',
                                       edgecolors='white', linewidth=0.5)
                    else:
                        # Target above chart - invisible proxy so it still appears in legend
                        ax.plot([], [], color=color, linewidth=0.8, linestyle=':',
                                alpha=0.5, label=legend_label)

            ax.axhline(0, color='white', linewidth=0.6, alpha=0.3)
            ax.yaxis.set_major_formatter(fi_dollar_fmt)
            ax.set_ylabel("Net Worth")
            ax.set_title(
                f"FI Forecast - {return_label} return  |  "
                f"${monthly_investment}/mo contribution until yr {withdrawal_start_year}  |  "
                f"SWR {safe_withdrawal_rate:.1%}" if has_swr else
                f"FI Forecast - {return_label} return  |  "
                f"${monthly_investment}/mo contribution until yr {withdrawal_start_year}"
            )
            ax.legend(fontsize=9, loc='upper left', framealpha=0.5)
            apply_style(fig, [ax])

            # Now annotate the withdrawal start line after axes are scaled
            ylims = ax.get_ylim()
            if not no_withdrawals:
                ax.text(acc_end_date, ylims[1] * 0.97,
                        "← accumulation ", fontsize=8, color="#4caf50",
                        alpha=0.9, va='top', ha='right')
                ax.text(acc_end_date, ylims[1] * 0.97,
                        " withdrawal →", fontsize=8, color="#ef5350",
                        alpha=0.9, va='top', ha='left')
            ax.margins(x=0)
            st.pyplot(fig)
            plt.close("all")

            # ── FI Summary table ────────────────────────────────────────────────
            st.markdown('<div class="section-header">FI Goals Summary</div>', unsafe_allow_html=True)
            st.caption(f"Forecast starts from current portfolio value: {disp_sym}{current_portfolio_value_disp:,.0f} ({portfolio_native_currency} {initial_investment_native:,.0f} invested from {start_date}, grown at historical returns)")

            fi_rows = []
            for spend_k, label, _ in scenarios:
                vals    = simulate(spend_k)
                series  = pd.Series(vals, index=proj_dates)

                # NW at withdrawal start
                nw_at_retirement = vals[withdrawal_start_mo]

                # Required NW via SWR
                if has_swr:
                    target      = spend_k / safe_withdrawal_rate
                    acc_series  = series.iloc[:withdrawal_start_mo + 1]
                    cross       = acc_series[acc_series >= target]
                    yrs_to_fi   = (cross.index[0] - datetime.today()).days / 365 if not cross.empty else None
                    fi_target   = fmt_dollar((target) * 1000)
                    yrs_str     = f"{yrs_to_fi:.1f}" if yrs_to_fi else f">{withdrawal_start_year}"
                else:
                    fi_target = "-"
                    yrs_str   = "-"

                # Portfolio longevity after withdrawal start
                withdrawal_vals = vals[withdrawal_start_mo:]
                exhausted = [i for i, v in enumerate(withdrawal_vals) if v <= 0]
                if exhausted:
                    longevity = f"{exhausted[0] / 12:.0f} yrs (exhausted)"
                else:
                    longevity = f"{(total_horizon_years - withdrawal_start_year)}+ yrs ({fmt_dollar((vals[-1]) * 1000)} left)"

                monthly_w = spend_k / 12
                fi_rows.append({
                    "Scenario":              label,
                    "Annual Spend":          f"${spend_k}k  (${monthly_w:.1f}k/mo)",
                    "Required NW (SWR)":     fi_target,
                    "Years to FI target":    yrs_str,
                    "NW at retirement":      fmt_dollar((nw_at_retirement) * 1000),
                    "Portfolio lasts":       longevity,
                })

            st.dataframe(pd.DataFrame(fi_rows), width='stretch', hide_index=True)

            if not has_swr:
                st.info("Set Safe Withdrawal Rate > 0 in the sidebar to see FI target NW calculations and years-to-FI.")

            # ── Monte Carlo ──────────────────────────────────────────────────────
            st.markdown('<div class="section-header">Monte Carlo Simulation</div>', unsafe_allow_html=True)

            mc_col1, mc_col2, mc_col3 = st.columns(3)
            with mc_col1:
                n_sim        = st.number_input("Number of simulations", 100, 5000, 500, step=100)
            with mc_col2:
                mc_spend     = st.selectbox("Spending scenario for MC", ["Lean FI", "Safe FI", "Cozy FI"], index=1)
            with mc_col3:
                n_paths_plot = st.number_input("Paths shown in chart", 10, 500, 100, step=10)

            mc_spend_map  = {"Lean FI": lean_fi, "Safe FI": safe_fi, "Cozy FI": cozy_fi}
            mc_spend_k    = mc_spend_map[mc_spend]
            sig_m         = ann_vol(p_ret) / np.sqrt(12)
            mc_paths      = [simulate(mc_spend_k, deterministic=False, sig_m=sig_m) for _ in range(int(n_sim))]
            mc_arr        = np.array(mc_paths)

            fig, ax = plt.subplots(figsize=(12, 5))

            ax.axvspan(proj_dates[0], acc_end_date, alpha=0.04, color=db.ACCENT, zorder=0)
            ax.axvspan(acc_end_date, proj_dates[-1], alpha=0.04, color=db.ACCENT2, zorder=0)
            ax.axvline(acc_end_date, color="white", linewidth=1.0, linestyle=':', alpha=0.5)

            for path in mc_paths[:int(n_paths_plot)]:
                ax.plot(proj_dates, path, alpha=0.04, color=db.ACCENT, linewidth=0.7)

            p10 = np.percentile(mc_arr, 10,  axis=0)
            p50 = np.percentile(mc_arr, 50,  axis=0)
            p90 = np.percentile(mc_arr, 90,  axis=0)
            ax.plot(proj_dates, p50, color=db.ACCENT,  linewidth=2,   label="Median (50th pct)")
            ax.plot(proj_dates, p10, color=db.ACCENT2, linewidth=1.5, linestyle='--', label="Pessimistic (10th pct)")
            ax.plot(proj_dates, p90, color=db.ACCENT3, linewidth=1.5, linestyle='--', label="Optimistic (90th pct)")
            ax.fill_between(proj_dates, p10, p90, alpha=0.08, color=db.ACCENT)
            ax.axhline(0, color='white', linewidth=0.6, alpha=0.3)

            # % of paths that survive (stay > 0) through full horizon
            surviving = np.sum(mc_arr[:, -1] > 0) / len(mc_paths) * 100
            exhausted_paths = np.sum(mc_arr[:, -1] <= 0)

            ax.set_ylabel("Net Worth")
            ax.set_title(
                f"{total_horizon_years}-yr Monte Carlo - {mc_spend} (${mc_spend_k}k/yr spend)  |  "
                f"Withdrawals start yr {withdrawal_start_year}  |  "
                f"Portfolio survives in {surviving:.0f}% of scenarios"
            )
            ax.legend(fontsize=9)
            ax.yaxis.set_major_formatter(fi_dollar_fmt)

            ax.margins(x=0.0015)
            apply_style(fig, [ax])
            st.pyplot(fig)
            plt.close("all")

            st.caption(
                f"At year {total_horizon_years} - "
                f"Median: {fmt_dollar((p50[-1]) * 1000)}  |  "
                f"10th pct: {fmt_dollar((p10[-1]) * 1000)}  |  "
                f"90th pct: {fmt_dollar((p90[-1]) * 1000)}  |  "
                f"Portfolio exhausted in {exhausted_paths:.0f}/{int(n_sim)} scenarios ({100-surviving:.0f}%)"
            )

        render_fi()

gc.collect()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 – OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_opt:
        from scipy.optimize import minimize

        if len(available) < 2:
            st.warning("Optimization requires at least 2 tickers.")
        else:
            # ── Helper functions using existing `returns` and `w_aligned` ──────────
            _ret_mat = returns[available]  # daily returns DataFrame

            def _port_stats(w):
                """Annual return, annual volatility, Sharpe for weight array w."""
                r   = float((_ret_mat @ w).mean() * 252)
                vol = float(np.sqrt(w @ (_ret_mat.cov() * 252).values @ w))
                sh  = (r - risk_free_rate) / vol if vol > 0 else 0.0
                return r, vol, sh

            def _neg_sharpe(w):
                r, vol, _ = _port_stats(w)
                return -(r - risk_free_rate) / vol if vol > 0 else 0.0

            def _port_vol(w):
                return _port_stats(w)[1]

            _n      = len(available)
            _bounds = [(0.0, 1.0)] * _n
            _cons   = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
            _w0     = np.ones(_n) / _n

            with st.spinner("Running optimization & efficient frontier (4 000 simulations)..."):
                # Max Sharpe
                _res_sh = minimize(_neg_sharpe, _w0, method="SLSQP", bounds=_bounds, constraints=_cons)
                _w_sh   = _res_sh.x
                _r_sh, _v_sh, _s_sh = _port_stats(_w_sh)

                # Min Volatility
                _res_mv = minimize(_port_vol, _w0, method="SLSQP", bounds=_bounds, constraints=_cons)
                _w_mv   = _res_mv.x
                _r_mv, _v_mv, _s_mv = _port_stats(_w_mv)

                # Monte Carlo efficient frontier
                _np    = 4000
                _rets  = np.zeros(_np)
                _vols  = np.zeros(_np)
                _shrps = np.zeros(_np)
                _wmat  = np.zeros((_np, _n))
                rng    = np.random.default_rng(42)
                for _i in range(_np):
                    _w = rng.dirichlet(np.ones(_n))
                    _r2, _v2, _s2 = _port_stats(_w)
                    _rets[_i]  = _r2
                    _vols[_i]  = _v2
                    _shrps[_i] = _s2
                    _wmat[_i]  = _w

            # Current portfolio stats (reuse existing variables)
            _r_cur  = float(m["Annual Return"])
            _v_cur  = float(m["Annual Volatility"])

            # Current weights dict
            _cur_w_dict = {t: float(w) for t, w in zip(available, w_aligned)}

            _sizes_cur  = [_cur_w_dict.get(t, 0) for t in available]
            _opt_colors = get_ticker_colors_global(available, asset_classes, _sizes_cur)

            opt_subtabs = st.tabs([
                "Max Sharpe",
                "Min Volatility",
                "Efficient Frontier 2D",
                "Efficient Frontier 3D",
            ])

            # ── Max Sharpe ───────────────────────────────────────────────────────
            with opt_subtabs[0]:
                st.markdown("**Best Sharpe ratio** - maximises return/risk ratio.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Expected Annual Return", f"{_r_sh:.2%}")
                c2.metric("Volatility",             f"{_v_sh:.2%}")
                c3.metric("Sharpe Ratio",           f"{_s_sh:.2f}")

                _w_df_sh = pd.DataFrame([
                    {
                        "Ticker":           t,
                        "Current weight":   f"{_cur_w_dict.get(t, 0):.1%}",
                        "Optimal weight":   f"{w:.1%}",
                        "Change":           f"{w - _cur_w_dict.get(t, 0):+.1%}",
                    }
                    for t, w in zip(available, _w_sh)
                ])
                st.dataframe(_w_df_sh, width='stretch', hide_index=True)

                _pc1, _pc2 = st.columns(2)
                with _pc1:
                    fig, ax = plt.subplots(figsize=(6, 5))
                    fig.patch.set_facecolor(db.PLOT_BG)
                    draw_pie(ax, _sizes_cur, available, _opt_colors, "Current")
                    fig.subplots_adjust(left=0.35)
                    st.pyplot(fig)
                    plt.close("all")
                with _pc2:
                    _w_sh_colors = get_ticker_colors_global(available, asset_classes, list(_w_sh))
                    fig, ax = plt.subplots(figsize=(6, 5))
                    fig.patch.set_facecolor(db.PLOT_BG)
                    draw_pie(ax, list(_w_sh), available, _w_sh_colors, "Max Sharpe", filter_zero=True)
                    fig.subplots_adjust(left=0.35)
                    st.pyplot(fig)
                    plt.close("all")

            # ── Min Volatility ───────────────────────────────────────────────────
            with opt_subtabs[1]:
                st.markdown("**Minimum risk** - suitable for conservative investors.")
                c1, c2 = st.columns(2)
                c1.metric("Expected Annual Return", f"{_r_mv:.2%}")
                c2.metric("Volatility",             f"{_v_mv:.2%}")

                _w_df_mv = pd.DataFrame([
                    {
                        "Ticker":           t,
                        "Current weight":   f"{_cur_w_dict.get(t, 0):.1%}",
                        "Optimal weight":   f"{w:.1%}",
                        "Change":           f"{w - _cur_w_dict.get(t, 0):+.1%}",
                    }
                    for t, w in zip(available, _w_mv)
                ])
                st.dataframe(_w_df_mv, width='stretch', hide_index=True)

                _pc3, _pc4 = st.columns(2)
                with _pc3:
                    fig, ax = plt.subplots(figsize=(6, 5))
                    fig.patch.set_facecolor(db.PLOT_BG)
                    draw_pie(ax, _sizes_cur, available, _opt_colors, "Current")
                    fig.subplots_adjust(left=0.35)
                    st.pyplot(fig)
                    plt.close("all")
                with _pc4:
                    _w_mv_colors = get_ticker_colors_global(available, asset_classes, list(_w_mv))
                    fig, ax = plt.subplots(figsize=(6, 5))
                    fig.patch.set_facecolor(db.PLOT_BG)
                    draw_pie(ax, list(_w_mv), available, _w_mv_colors, "Min Volatility", filter_zero=True)
                    fig.subplots_adjust(left=0.35)
                    st.pyplot(fig)
                    plt.close("all")

            # ── Efficient Frontier 2D ────────────────────────────────────────────
            with opt_subtabs[2]:
                fig, ax = plt.subplots(figsize=(10, 6))
                sc = ax.scatter(_vols * 100, _rets * 100, c=_shrps, cmap="RdYlGn",
                                alpha=0.5, s=6, linewidths=0)
                plt.colorbar(sc, ax=ax, label="Sharpe Ratio")
                # Current portfolio
                ax.scatter(_v_cur * 100, _r_cur * 100, marker="o", s=80,
                           color=db.ACCENT2, zorder=5, label="Current portfolio")
                # Max Sharpe point
                ax.scatter(_v_sh * 100, _r_sh * 100, marker="D", s=50,
                           color=db.ACCENT, zorder=5, label=f"Max Sharpe ({_s_sh:.2f})")
                # Min Vol point
                ax.scatter(_v_mv * 100, _r_mv * 100, marker="s", s=55,
                           color=db.ACCENT3, zorder=5, label=f"Min Volatility")
                ax.set_xlabel("Annual Volatility")
                ax.set_ylabel("Annual Return")
                ax.set_title("Efficient Frontier")
                ax.legend(fontsize=9, borderpad=0.6)
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
                apply_style(fig, [ax])
                fig.tight_layout()
                st.pyplot(fig)
                plt.close("all")
                st.caption(
                    "Each dot = randomly generated portfolio. Colour = Sharpe ratio. "
                    "Red star = your current portfolio. Green triangle = Max Sharpe. Blue diamond = Min Volatility."
                )

            # ── Efficient Frontier 3D ────────────────────────────────────────────
            with opt_subtabs[3]:
                import plotly.graph_objects as go
                _cur_sharpe = (_r_cur - risk_free_rate) / _v_cur if _v_cur > 0 else 0

                _fig3d = go.Figure()

                # Scatter cloud
                _fig3d.add_trace(go.Scatter3d(
                    x=_vols * 100,
                    y=_rets * 100,
                    z=_shrps,
                    mode="markers",
                    marker=dict(
                        size=2,
                        color=_shrps,
                        colorscale="RdYlGn",
                        opacity=0.5,
                        colorbar=dict(title="Sharpe", thickness=12, len=0.6),
                    ),
                    name="Simulated Portfolios",
                    hovertemplate="Vol: %{x:.1f}%<br>Return: %{y:.1f}%<br>Sharpe: %{z:.2f}<extra></extra>",
                ))

                # Current portfolio
                _fig3d.add_trace(go.Scatter3d(
                    x=[_v_cur * 100], y=[_r_cur * 100], z=[_cur_sharpe],
                    mode="markers",
                    marker=dict(size=8, color=db.ACCENT2, symbol="circle"),
                    name="Current portfolio",
                    hovertemplate=f"Current<br>Vol: {_v_cur*100:.1f}%<br>Return: {_r_cur*100:.1f}%<br>Sharpe: {_cur_sharpe:.2f}<extra></extra>",
                ))

                # Max Sharpe
                _fig3d.add_trace(go.Scatter3d(
                    x=[_v_sh * 100], y=[_r_sh * 100], z=[_s_sh],
                    mode="markers",
                    marker=dict(size=6, color=db.ACCENT, symbol="diamond"),
                    name=f"Max Sharpe ({_s_sh:.2f})",
                    hovertemplate=f"Max Sharpe<br>Vol: {_v_sh*100:.1f}%<br>Return: {_r_sh*100:.1f}%<br>Sharpe: {_s_sh:.2f}<extra></extra>",
                ))

                # Min Volatility
                _fig3d.add_trace(go.Scatter3d(
                    x=[_v_mv * 100], y=[_r_mv * 100], z=[_s_mv],
                    mode="markers",
                    marker=dict(size=8, color=db.ACCENT3, symbol="square"),
                    name="Min Volatility",
                    hovertemplate=f"Min Vol<br>Vol: {_v_mv*100:.1f}%<br>Return: {_r_mv*100:.1f}%<br>Sharpe: {_s_mv:.2f}<extra></extra>",
                ))

                _fig3d.update_layout(
                    title="            Efficient Frontier 3D",
                    scene=dict(
                        xaxis=dict(title="Volatility",  backgroundcolor=db.PLOT_BG, tickformat=".0f", ticksuffix="%", gridcolor=db.DARKER, color=db.PLOT_FG),
                        yaxis=dict(title="Return",      backgroundcolor=db.PLOT_BG, tickformat=".0f", ticksuffix="%", gridcolor=db.DARKER, color=db.PLOT_FG),
                        zaxis=dict(title="Sharpe",      backgroundcolor=db.PLOT_BG, tickformat=".1f", gridcolor=db.DARKER, color=db.PLOT_FG),
                        bgcolor=db.PLOT_BG,
                    ),
                    paper_bgcolor=db.PLOT_BG,
                    plot_bgcolor=db.PLOT_BG,
                    font=dict(color=db.PLOT_FG),
                    legend=dict(bgcolor=db.PLOT_BG, bordercolor=db.DARKER),
                    height=650,
                )
                st.plotly_chart(_fig3d, width='stretch')
                st.caption("X = volatility, Y = return, Z = Sharpe ratio. Drag to rotate, scroll to zoom.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 – REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
        st.markdown('<div class="section-header">Full Metrics Report</div>', unsafe_allow_html=True)

        all_metrics = {
            "Annual Return":             f"{m['Annual Return']:.4%}",
            "Annual Volatility":         f"{m['Annual Volatility']:.4%}",
            "Sharpe Ratio":              f"{m['Sharpe Ratio']:.4f}",
            "Sortino Ratio":             f"{m['Sortino Ratio']:.4f}",
            "Calmar Ratio":              f"{m['Calmar Ratio']:.4f}",
            "Max Drawdown":              f"{m['Max Drawdown']:.4%}",
            "VaR 95%":                   f"{m['VaR 95%']:.4%}",
            "CVaR 95%":                  f"{m['CVaR 95%']:.4%}",
            "Beta":                      f"{m['Beta']:.4f}"                if _has_bench else "N/A",
            "Alpha (Jensen, annualized)":f"{m['Alpha (Jensen)']:.4%}"       if _has_bench else "N/A",
            "Tracking Error":            f"{m['Tracking Error']:.4%}"       if _has_bench else "N/A",
            "Information Ratio":         f"{m['Information Ratio']:.4f}"    if _has_bench else "N/A",
            "Up Capture":                f"{m['Up Capture']:.2f}%"          if _has_bench else "N/A",
            "Down Capture":              f"{m['Down Capture']:.2f}%"        if _has_bench else "N/A",
            "Correlation to Benchmark":  f"{_corr_coef:.4f}"                if _has_bench else "N/A",
            "R-Squared":                 f"{_corr_coef**2:.4f}"             if _has_bench else "N/A",
            "Benchmark Annual Return":   f"{m['Bench Annual Return']:.4%}"  if _has_bench else "N/A",
            "Benchmark Volatility":      f"{m['Bench Volatility']:.4%}"     if _has_bench else "N/A",
            "Benchmark Sharpe":          f"{m['Bench Sharpe']:.4f}"         if _has_bench else "N/A",
            "Benchmark Max Drawdown":    f"{m['Bench Max Drawdown']:.4%}"   if _has_bench else "N/A",
            "Start Date":                start_date,
            "End Date":                  end_date,
            "Benchmark":                 benchmark_ticker if benchmark_ticker.strip() else "None",
            "Risk-Free Rate":            f"{risk_free_rate:.2%}",
        }

        report_df = pd.DataFrame(list(all_metrics.items()), columns=["Metric", "Value"])
        st.dataframe(report_df, width='stretch', hide_index=True)

        # Download CSV
        csv = report_df.to_csv(index=False).encode()
        st.download_button("Download Metrics CSV", csv, "portfolio_metrics.csv", "text/csv")

        # QuantStats HTML report
        st.markdown('<div class="section-header">Full Report</div>', unsafe_allow_html=True)
        if st.button("Generate HTML Report"):
            with st.spinner("Generating report..."):
                try:
                    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
                    tmp_path = tmp.name
                    tmp.close()  # Close before QuantStats writes (required on Windows)
                    qs.reports.html(p_ret, benchmark=b_ret if _has_bench else None, output=tmp_path, title="Portfolio Report", rf=risk_free_rate)
                    with open(tmp_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    os.unlink(tmp_path)
                    st.download_button(
                        "Download HTML Report",
                        html_content.encode(),
                        "portfolio_report.html",
                        "text/html"
                    )
                    st.success("Report ready - click above to download.")
                except Exception as e:
                    st.error(f"Report failed: {e}")

gc.collect()