import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import quantstats as qs
from datetime import datetime, timedelta, date
from itertools import combinations
from collections import defaultdict
from matplotlib.colors import LinearSegmentedColormap
import warnings
import io
import os
import tempfile

warnings.filterwarnings('ignore')

import my_portfolio as _p
import json

# ── Load user config (overrides my_portfolio.py without touching it) ──────────
_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "portfolio_config.json")

def _load_config():
    """Load saved config. Falls back to my_portfolio defaults if not found."""
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_config(cfg: dict):
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

_cfg = _load_config()

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
PLOT_BG         = '#1a1a1a'
PLOT_FG         = '#e8e8e8'
ACCENT          = '#c8f55a'
ACCENT2         = "#ff4b4b"
ACCENT3         = '#6bc5ff'
ACCENT4         = '#ffa94d'
BUTTONHOVER     = '#ff2121'
DARK            = '#666666'
DARKER          = '#2a2a2a'

def apply_style(fig, ax_list=None):
    fig.patch.set_facecolor(PLOT_BG)
    if ax_list is None:
        ax_list = fig.get_axes()
    for ax in ax_list:
        ax.set_facecolor(PLOT_BG)
        ax.tick_params(colors=PLOT_FG, labelsize=9)
        ax.xaxis.label.set_color(PLOT_FG)
        ax.yaxis.label.set_color(PLOT_FG)
        ax.title.set_color(PLOT_FG)
        for spine in ax.spines.values():
            spine.set_edgecolor('#2a2a2a')
        ax.grid(True, color='#2a2a2a', linewidth=0.5, alpha=0.8)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
            
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background-color: {ACCENT2};
    color: {PLOT_FG};
    border: 1px solid {ACCENT2};
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    background-color: {BUTTONHOVER};
    color: {PLOT_FG};
    border: 1px solid {BUTTONHOVER};
}}

.stSlider [data-baseweb="slider"] [role="slider"] {{
    background-color: {ACCENT2};
}}

.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {{
    color: {ACCENT2};
}}

.stSlider [data-baseweb="slider"] div[data-testid="stSlider"] {{
    color: {ACCENT2};
}}

st-ct {{
    background-color: {ACCENT} !important;
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
    color: {'#e8e8e8'};
}}

section[data-testid="stSidebar"] {{
    background-color: {'#161616'};
    border-right: 1px solid {'#2a2a2a'};
}}

.metric-card {{
    background: {'#1a1a1a'};
    border: 1px solid {DARKER};
    border-left: 3px solid {ACCENT};
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}}

.metric-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}}

.metric-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem;
    font-weight: 600;
    color: #e8e8e8;
}}

.metric-value.positive {{ color: {ACCENT}; }}
.metric-value.negative {{ color: {ACCENT2}; }}

.section-header {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: {DARK};
    text-transform: uppercase;
    letter-spacing: 0.15em;
    border-bottom: 1px solid {DARKER};
    padding-bottom: 0.5rem;
    margin: 2rem 0 1rem 0;
}}

.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
}}

div[data-testid="stMetric"] {{
    background: {PLOT_BG};
    border: 1px solid {DARKER};
    padding: 1rem;
}}

.stDataFrame {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
}}

