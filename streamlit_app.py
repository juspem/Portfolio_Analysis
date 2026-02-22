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
import warnings
import io
import os
import tempfile

warnings.filterwarnings('ignore')

import my_portfolio as _p

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: -0.02em;
}

.stApp {
    background-color: #0f0f0f;
    color: #e8e8e8;
}

section[data-testid="stSidebar"] {
    background-color: #161616;
    border-right: 1px solid #2a2a2a;
}

.metric-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #c8f55a;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}

.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}

.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem;
    font-weight: 600;
    color: #e8e8e8;
}

.metric-value.positive { color: #c8f55a; }
.metric-value.negative { color: #ff6b6b; }

.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.5rem;
    margin: 2rem 0 1rem 0;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
}

div[data-testid="stMetric"] {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    padding: 1rem;
}

.stDataFrame {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)


# ── Matplotlib dark theme ─────────────────────────────────────────────────────
plt.style.use('dark_background')
PLOT_BG    = '#1a1a1a'
PLOT_FG    = '#e8e8e8'
ACCENT     = '#c8f55a'
ACCENT2    = '#ff6b6b'
ACCENT3    = '#6bc5ff'
ACCENT4    = '#ffa94d'

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


# ── Sidebar – Portfolio Configuration ────────────────────────────────────────
with st.sidebar:
    st.markdown("## Portfolio Analysis")
    st.markdown('<div class="section-header">Holdings</div>', unsafe_allow_html=True)

    tickers_input  = st.text_input("Tickers (comma-separated)", ",".join(_p.tickers))
    weights_input  = st.text_input("Weights (comma-separated)", ",".join(str(w) for w in _p.weights))
    asset_class_input = st.text_input(
        "Asset classes (comma-separated)",
        ",".join(_p.asset_classes.values())
    )

    st.markdown('<div class="section-header">Date Range</div>', unsafe_allow_html=True)
    start_date = st.date_input("Start date", date.fromisoformat(_p.start_date), min_value=date(1980, 1, 1), max_value=date.today()).strftime('%Y-%m-%d')
    end_date   = st.date_input("End date",   date.today() - timedelta(days=1), min_value=date(1980, 1, 1), max_value=date.today()).strftime('%Y-%m-%d')
    st.caption(f"End date: {end_date}")

    st.markdown('<div class="section-header">Parameters</div>', unsafe_allow_html=True)
    risk_free_rate           = st.slider("Risk-free rate",           0.0, 10.0, float(_p.risk_free_rate * 100), 0.1, format="%.1f%%") / 100
    benchmark_ticker         = st.text_input("Benchmark ticker", "SPY")
    initial_investment       = st.number_input("Initial investment ($)", 1000, 10_000_000, _p.initial_investment, step=500)
    monthly_investment       = st.number_input("Monthly contribution ($)", 0, 50_000, _p.monthly_investment, step=100)
    custom_annualized_return = st.slider("Custom annual return (forecast)", 0.0, 30.0, float(_p.custom_annualized_return * 100) if _p.custom_annualized_return else 0.0, 0.5, format="%.1f%%") / 100
    safe_withdrawal_rate     = st.slider("Safe withdrawal rate (SWR)", 0.0, 10.0, float(_p.safe_withdrawal_rate * 100), 0.1, format="%.1f%%") / 100

    run = st.button("Run Analysis", type="primary", use_container_width=True)

    st.markdown('<div class="section-header">Save Configuration</div>', unsafe_allow_html=True)
    if st.button("Save changes to my_portfolio", use_container_width=True):
        content = f"""from datetime import datetime, timedelta

        tickers = {[t.strip() for t in tickers_input.split(",") if t.strip()]}
        weights = {[float(w.strip()) for w in weights_input.split(",") if w.strip()]}
        portfolio = dict(zip(tickers, weights))

        asset_classes = dict(zip(tickers, {[a.strip() for a in asset_class_input.split(",") if a.strip()]}))

        start_date = '{start_date}'
        end_date = '{end_date}'

        risk_free_rate = {risk_free_rate}
        initial_investment = {initial_investment}
        monthly_investment = {monthly_investment}
        custom_annualized_return = {custom_annualized_return}
        safe_withdrawal_rate = {safe_withdrawal_rate}
        """
        with open("my_portfolio.py", "w") as f:
            f.write(content)
        st.success("Tallennettu! Käynnistä Streamlit uudelleen ladataksesi uudet oletusarvot.")


# ── Parse inputs ─────────────────────────────────────────────────────────────
tickers      = [t.strip() for t in tickers_input.split(",") if t.strip()]
weights_raw  = [float(w.strip()) for w in weights_input.split(",") if w.strip()]
asset_classes_raw = [a.strip() for a in asset_class_input.split(",") if a.strip()]

weight_sum = sum(weights_raw)
if abs(weight_sum - 1.0) > 1e-4:
    st.sidebar.warning(f"Weights sum to {weight_sum:.4f}, not 1.0")

portfolio     = dict(zip(tickers, weights_raw))
asset_classes = dict(zip(tickers, asset_classes_raw))
weights       = np.array(weights_raw)

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("# Portfolio Analysis")
st.caption(f"Period: {start_date} to {end_date}  |  Benchmark: {benchmark_ticker}  |  Risk-free rate: {risk_free_rate:.2%}")

if not run:
    st.info("Configure your portfolio in the sidebar and click Run Analysis.")
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

# Align columns to ticker order
if len(tickers) > 1:
    available = [t for t in tickers if t in data.columns]
    data = data[available]
    w_aligned = np.array([weights_raw[tickers.index(t)] for t in available])
else:
    w_aligned = weights

# Returns
returns           = data.pct_change(fill_method=None).dropna(how='all').fillna(0)
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
tabs = st.tabs([
    "Overview",
    "Performance",
    "Risk",
    "Benchmark",
    "Allocation",
    "Correlations",
    "FI Forecast",
    "Report",
])

tab_overview, tab_perf, tab_risk, tab_bench, tab_alloc, tab_corr, tab_fi, tab_report = tabs


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
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
    ax.set_ylabel(f"Value ($)")
    ax.legend(fontsize=9)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab_perf:
    st.markdown('<div class="section-header">Daily Returns</div>', unsafe_allow_html=True)

    fig, axes = plt.subplots(3, 1, figsize=(12, 9))

    # 1. Daily returns bar
    axes[0].bar(p_ret.index, p_ret.values,
                color=np.where(p_ret.values >= 0, ACCENT, ACCENT2), width=1, alpha=0.8)
    axes[0].set_ylabel("Daily Return")
    axes[0].set_title("Daily Returns")

    # 2. Cumulative returns
    cum = (1 + p_ret).cumprod() - 1
    axes[1].plot(cum.index, cum.values * 100, color=ACCENT, linewidth=2)
    axes[1].fill_between(cum.index, 0, cum.values * 100, alpha=0.15, color=ACCENT)
    axes[1].set_ylabel("Cumulative Return (%)")
    axes[1].set_title("Cumulative Return")

    # 3. Rolling 30-day volatility
    roll_vol = p_ret.rolling(30).std() * np.sqrt(252) * 100
    axes[2].plot(roll_vol.index, roll_vol.values, color=ACCENT4, linewidth=1.5)
    axes[2].fill_between(roll_vol.index, 0, roll_vol.values, alpha=0.2, color=ACCENT4)
    axes[2].set_ylabel("Annualized Vol (%)")
    axes[2].set_title("30-Day Rolling Volatility")

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
                    annot_kws={'size': 8}, ax=ax, cbar_kws={'label': 'Return %'})
        ax.set_title("Monthly Returns (%)")
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
    ax.set_ylabel("Return (%)")
    ax.set_title("Annual Returns")
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()


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
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Underwater Chart")
    ax.legend(fontsize=9)
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
    ax.set_xlabel("Daily Return (%)")
    ax.set_ylabel("Frequency")
    ax.set_title("Return Distribution")
    ax.legend(fontsize=9)
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
with tab_bench:
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
    ax.set_ylabel("Value ($)")
    ax.set_title("Cumulative Growth Comparison")
    ax.legend(fontsize=9)
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
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(b_ret.values * 100, p_ret.values * 100,
               color=ACCENT, alpha=0.3, s=4, linewidths=0)
    xlim = max(abs(b_ret.values).max() * 100, 1)
    x_line = np.linspace(-xlim, xlim, 100)
    b_val  = m["Beta"]
    a_val  = m["Alpha (Jensen)"] / 252
    ax.plot(x_line, b_val * x_line + a_val * 100, color=ACCENT2, linewidth=1.5, label="Regression")
    ax.axhline(0, color='#444', linewidth=0.5)
    ax.axvline(0, color='#444', linewidth=0.5)
    ax.set_xlabel(f"{benchmark_ticker} Daily Return (%)")
    ax.set_ylabel("Portfolio Daily Return (%)")
    ax.set_title("Portfolio vs Benchmark")
    ax.legend(fontsize=9)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – ALLOCATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_alloc:
    st.markdown('<div class="section-header">Portfolio Weights</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Keyword-based group colors — anything matching a keyword gets this base color
    ASSET_GROUP_COLORS = [
        (['etf', 'stocks', 'fund', 'index', 'tracker', 'ishares', 'vanguard',
          'msci', 'sp500', 's&p', 'nasdaq', 'dow', 'russell', 'country etf',
          'sector etf', 'bond etf', 'equity etf', 'eft'],       '#3498db'),  # blue
        (['stock', 'equity', 'share', 'growth', 'value', 'small cap',
          'mid cap', 'large cap', 'dividend'],                    '#e74c3c'),  # red
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
          'nzdusd', 'usd', 'eur', 'gbp', 'jpy', 'chf'],          '#2ecc71'),  # green
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

    def get_ticker_colors(ticker_list, asset_classes_dict):
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
            for idx, t in enumerate(group_tickers):
                if n == 1:
                    new_h, new_s, new_v = h, s, v
                else:
                    # Spread hue up to ±25° and vary brightness significantly
                    hue_spread = 0.10  # ~25 degrees in 0-1 scale
                    new_h = (h + (idx - (n-1)/2) * hue_spread / max(n-1, 1)) % 1.0
                    new_s = min(1.0, max(0.4, s - idx * 0.10))
                    new_v = min(1.0, max(0.5, v + (idx * 0.20) - ((n-1) * 0.09)))
                nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
                ticker_color_map[t] = '#{:02x}{:02x}{:02x}'.format(
                    int(nr * 255), int(ng * 255), int(nb * 255))
        return [ticker_color_map[t] for t in ticker_list]

    def draw_pie(ax, sizes, labels, colors, title):
        """Draw a pie chart with labels+percentages in a legend, no overlapping text."""
        wedges, _ = ax.pie(
            sizes,
            colors=colors,
            startangle=140,
            wedgeprops=dict(linewidth=2, edgecolor='#0f0f0f'),
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
        ticker_colors = get_ticker_colors(tickers, asset_classes)
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
with tab_corr:
    st.markdown('<div class="section-header">Correlation Matrix</div>', unsafe_allow_html=True)

    monthly_r = (1 + returns).resample('ME').prod() - 1
    corr_mat  = round(monthly_r.corr(), 2)

    fig, ax = plt.subplots(figsize=(max(5, len(tickers)), max(4, len(tickers) - 1)))
    sns.heatmap(corr_mat, annot=True, fmt=".2f", cmap='coolwarm',
                vmin=-1, vmax=1, linewidths=0.5, linecolor='#0f0f0f',
                annot_kws={'size': 10}, ax=ax,
                cbar_kws={'label': 'Correlation'})
    ax.set_title("Monthly Return Correlation")
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    if len(tickers) >= 2:
        st.markdown('<div class="section-header">36-Month Rolling Correlation</div>', unsafe_allow_html=True)
        window_size = st.slider("Rolling window (months)", 6, 60, 36)
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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 – FI FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab_fi:
    st.markdown('<div class="section-header">Financial Independence Forecast</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        lean_fi  = st.number_input("Lean FI annual spend ($k)",  10, 500, 50)
    with col2:
        safe_fi  = st.number_input("Safe FI annual spend ($k)",  10, 500, 100)
    with col3:
        cozy_fi  = st.number_input("Cozy FI annual spend ($k)",  10, 500, 175)

    hist_return = ann_return(p_ret)
    use_return  = custom_annualized_return if custom_annualized_return > 0 else hist_return

    # Project 40 years
    months      = 40 * 12
    values      = [initial_investment / 1000]
    monthly_ret = (1 + use_return) ** (1/12) - 1
    for _ in range(months):
        values.append(values[-1] * (1 + monthly_ret) + monthly_investment / 1000)

    from datetime import date
    proj_dates = pd.date_range(datetime.today(), periods=months + 1, freq='MS')
    proj_series = pd.Series(values, index=proj_dates)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(proj_series.index, proj_series.values,
            color=ACCENT, linewidth=2, label="Projected Net Worth")
    ax.fill_between(proj_series.index, 0, proj_series.values, alpha=0.1, color=ACCENT)

    if safe_withdrawal_rate > 0:
        for target, label, color in [
            (lean_fi / safe_withdrawal_rate, f"Lean FI (${lean_fi}k/yr)", ACCENT3),
            (safe_fi / safe_withdrawal_rate, f"Safe FI (${safe_fi}k/yr)", ACCENT),
            (cozy_fi / safe_withdrawal_rate, f"Cozy FI (${cozy_fi}k/yr)", ACCENT4),
        ]:
            ax.axhline(target, color=color, linewidth=1.5, linestyle='--', label=label)
            # Mark crossing
            cross = proj_series[proj_series >= target]
            if not cross.empty:
                ax.scatter([cross.index[0]], [cross.iloc[0]],
                           color=color, s=60, zorder=5)

    ax.set_ylabel("Net Worth ($k)")
    ax.set_title(f"40-Year Forecast — {use_return:.1%} annual return, ${monthly_investment}/month contribution")
    ax.legend(fontsize=9)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    # FI table
    if safe_withdrawal_rate > 0:
        st.markdown('<div class="section-header">FI Goals</div>', unsafe_allow_html=True)
        fi_rows = []
        for label, spend in [("Lean", lean_fi), ("Safe", safe_fi), ("Cozy", cozy_fi)]:
            target = spend / safe_withdrawal_rate
            cross  = proj_series[proj_series >= target]
            years  = (cross.index[0] - datetime.today()).days / 365 if not cross.empty else None
            fi_rows.append({
                "Goal":              label,
                "Annual Spend ($k)": spend,
                "Required NW ($k)":  f"{target:.0f}",
                "Years to Goal":     f"{years:.1f}" if years else "40+ years",
            })
        st.dataframe(pd.DataFrame(fi_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Set Safe Withdrawal Rate > 0 in the sidebar to see FI goals.")

    # Monte Carlo
    st.markdown('<div class="section-header">Monte Carlo Simulation (500 paths)</div>', unsafe_allow_html=True)
    n_sim    = 500
    n_months = 20 * 12
    mc_paths = []
    mu_m     = (1 + use_return) ** (1/12) - 1
    sig_m    = ann_vol(p_ret) / np.sqrt(12)
    for _ in range(n_sim):
        path = [initial_investment / 1000]
        for _ in range(n_months):
            r = np.random.normal(mu_m, sig_m)
            path.append(path[-1] * (1 + r) + monthly_investment / 1000)
        mc_paths.append(path)

    mc_arr   = np.array(mc_paths)
    mc_dates = pd.date_range(datetime.today(), periods=n_months + 1, freq='MS')

    fig, ax = plt.subplots(figsize=(12, 5))
    for path in mc_paths[:100]:
        ax.plot(mc_dates, path, alpha=0.05, color=ACCENT, linewidth=0.8)
    p10  = np.percentile(mc_arr, 10,  axis=0)
    p50  = np.percentile(mc_arr, 50,  axis=0)
    p90  = np.percentile(mc_arr, 90,  axis=0)
    ax.plot(mc_dates, p50, color=ACCENT,  linewidth=2, label="Median")
    ax.plot(mc_dates, p10, color=ACCENT2, linewidth=1.5, linestyle='--', label="10th pct")
    ax.plot(mc_dates, p90, color=ACCENT3, linewidth=1.5, linestyle='--', label="90th pct")
    ax.fill_between(mc_dates, p10, p90, alpha=0.1, color=ACCENT)
    ax.set_ylabel("Net Worth ($k)")
    ax.set_title("20-Year Monte Carlo Simulation")
    ax.legend(fontsize=9)
    apply_style(fig, [ax])
    st.pyplot(fig)
    plt.close()

    st.caption(f"Final value at 20 years — Median: ${p50[-1]:.0f}k  |  10th pct: ${p10[-1]:.0f}k  |  90th pct: ${p90[-1]:.0f}k")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 – REPORT
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
    st.markdown('<div class="section-header">QuantStats HTML Report</div>', unsafe_allow_html=True)
    if st.button("Generate QuantStats Report"):
        with st.spinner("Generating report..."):
            try:
                tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
                qs.reports.html(p_ret, benchmark=b_ret, output=tmp.name, title="Portfolio Report")
                with open(tmp.name, "r", encoding="utf-8") as f:
                    html_content = f.read()
                os.unlink(tmp.name)
                st.download_button(
                    "Download QuantStats HTML Report",
                    html_content.encode(),
                    "portfolio_report.html",
                    "text/html"
                )
                st.success("Report ready — click above to download.")
            except Exception as e:
                st.error(f"QuantStats report failed: {e}")