</style>
""", unsafe_allow_html=True)

# ── Global dollar formatter ───────────────────────────────────────────────────
import matplotlib.ticker as mticker

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
    st.caption(f"End date: {end_date}")

    st.markdown('<div class="section-header">Parameters</div>', unsafe_allow_html=True)
    risk_free_rate           = st.slider("Risk-free rate",           0.0, 10.0, float(_cv("risk_free_rate", _p.risk_free_rate) * 100), 0.1, format="%.1f%%") / 100
    benchmark_ticker         = st.text_input("Benchmark ticker", _cv("benchmark_ticker", "SPY"))
    initial_investment       = st.number_input("Initial investment ($)", 1000, 10_000_000, _cv("initial_investment", _p.initial_investment), step=500)
    monthly_investment       = st.number_input("Monthly contribution ($)", 0, 50_000, _cv("monthly_investment", _p.monthly_investment), step=100)
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

    # Track whether analysis has ever been run (persists for the session)
    if "has_run_once" not in st.session_state:
        st.session_state["has_run_once"] = False

    # Detect if data-relevant params changed -> need fresh fetch
    _key = (tickers_input, weights_input, start_date, end_date, benchmark_ticker)
    if st.session_state.get("_last_key") != _key:
        st.session_state["_last_key"] = _key
        st.session_state["analysis_run"] = False

    _btn_label = "Re-run Analysis" if st.session_state.get("has_run_once") else "Run Analysis"
    if st.button(_btn_label, type="primary", use_container_width=True):
        st.session_state["analysis_run"] = True
        st.session_state["has_run_once"] = True

    # After first run: never block the UI again even if params change
    run = st.session_state.get("analysis_run", False) or st.session_state.get("has_run_once", False)

    st.markdown('<div class="section-header">Save Configuration</div>', unsafe_allow_html=True)
    if st.button("Save settings", use_container_width=True):
        _save_config({
            "tickers_input":           tickers_input,
            "weights_input":           weights_input,
            "asset_class_input":       asset_class_input,
            "start_date":              start_date,
            "risk_free_rate":          risk_free_rate,
            "benchmark_ticker":        benchmark_ticker,
            "initial_investment":      initial_investment,
            "monthly_investment":      monthly_investment,
            "custom_annualized_return":custom_annualized_return,
            "safe_withdrawal_rate":    safe_withdrawal_rate,
        })
        st.success("Saved to portfolio_config.json")
    if os.path.exists(_CONFIG_FILE):
        if st.button("Reset to defaults", use_container_width=True):
            os.remove(_CONFIG_FILE)
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
weights       = np.array(weights_raw)

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("# Portfolio Analysis")
st.caption(f"Period: {start_date} to {end_date}  |  Benchmark: {benchmark_ticker}  |  Risk-free rate: {risk_free_rate:.2%}")

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

if not run:
    st.info("Configure your portfolio in the sidebar and click **Run Analysis**.")
    st.stop()


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    return data

@st.cache_data(show_spinner=False)
def load_benchmark(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df["Close"]
    return df.squeeze()

with st.spinner("Fetching market data..."):
    data      = load_data(tickers, start_date, end_date)
    bench_raw = load_benchmark(benchmark_ticker, start_date, end_date)

# Align columns to ticker order -- available always defined
if isinstance(data, pd.Series):
    data = data.to_frame(name=tickers[0])

available = [t for t in tickers if t in data.columns]

if len(available) == 0:
    st.error("Yhtään tickerä ei saatu ladattua. Tarkista yhteys ja tickerien nimet.")
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

bench_returns = bench_raw.pct_change(fill_method=None).dropna()
common_idx    = portfolio_returns.index.intersection(bench_returns.index)
p_ret         = portfolio_returns.loc[common_idx]
b_ret         = bench_returns.loc[common_idx]


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
m = {
    "Annual Return":       ann_return(p_ret),
    "Annual Volatility":   ann_vol(p_ret),
    "Sharpe Ratio":        sharpe(p_ret),
    "Sortino Ratio":       sortino(p_ret),
    "Max Drawdown":        max_drawdown(p_ret),
    "Calmar Ratio":        calmar(p_ret),
    "VaR 95%":             var_95(p_ret),
    "CVaR 95%":            cvar_95(p_ret),
    "Beta":                beta(p_ret.values, b_ret.values),
    "Alpha (Jensen)":      alpha_jensen(p_ret.values, b_ret.values),
    "Tracking Error":      tracking_error(p_ret, b_ret),
    "Information Ratio":   information_ratio(p_ret, b_ret),
    "Up Capture":          up_capture(p_ret, b_ret),
    "Down Capture":        down_capture(p_ret, b_ret),
    "Bench Annual Return": ann_return(b_ret),
    "Bench Volatility":    ann_vol(b_ret),
    "Bench Sharpe":        sharpe(b_ret),
    "Bench Max Drawdown":  max_drawdown(b_ret),
}


# ── Tabs ──────────────────────────────────────────────────────────────────────
# ── Custom tab navigation with session_state memory ──────────────────────────
_TAB_NAMES = ["Overview", "Performance", "Risk", "Benchmark", "Allocation", "Correlations", "FI Forecast", "Report"]
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = 0

# Inject CSS to make tab buttons look like plain text links
st.markdown("""
<style>
[data-testid="stHorizontalBlock"] > div [data-testid="stButton"] > button {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #aaa !important;
    font-size: 0.95rem !important;
    font-weight: 400 !important;
    padding: 0.25rem 0.5rem !important;
    border-radius: 0 !important;
    transition: color 0.15s;
    width: 100%;
}
[data-testid="stHorizontalBlock"] > div [data-testid="stButton"] > button:hover {
    color: #e53935 !important;
    background: none !important;
}
[data-testid="stHorizontalBlock"] > div [data-testid="stButton"] > button.active-tab {
    color: #fff !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #fff !important;
}
</style>
""", unsafe_allow_html=True)

_tcols = st.columns(len(_TAB_NAMES))
for _i, (_tc, _tn) in enumerate(zip(_tcols, _TAB_NAMES)):
    with _tc:
        _is_active = st.session_state["active_tab"] == _i
        _label = f"**{_tn}**" if _is_active else _tn
        if st.button(
            _label,
            key=f"_tab_btn_{_i}",
            use_container_width=True,
        ):
            st.session_state["active_tab"] = _i
            st.rerun()

st.markdown("<hr style='margin:0.3rem 0 1rem 0; border-color:#444'>", unsafe_allow_html=True)
_active_tab = st.session_state["active_tab"]

tab_overview = _active_tab == 0
tab_perf     = _active_tab == 1
tab_risk     = _active_tab == 2
tab_bench    = _active_tab == 3
tab_alloc    = _active_tab == 4
tab_corr     = _active_tab == 5
tab_fi       = _active_tab == 6
tab_report   = _active_tab == 7


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if tab_overview:
    def metric_html(label, value, fmt=".2%", positive_good=True):
        if isinstance(value, float) and not np.isnan(value):
            if fmt == ".2f" or fmt == ".3f":
                display = f"{value:{fmt}}"
            else:
                display = f"{value:{fmt}}"
            cls = ""
            if positive_good:
                cls = "positive" if value > 0 else "negative"
            else:
                cls = "negative" if value > 0 else "positive"
        else:
            display = "N/A"
            cls = ""
        return f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {cls}">{display}</div>
        </div>"""

    col1, col2, col3, col4 = st.columns(4)
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

    st.markdown('<div class="section-header">Holdings - Links to Yahoo Finance</div>', unsafe_allow_html=True)

    # Yahoo Finance links
    links_html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:1.5rem;">'
    for t in tickers:
        url = f'https://finance.yahoo.com/quote/{t}'
        links_html += f'<a href="{url}" target="_blank" style="font-family:IBM Plex Mono,monospace;font-size:0.8rem;color:#c8f55a;background:#1a1a1a;border:1px solid #2a2a2a;padding:0.35rem 0.75rem;text-decoration:none;letter-spacing:0.05em;">{t}</a>'
    links_html += '</div>'
    st.markdown(links_html, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Cumulative Growth</div>', unsafe_allow_html=True)

    fig, ax = plt.subplots(figsize=(12, 4))
    cum_p = (1 + p_ret).cumprod() * initial_investment
    cum_b = (1 + b_ret).cumprod() * initial_investment
    ax.plot(cum_p.index, cum_p.values, color=ACCENT,  linewidth=2,   label="Portfolio")
    ax.plot(cum_b.index, cum_b.values, color=ACCENT3, linewidth=1.5, label=benchmark_ticker, alpha=0.7)
    ax.fill_between(cum_p.index, initial_investment, cum_p.values, alpha=0.1, color=ACCENT)
    ax.set_ylabel("Value")
    ax.legend(fontsize=9)
    dollar_axis(ax)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
if tab_perf:
    st.markdown('<div class="section-header">Daily Returns</div>', unsafe_allow_html=True)

    fig, axes = plt.subplots(3, 1, figsize=(12, 9))

    # 1. Daily returns bar
    axes[0].bar(p_ret.index, p_ret.values,
                color=np.where(p_ret.values >= 0, ACCENT, ACCENT2), width=1, alpha=0.8)
    axes[0].set_ylabel("Daily Return")
    axes[0].set_title("Daily Returns")
    pct_axis(axes[0], decimals=1, multiply=True)

    # 2. Cumulative returns
    cum = (1 + p_ret).cumprod() - 1
    axes[1].plot(cum.index, cum.values * 100, color=ACCENT, linewidth=2)
    axes[1].fill_between(cum.index, 0, cum.values * 100, alpha=0.15, color=ACCENT)
    axes[1].set_ylabel("Cumulative Return")
    axes[1].set_title("Cumulative Return")
    pct_axis(axes[1], decimals=0)

    # 3. Rolling 30-day volatility
    roll_vol = p_ret.rolling(30).std() * np.sqrt(252) * 100
    axes[2].plot(roll_vol.index, roll_vol.values, color=ACCENT4, linewidth=1.5)
    axes[2].fill_between(roll_vol.index, 0, roll_vol.values, alpha=0.2, color=ACCENT4)
    axes[2].set_ylabel("Annualized Vol")
    axes[2].set_title("30-Day Rolling Volatility")
    pct_axis(axes[2], decimals=1)

    apply_style(fig, axes)
    fig.tight_layout(pad=2)
    st.pyplot(fig)
    plt.close()

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
                    annot_kws={'size': 8}, ax=ax, cbar_kws={'label': 'Return', 'format': mticker.FuncFormatter(lambda x, _: f"{x:.1f}%")})
        # Add % suffix to each annotated cell
        for t in ax.texts:
            t.set_text(t.get_text() + "%")
        ax.set_title("Monthly Returns")
        ax.set_xlabel("")
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close()

    # Annual returns
    st.markdown('<div class="section-header">Annual Returns</div>', unsafe_allow_html=True)
    annual = p_ret.resample('YE').apply(lambda x: (1 + x).prod() - 1)
    fig, ax = plt.subplots(figsize=(12, 3))
    colors_bar = [ACCENT if v >= 0 else ACCENT2 for v in annual.values]
    ax.bar(annual.index.year, annual.values * 100, color=colors_bar, width=0.6)
    ax.axhline(0, color='#555', linewidth=0.8)
    ax.set_ylabel("Return")
    ax.set_title("Annual Returns")
    pct_axis(ax, decimals=0)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – RISK
# ══════════════════════════════════════════════════════════════════════════════
if tab_risk:
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
            f"{m['Bench Volatility']:.2%}",
            f"{m['Bench Max Drawdown']:.2%}",
            f"{var_95(b_ret):.2%}",
            f"{cvar_95(b_ret):.2%}",
            f"{calmar(b_ret):.3f}",
            f"{m['Bench Sharpe']:.3f}",
            f"{sortino(b_ret):.3f}",
        ],
    })
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

    # Drawdown chart
    st.markdown('<div class="section-header">Drawdown</div>', unsafe_allow_html=True)
    cum   = (1 + p_ret).cumprod()
    roll  = cum.cummax()
    dd    = (cum - roll) / roll

    cum_b  = (1 + b_ret).cumprod()
    roll_b = cum_b.cummax()
    dd_b   = (cum_b - roll_b) / roll_b

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(dd.index,   dd.values   * 100, 0, color=ACCENT2, alpha=0.6, label="Portfolio")
    ax.fill_between(dd_b.index, dd_b.values * 100, 0, color=ACCENT3, alpha=0.3, label=benchmark_ticker)
    ax.set_ylabel("Drawdown")
    ax.set_title("Underwater Chart")
    ax.legend(fontsize=9)
    pct_axis(ax, decimals=1)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    # Return distribution
    st.markdown('<div class="section-header">Return Distribution</div>', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.hist(p_ret.values * 100, bins=80, color=ACCENT, alpha=0.75, edgecolor='none', label="Portfolio")
    ax.hist(b_ret.values * 100, bins=80, color=ACCENT3, alpha=0.4, edgecolor='none', label=benchmark_ticker)
    v95 = var_95(p_ret) * 100
    ax.axvline(v95, color=ACCENT2, linewidth=1.5, linestyle='--', label=f"VaR 95%: {v95:.2f}%")
    ax.set_xlabel("Daily Return")
    ax.set_ylabel("Frequency")
    ax.set_title("Return Distribution")
    ax.legend(fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    # Rolling Sharpe
    st.markdown('<div class="section-header">252-Day Rolling Sharpe Ratio</div>', unsafe_allow_html=True)
    roll_sharpe = p_ret.rolling(252).apply(lambda x: sharpe(pd.Series(x)), raw=False)
    if roll_sharpe.dropna().empty:
        st.caption("Not enough data for 252-day rolling Sharpe.")
    else:
        fig, ax = plt.subplots(figsize=(12, 3))
        ax.plot(roll_sharpe.index, roll_sharpe.values, color=ACCENT, linewidth=1.5)
        ax.axhline(0, color='#555', linewidth=0.8)
        ax.axhline(1, color=ACCENT, linewidth=0.6, linestyle='--', alpha=0.5)
        ax.set_ylabel("Sharpe Ratio")
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
if tab_bench:
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
            f"{np.corrcoef(p_ret, b_ret)[0,1]:.3f}",
        ],
        f"Benchmark ({benchmark_ticker})": [
            f"{m['Bench Annual Return']:.2%}",
            f"{m['Bench Volatility']:.2%}",
            f"{m['Bench Sharpe']:.3f}",
            f"{m['Bench Max Drawdown']:.2%}",
            "1.000", "0.00%", "0.00%", "—", "100.0%", "100.0%", "1.000",
        ],
    })
    st.dataframe(bench_metrics, use_container_width=True, hide_index=True)

    # Cumulative comparison
    fig, ax = plt.subplots(figsize=(12, 4))
    cum_p = (1 + p_ret).cumprod() * initial_investment
    cum_b = (1 + b_ret).cumprod() * initial_investment
    ax.plot(cum_p.index, cum_p.values, color=ACCENT,  linewidth=2,   label="Portfolio")
    ax.plot(cum_b.index, cum_b.values, color=ACCENT3, linewidth=1.5, label=benchmark_ticker, alpha=0.8)
    ax.set_ylabel("Value")
    ax.set_title("Cumulative Growth Comparison")
    ax.legend(fontsize=9)
    dollar_axis(ax)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    # Rolling Beta
    st.markdown('<div class="section-header">252-Day Rolling Beta</div>', unsafe_allow_html=True)
    def rolling_beta(window=252):
        betas = []
        idx   = []
        for i in range(window, len(p_ret)):
            pw = p_ret.iloc[i-window:i].values
            bw = b_ret.iloc[i-window:i].values
            cov = np.cov(pw, bw)
            betas.append(cov[0,1] / cov[1,1] if cov[1,1] != 0 else np.nan)
            idx.append(p_ret.index[i])
        return pd.Series(betas, index=idx)

    rb = rolling_beta()
    if rb.dropna().empty:
        st.caption("Not enough data for 252-day rolling Beta.")
    else:
        fig, ax = plt.subplots(figsize=(12, 3))
        ax.plot(rb.index, rb.values, color=ACCENT4, linewidth=1.5)
        ax.axhline(1, color='#555', linewidth=0.8, linestyle='--')
        ax.axhline(0, color='#333', linewidth=0.5)
        ax.set_ylabel("Beta")
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close()

    # Scatter
    st.markdown('<div class="section-header">Excess Returns Scatter</div>', unsafe_allow_html=True)
    legendalpha=0.6
    regressionalpha=0.4
    linealpha=0.5
    dotalpha=0.5
    linecolor='#505050'
    sc_size = 7
    sc_pos  = "Left"
    fig, ax = plt.subplots(figsize=(sc_size, sc_size))
    ax.scatter(b_ret.values * 100, p_ret.values * 100,
               color=ACCENT, alpha=dotalpha, s=4, linewidths=0)
    xlim = max(abs(b_ret.values).max() * 100, 1)
    x_line = np.linspace(-xlim, xlim, 100)
    b_val  = m["Beta"]
    a_val  = m["Alpha (Jensen)"] / 252
    ax.plot(x_line, b_val * x_line + a_val * 100, color=ACCENT2, linewidth=1.5,
            label=f"Regression (β={b_val:.2f})", alpha=regressionalpha)
    ax.axhline(0, color=linecolor, linewidth=1, alpha=linealpha)
    ax.axvline(0, color=linecolor, linewidth=1, alpha=linealpha)
    ax.set_xlabel(f"{benchmark_ticker} Daily Return (%)")
    ax.set_ylabel("Portfolio Daily Return")
    ax.set_title("Portfolio vs Benchmark")
    legend_loc = "upper left" if b_val >= 0 else "upper right"
    leg = ax.legend(fontsize=10, loc=legend_loc, framealpha=legendalpha)
    for text in leg.get_texts():
        text.set_alpha(legendalpha)
    xlim = max(abs(b_ret.values).max() * 100, 1)
    ax.set_xlim(-xlim, xlim)
    ax.set_ylim(-xlim, xlim)
    pct_axis(ax, decimals=1)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    apply_style(fig, [ax])
    ax.grid(True, color=linecolor, linewidth=0.5, alpha=linealpha)
    fig.tight_layout()
    sc_gap = max(1, 12 - sc_size)
    if   sc_pos == "Left":   _cols = st.columns([sc_size, sc_gap]);              _col = _cols[0]
    elif sc_pos == "Right":  _cols = st.columns([sc_gap, sc_size]);              _col = _cols[1]
    else:                     _cols = st.columns([sc_gap//2, sc_size, sc_gap//2]); _col = _cols[1]
    with _col: st.pyplot(fig, use_container_width=False)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════
if tab_alloc:
    st.markdown('<div class="section-header">Portfolio Weights</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Keyword-based group colors — anything matching a keyword gets this base color
    ASSET_GROUP_COLORS = [
        (['etf', 'stocks', 'fund', 'index', 'tracker', 'ishares', 'vanguard',
          'msci', 'sp500', 's&p', 'nasdaq', 'dow', 'russell', 'country etf',
          'sector etf', 'bond etf', 'equity etf', 'eft'],       "#2e80b8"),  # blue
        (['stock', 'equity', 'share', 'growth', 'value', 'small cap',
          'mid cap', 'large cap', 'dividend'],                    "#d44535"),  # red
        (['cash', 'money market', 'savings', 'deposit', 'liquidity',
          # Fiat spot pairs (Yahoo Finance format)
          'eurusd=x', 'usdeur=x', 'gbpusd=x', 'usdgbp=x', 'usdjpy=x',
          'jpyusd=x', 'usdchf=x', 'chfusd=x', 'usdcad=x', 'cadusd=x',
          'audusd=x', 'usdaud=x', 'nzdusd=x', 'usdnzd=x', 'usdsek=x',
          'usdnok=x', 'usddkk=x', 'usdpln=x', 'usdhuf=x', 'usdczk=x',
          'usdsgd=x', 'usdhkd=x', 'usdcny=x', 'usdtry=x', 'usdinr=x',
          'usdbrl=x', 'usdmxn=x', 'usdzar=x', 'usdkrw=x',
          # Generic currency keywords
          'eurusd', 'gbpusd', 'usdjpy', 'usdchf', 'usdcad', 'audusd',
          'nzdusd', 'usd', 'eur', 'gbp', 'jpy', 'chf'],          "#29b864"),  # green
        (['bond', 'fixed income', 'treasury', 'gilt', 'note',
          'corporate bond', 'municipal', 'high yield', 'duration'],  '#f39c12'),  # orange
        (['reit', 'real estate', 'property', 'infrastructure'],  '#e67e22'),  # dark orange
        (['commodity', 'gold', 'silver', 'oil', 'gas', 'copper',
          'wheat', 'corn', 'platinum', 'natural resource'],       '#95a5a6'),  # gray
        (['crypto', 'bitcoin', 'ethereum', 'altcoin', 'defi', 'web3',
          # Base names
          'btc', 'eth', 'xrp', 'sol', 'bnb', 'doge', 'ada', 'avax',
          'dot', 'matic', 'ltc', 'link', 'uni', 'atom', 'xlm', 'algo',
          'icp', 'fil', 'hbar', 'near', 'apt', 'arb', 'op', 'sui',
          'trx', 'shib', 'pepe', 'floki', 'inj', 'sei', 'ton', 'kas',
          # USD pairs
          'btcusd', 'ethusd', 'xrpusd', 'solusd', 'bnbusd', 'dogeusd',
          'adausd', 'avaxusd', 'dotusd', 'maticusd', 'ltcusd', 'linkusd',
          'uniusd', 'atomusd', 'xlmusd', 'algousd', 'icpusd', 'filusd',
          'hbarusd', 'nearusd', 'aptusd', 'arbusd', 'opusd', 'suiusd',
          'trxusd', 'shibusd', 'pepeusd', 'injusd', 'seiusd', 'tonusd',
          # EUR pairs
          'btceur', 'etheur', 'xrpeur', 'soleur', 'bnbeur', 'dogeeur',
          'adaeur', 'avaxeur', 'doteur', 'maticeur', 'ltceur', 'linkeur',
          'unieur', 'atomeur', 'xlmeur', 'algoeur', 'icpeur', 'fileur',
          'hbareur', 'neareur', 'apteur', 'arbeur', 'opeur', 'suieur',
          'trxeur', 'shibeur', 'pepeeur', 'injeur', 'seieur', 'toneur',
          # Yahoo Finance format (COIN-USD / COIN-EUR)
          'btc-usd', 'eth-usd', 'xrp-usd', 'sol-usd', 'bnb-usd',
          'doge-usd', 'ada-usd', 'avax-usd', 'dot-usd', 'matic-usd',
          'ltc-usd', 'link-usd', 'uni-usd', 'atom-usd', 'xlm-usd',
          'algo-usd', 'icp-usd', 'fil-usd', 'hbar-usd', 'near-usd',
          'apt-usd', 'arb-usd', 'op-usd', 'sui-usd', 'trx-usd',
          'shib-usd', 'pepe-usd', 'inj-usd', 'sei-usd', 'ton-usd',
          'kas-usd', 'fet-usd', 'render-usd', 'grt-usd', 'sand-usd',
          'mana-usd', 'axs-usd', 'flow-usd', 'egld-usd', 'theta-usd',
          'btc-eur', 'eth-eur', 'xrp-eur', 'sol-eur', 'bnb-eur',
          'doge-eur', 'ada-eur', 'avax-eur', 'dot-eur', 'matic-eur',
          'ltc-eur', 'link-eur', 'uni-eur', 'atom-eur', 'xlm-eur',
          'algo-eur', 'icp-eur', 'fil-eur', 'hbar-eur', 'near-eur',
          'apt-eur', 'arb-eur', 'op-eur', 'sui-eur', 'trx-eur',
          'shib-eur', 'pepe-eur', 'inj-eur', 'sei-eur', 'ton-eur',
          # Stablecoins
          'usdt', 'usdc', 'dai', 'busd', 'tusd', 'frax'],        '#fd79a8'),  # pink
        (['forex', 'currency', 'fx',
          # Yahoo Finance forex format (XXXYYY=X)
          'eurusd=x', 'gbpusd=x', 'usdjpy=x', 'usdchf=x', 'usdcad=x',
          'audusd=x', 'nzdusd=x', 'usdsek=x', 'usdnok=x', 'usddkk=x',
          'usdpln=x', 'usdhuf=x', 'usdczk=x', 'usdsgd=x', 'usdhkd=x',
          'usdcny=x', 'usdtry=x', 'usdinr=x', 'usdbrl=x', 'usdmxn=x',
          'usdzar=x', 'usdkrw=x', 'usdphp=x', 'usdthb=x', 'usdidr=x',
          'eurgbp=x', 'eurjpy=x', 'eurchf=x', 'eurcad=x', 'euraud=x',
          'eurnzd=x', 'eursek=x', 'eurnok=x', 'gbpjpy=x', 'gbpchf=x',
          'gbpcad=x', 'gbpaud=x', 'gbpnzp=x', 'chfjpy=x', 'cadjpy=x',
          'audjpy=x', 'nzdjpy=x', 'audcad=x', 'audchf=x', 'audnzd=x',
          '=x'],                                                  '#f1c40f'),  # yellow
    ]

    def get_group_color(label):
        """Return base group color by matching keywords in label or ticker symbol."""
        l = label.lower()
        for keywords, color in ASSET_GROUP_COLORS:
            if any(kw in l for kw in keywords):
                return color
        return '#7f8c8d'  # fallback gray

    def get_ticker_colors(ticker_list, asset_classes_dict, sizes):
        """Each ticker gets its own shade derived from its asset group color.
        Falls back to matching the ticker symbol itself when asset class gives no match."""
        import colorsys
        groups = defaultdict(list)
        for t in ticker_list:
            ac_label = asset_classes_dict.get(t, '')
            color = get_group_color(ac_label)
            # If asset class didn't match, try the ticker symbol itself
            if color == '#7f8c8d':
                color = get_group_color(t)
            groups[color].append(t)
        ticker_color_map = {}
        for base_hex, group_tickers in groups.items():
            r = int(base_hex[1:3], 16) / 255
            g = int(base_hex[3:5], 16) / 255
            b = int(base_hex[5:7], 16) / 255
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            n = len(group_tickers)
            # Sort tickers in group by weight descending — largest gets base color
            group_tickers_sorted = sorted(
                group_tickers,
                key=lambda t: ticker_list.index(t)
            )
            weights_in_group = [sizes[ticker_list.index(t)] for t in group_tickers_sorted]
            # Re-sort by weight descending so biggest gets idx=0 (base color)
            group_tickers_sorted = [t for _, t in sorted(
                zip(weights_in_group, group_tickers_sorted), reverse=True)]
            for idx, t in enumerate(group_tickers_sorted):
                if n == 1:
                    new_h, new_s, new_v = h, s, v
                else:
                    # Keep hue identical, only brighten each step
                    new_h = h
                    new_s = max(0.25, s - idx * 0.20)
                    new_v = min(1.0, v + idx * 0.22)
                nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
                ticker_color_map[t] = '#{:02x}{:02x}{:02x}'.format(
                    int(nr * 255), int(ng * 255), int(nb * 255))
        return [ticker_color_map[t] for t in ticker_list]

    def draw_pie(ax, sizes, labels, colors, title):
        """Draw a pie chart with labels+percentages in a legend, no overlapping text."""
        explode = [0.00] * len(sizes)
        wedges, _ = ax.pie(
            sizes,
            colors=colors,
            startangle=140,
            wedgeprops=dict(linewidth=0.5 if len(sizes) > 1 else 0, edgecolor="#0f0f0f"),
            explode=explode,
        )
        # Build legend labels: "TICKER  12.3%"
        legend_labels = [f"{lbl}  {sz:.1%}" for lbl, sz in zip(labels, sizes)]
        ax.legend(
            wedges, legend_labels,
            loc='center left',
            bbox_to_anchor=(-0.45, 0.5),
            fontsize=9,
            frameon=True,
            facecolor='#1a1a1a',
            edgecolor='#2a2a2a',
            labelcolor=PLOT_FG,
        )
        ax.set_title(title, color=PLOT_FG, pad=12)
        ax.set_facecolor(PLOT_BG)

    with col1:
        # Ticker pie
        ticker_colors = get_ticker_colors(tickers, asset_classes, weights_raw)
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor(PLOT_BG)
        draw_pie(ax, weights_raw, tickers, ticker_colors, "By Ticker")
        fig.subplots_adjust(left=0.35)
        st.pyplot(fig)
        plt.close()

    with col2:
        # Asset class pie
        class_weights = defaultdict(float)
        for ticker, weight in portfolio.items():
            if ticker in asset_classes:
                class_weights[asset_classes[ticker]] += weight

        if class_weights:
            labels_ac = list(class_weights.keys())
            sizes_ac  = list(class_weights.values())
            ac_colors = [get_group_color(l) for l in labels_ac]
            fig, ax = plt.subplots(figsize=(6, 5))
            fig.patch.set_facecolor(PLOT_BG)
            draw_pie(ax, sizes_ac, labels_ac, ac_colors, "By Asset Class")
            fig.subplots_adjust(left=0.35)
            st.pyplot(fig)
            plt.close()

    # Holdings table
    st.markdown('<div class="section-header">Holdings</div>', unsafe_allow_html=True)
    holdings_df = pd.DataFrame({
        "Ticker":       tickers,
        "Weight":       [f"{w:.2%}" for w in weights_raw],
        "Asset Class":  [asset_classes.get(t, "—") for t in tickers],
    })
    st.dataframe(holdings_df, use_container_width=True, hide_index=True)

    # Individual performance
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
        st.dataframe(pd.DataFrame(ind_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 – CORRELATIONS
# ══════════════════════════════════════════════════════════════════════════════
if tab_corr:

    coolwarm_colors = plt.cm.coolwarm(np.linspace(0, 1, 256))
    white = np.array([[1, 1, 1, 1]])  # RGBA valkoinen
    extended_colors = np.vstack([coolwarm_colors, white])
    custom_cmap = LinearSegmentedColormap.from_list("coolwarm_white", extended_colors)

    @st.fragment
    def render_correlations():
        st.markdown('<div class="section-header">Correlation Matrix</div>', unsafe_allow_html=True)
        cm_size = max(7, len(tickers))  # ← kaavion koko (tuumaa, neliö)
        cm_pos  = "Left"              # ← sijainti: "Left" / "Center" / "Right"

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
        cm_gap = max(1, 12 - cm_size)
        if   cm_pos == "Left":   _cols = st.columns([cm_size, cm_gap]);               _col = _cols[0]
        elif cm_pos == "Right":  _cols = st.columns([cm_gap, cm_size]);               _col = _cols[1]
        else:                     _cols = st.columns([cm_gap//2, cm_size, cm_gap//2]); _col = _cols[1]
        with _col: st.pyplot(fig, use_container_width=False)
        plt.close()

        if len(tickers) >= 2:
            st.markdown('<div class="section-header">36-Month Rolling Correlation</div>', unsafe_allow_html=True)
            default_window = min(36, len(monthly_r) - 1)
            window_size = st.slider("Rolling window (months)", 6, 60, max(6, default_window))
            if len(monthly_r) < window_size:
                st.warning(f"Dataa on vain {len(monthly_r)} kuukautta — tarvitaan vähintään {window_size}. Pienennä ikkunaa sliderilla.")
            else:
                fig, ax = plt.subplots(figsize=(12, 4))
                color_cycle = [ACCENT, ACCENT3, ACCENT4, ACCENT2, '#b19cd9']
                for i, (t1, t2) in enumerate(combinations(available, 2)):
                    rc = monthly_r[t1].rolling(window_size).corr(monthly_r[t2])
                    ax.plot(rc, label=f"{t1} vs {t2}",
                            linewidth=2, color=color_cycle[i % len(color_cycle)])
                ax.axhline(0,  color='#555', linewidth=0.5)
                ax.axhline(1,  color='#333', linewidth=0.5, linestyle='--')
                ax.axhline(-1, color='#333', linewidth=0.5, linestyle='--')
                ax.set_ylim(-1.05, 1.05)
                ax.set_ylabel("Correlation")
                ax.set_title(f"{window_size}-Month Rolling Correlation")
                ax.legend(fontsize=9, loc='lower left')
                apply_style(fig, [ax])
                st.pyplot(fig)
                plt.close()

    render_correlations()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 – FI FORECAST
# ══════════════════════════════════════════════════════════════════════════════
if tab_fi:
    @st.fragment
    def render_fi():
        st.markdown('<div class="section-header">Financial Independence Forecast</div>', unsafe_allow_html=True)

        # ── Spend targets ───────────────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        with col1:
            lean_fi = st.number_input("Lean FI annual spend ($k)",  10, 500, 36)
        with col2:
            safe_fi = st.number_input("Safe FI annual spend ($k)",  10, 500, 50)
        with col3:
            cozy_fi = st.number_input("Cozy FI annual spend ($k)",  10, 500, 100)

        # ── Withdrawal start slider ─────────────────────────────────────────
        st.markdown('<div class="section-header">Withdrawal Phase Settings</div>', unsafe_allow_html=True)
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

        no_withdrawals = _wy_sel == "Accumulation only"

        hist_return  = ann_return(p_ret)
        use_return   = custom_annualized_return if custom_annualized_return > 0 else hist_return
        return_label = f"{use_return:.1%} (historical)" if custom_annualized_return == 0 else f"{use_return:.1%} (custom)"
        monthly_ret  = (1 + use_return) ** (1/12) - 1

        if no_withdrawals:
            st.caption(
                f"**Accumulation only** — contributing ${monthly_investment}/month for {total_horizon_years} years, "
                f"growing at {return_label}/yr. No withdrawals."
            )
        else:
            st.caption(
                f"**Accumulation:** years 0–{withdrawal_start_year} — contributing ${monthly_investment}/month, "
                f"growing at {return_label}/yr   |   "
                f"**Withdrawal:** years {withdrawal_start_year}–{total_horizon_years} — contributions stop, spending begins"
            )

        total_months         = total_horizon_years * 12
        # If withdrawal_start_year == 0, set start beyond total so withdrawal phase never triggers
        withdrawal_start_mo  = total_months if no_withdrawals else withdrawal_start_year * 12
        proj_dates           = pd.date_range(datetime.today(), periods=total_months + 1, freq='MS')

        # ── Current portfolio value: initial_investment grown through history ──
        current_portfolio_value = (1 + p_ret).cumprod().iloc[-1] * initial_investment

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
            (lean_fi, "Lean FI",  ACCENT3),
            (safe_fi, "Safe FI",  ACCENT),
            (cozy_fi, "Cozy FI",  ACCENT4),
        ]

        # ── Main chart ──────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(12, 5))

        # Shade accumulation vs withdrawal regions
        acc_end_date = proj_dates[withdrawal_start_mo] if not no_withdrawals else proj_dates[-1]
        ax.axvspan(proj_dates[0], acc_end_date, alpha=0.04, color=ACCENT, zorder=0)
        if not no_withdrawals:
            ax.axvspan(acc_end_date, proj_dates[-1], alpha=0.04, color=ACCENT2, zorder=0)
            ax.axvline(acc_end_date, color="white", linewidth=1.2, linestyle=':', alpha=0.6)

        # ── Dollar formatter for $k values (wraps global fmt_dollar) ────────
        def fmt_dollars(value_k):
            return fmt_dollar(value_k * 1000)

        def _yaxis_fmt(x, pos):
            return fmt_dollars(x)

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
                legend_label = f"{label} target: {fmt_dollars(target)}"
                if target <= y_top:
                    # Target is within chart range — draw horizontal line
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
                    # Target above chart — invisible proxy so it still appears in legend
                    ax.plot([], [], color=color, linewidth=0.8, linestyle=':',
                            alpha=0.5, label=legend_label)

        ax.axhline(0, color='white', linewidth=0.6, alpha=0.3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_yaxis_fmt))
        ax.set_ylabel("Net Worth")
        ax.set_title(
            f"FI Forecast — {return_label} return  |  "
            f"${monthly_investment}/mo contribution until yr {withdrawal_start_year}  |  "
            f"SWR {safe_withdrawal_rate:.1%}" if has_swr else
            f"FI Forecast — {return_label} return  |  "
            f"${monthly_investment}/mo contribution until yr {withdrawal_start_year}"
        )
        ax.legend(fontsize=9, loc='upper left')
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
        st.pyplot(fig)
        plt.close()

        # ── FI Summary table ────────────────────────────────────────────────
        st.markdown('<div class="section-header">FI Goals Summary</div>', unsafe_allow_html=True)
        st.caption(f"Forecast starts from current portfolio value: ${current_portfolio_value:,.0f} (${initial_investment:,.0f} invested from {start_date}, grown at historical returns)")

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
                fi_target   = fmt_dollars(target)
                yrs_str     = f"{yrs_to_fi:.1f}" if yrs_to_fi else f">{withdrawal_start_year}"
            else:
                fi_target = "—"
                yrs_str   = "—"

            # Portfolio longevity after withdrawal start
            withdrawal_vals = vals[withdrawal_start_mo:]
            exhausted = [i for i, v in enumerate(withdrawal_vals) if v <= 0]
            if exhausted:
                longevity = f"{exhausted[0] / 12:.0f} yrs (exhausted)"
            else:
                longevity = f"{(total_horizon_years - withdrawal_start_year)}+ yrs ({fmt_dollars(vals[-1])} left)"

            monthly_w = spend_k / 12
            fi_rows.append({
                "Scenario":              label,
                "Annual Spend":          f"${spend_k}k  (${monthly_w:.1f}k/mo)",
                "Required NW (SWR)":     fi_target,
                "Years to FI target":    yrs_str,
                "NW at retirement":      fmt_dollars(nw_at_retirement),
                "Portfolio lasts":       longevity,
            })

        st.dataframe(pd.DataFrame(fi_rows), use_container_width=True, hide_index=True)

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

        ax.axvspan(proj_dates[0], acc_end_date, alpha=0.04, color=ACCENT, zorder=0)
        ax.axvspan(acc_end_date, proj_dates[-1], alpha=0.04, color=ACCENT2, zorder=0)
        ax.axvline(acc_end_date, color="white", linewidth=1.0, linestyle=':', alpha=0.5)

        for path in mc_paths[:int(n_paths_plot)]:
            ax.plot(proj_dates, path, alpha=0.04, color=ACCENT, linewidth=0.7)

        p10 = np.percentile(mc_arr, 10,  axis=0)
        p50 = np.percentile(mc_arr, 50,  axis=0)
        p90 = np.percentile(mc_arr, 90,  axis=0)
        ax.plot(proj_dates, p50, color=ACCENT,  linewidth=2,   label="Median (50th pct)")
        ax.plot(proj_dates, p10, color=ACCENT2, linewidth=1.5, linestyle='--', label="Pessimistic (10th pct)")
        ax.plot(proj_dates, p90, color=ACCENT3, linewidth=1.5, linestyle='--', label="Optimistic (90th pct)")
        ax.fill_between(proj_dates, p10, p90, alpha=0.08, color=ACCENT)
        ax.axhline(0, color='white', linewidth=0.6, alpha=0.3)

        # % of paths that survive (stay > 0) through full horizon
        surviving = np.sum(mc_arr[:, -1] > 0) / len(mc_paths) * 100
        exhausted_paths = np.sum(mc_arr[:, -1] <= 0)

        ax.set_ylabel("Net Worth")
        ax.set_title(
            f"{total_horizon_years}-yr Monte Carlo — {mc_spend} (${mc_spend_k}k/yr spend)  |  "
            f"Withdrawals start yr {withdrawal_start_year}  |  "
            f"Portfolio survives in {surviving:.0f}% of scenarios"
        )
        ax.legend(fontsize=9)
        dollar_axis_k = mticker.FuncFormatter(lambda x, _: fmt_dollars(x))
        ax.yaxis.set_major_formatter(dollar_axis_k)
        apply_style(fig, [ax])
        st.pyplot(fig)
        plt.close()

        st.caption(
            f"At year {total_horizon_years} — "
            f"Median: {fmt_dollars(p50[-1])}  |  "
            f"10th pct: {fmt_dollars(p10[-1])}  |  "
            f"90th pct: {fmt_dollars(p90[-1])}  |  "
            f"Portfolio exhausted in {exhausted_paths:.0f}/{int(n_sim)} scenarios ({100-surviving:.0f}%)"
        )

    render_fi()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 – REPORT
# ══════════════════════════════════════════════════════════════════════════════
if tab_report:
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
        "Beta":                      f"{m['Beta']:.4f}",
        "Alpha (Jensen, annualized)":f"{m['Alpha (Jensen)']:.4%}",
        "Tracking Error":            f"{m['Tracking Error']:.4%}",
        "Information Ratio":         f"{m['Information Ratio']:.4f}",
        "Up Capture":                f"{m['Up Capture']:.2f}%",
        "Down Capture":              f"{m['Down Capture']:.2f}%",
        "Correlation to Benchmark":  f"{np.corrcoef(p_ret, b_ret)[0,1]:.4f}",
        "R-Squared":                 f"{np.corrcoef(p_ret, b_ret)[0,1]**2:.4f}",
        "Benchmark Annual Return":   f"{m['Bench Annual Return']:.4%}",
        "Benchmark Volatility":      f"{m['Bench Volatility']:.4%}",
        "Benchmark Sharpe":          f"{m['Bench Sharpe']:.4f}",
        "Benchmark Max Drawdown":    f"{m['Bench Max Drawdown']:.4%}",
        "Start Date":                start_date,
        "End Date":                  end_date,
        "Benchmark":                 benchmark_ticker,
        "Risk-Free Rate":            f"{risk_free_rate:.2%}",
    }

    report_df = pd.DataFrame(list(all_metrics.items()), columns=["Metric", "Value"])
    st.dataframe(report_df, use_container_width=True, hide_index=True)

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
                qs.reports.html(p_ret, benchmark=b_ret, output=tmp_path, title="Portfolio Report")
                with open(tmp_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                os.unlink(tmp_path)
                st.download_button(
                    "Download HTML Report",
                    html_content.encode(),
                    "portfolio_report.html",
                    "text/html"
                )
                st.success("Report ready — click above to download.")
            except Exception as e:
                st.error(f"Report failed: {e}")
