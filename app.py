"""
FTSE Follow the Green Scanner — v2
====================================
Single-file Streamlit app for UK (and US) long-term investors.
Uses Felix's "Follow the Money" methodology.

Run:   streamlit run app.py
Deps:  pip install streamlit yfinance pandas plotly numpy

New in v2
---------
1. S&P 500 top-50 + Sector ETFs alongside FTSE 100
2. Sector Rotation heatmap tab (vs parent index)
3. Cross-Market tab (FTSE sectors vs S&P equivalents)
4. Risk/Reward columns integrated into every scan results row
5. BACKLOG_NOTES — manual contract/order-book tags per ticker
6. Exit-signal warnings (Momentum Fading, Volume Drying, Overextended)
"""

# ── Imports ────────────────────────────────────────────────────────────────────
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import datetime
import io

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FTSE Follow the Green Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS – Dark Theme ────────────────────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
    }
    .main { background-color: #0e1117; }
    [data-testid="metric-container"] {
        background: #1c2333;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 14px 18px;
    }
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #90cdf4;
        border-left: 4px solid #3182ce;
        padding-left: 10px;
        margin: 20px 0 12px 0;
    }
    .risk-box {
        background: #1a2744;
        border: 1px solid #3182ce;
        border-radius: 10px;
        padding: 18px;
        margin-top: 10px;
        line-height: 1.7;
    }
    .banner-bullish {
        background: #1a472a; border: 1px solid #2f855a;
        border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;
    }
    .banner-bearish {
        background: #4a1818; border: 1px solid #9b2c2c;
        border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;
    }
    .banner-neutral {
        background: #2d3748; border: 1px solid #4a5568;
        border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;
    }
    @media (max-width: 768px) {
        [data-testid="metric-container"] { padding: 10px 12px; }
        .risk-box { padding: 12px; }
    }
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# BACKLOG NOTES
# Add ticker: "note" pairs here. A 📋 icon will appear in the results table.
# ─────────────────────────────────────────────────────────────────────────────

BACKLOG_NOTES = {
    "RR.L":  "£7.3B backlog, Power Systems orders +50% YoY",
    "UU.L":  "£11.5B AMP8 programme, £800M equity raise",
    "BA.L":  "Record order book, multi-year defence contracts",
    "PWR":   "$44B backlog, 3 years revenue locked in",
    "LMT":   "F-35 production + classified programmes backlog $160B+",
    "RTX":   "Pratt & Whitney GTF engine services multi-decade",
    "NOC":   "B-21 Raider low-rate initial production",
    "ANTO.L":"Copper growth pipeline: Zaldívar + Los Pelambres expansion",
    "GLEN.L":"Cobalt + copper for EV battery transition",
    "NG.L":  "£60B 5-year capex plan for grid transition",
}

# ─────────────────────────────────────────────────────────────────────────────
# FTSE 100 CONSTITUENTS  (tickers end in .L for Yahoo Finance / LSE)
# ─────────────────────────────────────────────────────────────────────────────

FTSE_100 = {
    "3i Group": "III.L",
    "Admiral Group": "ADM.L",
    "Anglo American": "AAL.L",
    "Antofagasta": "ANTO.L",
    "Ashtead Group": "AHT.L",
    "Associated British Foods": "ABF.L",
    "AstraZeneca": "AZN.L",
    "Auto Trader Group": "AUTO.L",
    "Aviva": "AV.L",
    "BAE Systems": "BA.L",
    "Barclays": "BARC.L",
    "Barratt Redrow": "BTRW.L",
    "Beazley": "BEZ.L",
    "BP": "BP.L",
    "British Land": "BLND.L",
    "BT Group": "BT-A.L",
    "Bunzl": "BNZL.L",
    "Burberry Group": "BRBY.L",
    "Carnival": "CCL.L",
    "Centrica": "CNA.L",
    "Compass Group": "CPG.L",
    "ConvaTec Group": "CTEC.L",
    "Croda International": "CRDA.L",
    "DCC": "DCC.L",
    "Diageo": "DGE.L",
    "Entain": "ENT.L",
    "Experian": "EXPN.L",
    "Ferguson Enterprises": "FERG.L",
    "Fresnillo": "FRES.L",
    "GSK": "GSK.L",
    "Glencore": "GLEN.L",
    "Haleon": "HLN.L",
    "Hargreaves Lansdown": "HL.L",
    "HSBC Holdings": "HSBA.L",
    "IAG": "IAG.L",
    "ICG (Intermediate Capital)": "ICG.L",
    "IMI": "IMI.L",
    "Imperial Brands": "IMB.L",
    "Informa": "INF.L",
    "InterContinental Hotels": "IHG.L",
    "Intertek Group": "ITRK.L",
    "JD Sports Fashion": "JD.L",
    "Land Securities": "LAND.L",
    "Legal & General": "LGEN.L",
    "Lloyds Banking Group": "LLOY.L",
    "London Stock Exchange Group": "LSEG.L",
    "M&G": "MNG.L",
    "Marks & Spencer": "MKS.L",
    "Melrose Industries": "MRO.L",
    "Mondi": "MNDI.L",
    "National Grid": "NG.L",
    "NatWest Group": "NWG.L",
    "Next": "NXT.L",
    "Ocado Group": "OCDO.L",
    "Pearson": "PSON.L",
    "Persimmon": "PSN.L",
    "Phoenix Group": "PHNX.L",
    "Prudential": "PRU.L",
    "Reckitt Benckiser": "RKT.L",
    "RELX": "REL.L",
    "Rentokil Initial": "RTO.L",
    "Rio Tinto": "RIO.L",
    "Rolls-Royce Holdings": "RR.L",
    "RS Group": "RS1.L",
    "Sage Group": "SGE.L",
    "Schroders": "SDR.L",
    "Scottish Mortgage IT": "SMT.L",
    "Segro": "SGRO.L",
    "Shell": "SHEL.L",
    "Smith & Nephew": "SN.L",
    "Smiths Group": "SMIN.L",
    "Smurfit Westrock": "SWR.L",
    "Spirax Group": "SPX.L",
    "SSE": "SSE.L",
    "St James's Place": "STJ.L",
    "Standard Chartered": "STAN.L",
    "Taylor Wimpey": "TW.L",
    "Tesco": "TSCO.L",
    "Unilever": "ULVR.L",
    "United Utilities": "UU.L",
    "Vistry Group": "VTY.L",
    "Vodafone Group": "VOD.L",
    "Whitbread": "WTB.L",
    "Wise": "WISE.L",
    "WPP": "WPP.L",
}

# ─────────────────────────────────────────────────────────────────────────────
# S&P 500 TOP-50 BY MARKET CAP  (no .L suffix — US tickers)
# ─────────────────────────────────────────────────────────────────────────────

SP500_TOP50 = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "Alphabet (A)": "GOOGL",
    "Amazon": "AMZN",
    "Meta Platforms": "META",
    "Berkshire Hathaway": "BRK-B",
    "Tesla": "TSLA",
    "Broadcom": "AVGO",
    "JPMorgan Chase": "JPM",
    "Eli Lilly": "LLY",
    "Visa": "V",
    "UnitedHealth": "UNH",
    "ExxonMobil": "XOM",
    "Mastercard": "MA",
    "Johnson & Johnson": "JNJ",
    "Costco": "COST",
    "Procter & Gamble": "PG",
    "Home Depot": "HD",
    "Netflix": "NFLX",
    "Salesforce": "CRM",
    "Advanced Micro Devices": "AMD",
    "Abbott Labs": "ABT",
    "Chevron": "CVX",
    "Wells Fargo": "WFC",
    "Merck": "MRK",
    "AbbVie": "ABBV",
    "Goldman Sachs": "GS",
    "Pepsico": "PEP",
    "Coca-Cola": "KO",
    "Palantir": "PLTR",
    "Caterpillar": "CAT",
    "BlackRock": "BLK",
    "Lockheed Martin": "LMT",
    "Raytheon Technologies": "RTX",
    "Northrop Grumman": "NOC",
    "General Dynamics": "GD",
    "Freeport-McMoRan": "FCX",
    "Newmont": "NEM",
    "NextEra Energy": "NEE",
    "Duke Energy": "DUK",
    "Southern Company": "SO",
    "Bank of America": "BAC",
    "Citigroup": "C",
    "Morgan Stanley": "MS",
    "Qualcomm": "QCOM",
    "Texas Instruments": "TXN",
    "Applied Materials": "AMAT",
    "ServiceNow": "NOW",
    "Palo Alto Networks": "PANW",
}

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR ETFs
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_ETFS = {
    "SPDR S&P 500": "SPY",
    "iShares S&P 500": "IVV",
    "Vanguard S&P 500": "VOO",
    "Financials (XLF)": "XLF",
    "Industrials (XLI)": "XLI",
    "Energy (XLE)": "XLE",
    "Technology (XLK)": "XLK",
    "Healthcare (XLV)": "XLV",
    "Semiconductors (SMH)": "SMH",
    "Gold Miners (GDX)": "GDX",
    "Copper Miners (COPX)": "COPX",
}

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR MAPPINGS
# Each ticker maps to one of the canonical sector names.
# Used for the Sector Rotation heatmap and Cross-Market tabs.
# ─────────────────────────────────────────────────────────────────────────────

FTSE_SECTORS = {
    # Defence
    "BA.L": "Defence", "RR.L": "Defence", "QQ.L": "Defence",
    # Mining / Materials
    "AAL.L": "Mining", "ANTO.L": "Mining", "FRES.L": "Mining",
    "GLEN.L": "Mining", "RIO.L": "Mining", "MNDI.L": "Mining",
    "CRDA.L": "Materials",
    # Utilities
    "NG.L": "Utilities", "UU.L": "Utilities", "SSE.L": "Utilities",
    "CNA.L": "Utilities",
    # Energy
    "BP.L": "Energy", "SHEL.L": "Energy",
    # Financials
    "HSBA.L": "Financials", "BARC.L": "Financials", "LLOY.L": "Financials",
    "NWG.L": "Financials", "STAN.L": "Financials", "LSEG.L": "Financials",
    "AV.L": "Financials", "LGEN.L": "Financials", "PHNX.L": "Financials",
    "PRU.L": "Financials", "ICG.L": "Financials", "HL.L": "Financials",
    "III.L": "Financials", "ADM.L": "Financials", "BEZ.L": "Financials",
    "MNG.L": "Financials", "SDR.L": "Financials", "STJ.L": "Financials",
    # Technology
    "AUTO.L": "Technology", "EXPN.L": "Technology", "REL.L": "Technology",
    "SGE.L": "Technology", "INF.L": "Technology", "WISE.L": "Technology",
    # Healthcare
    "AZN.L": "Healthcare", "GSK.L": "Healthcare", "HLN.L": "Healthcare",
    "SN.L": "Healthcare", "RKT.L": "Healthcare", "CTEC.L": "Healthcare",
    # Consumer
    "TSCO.L": "Consumer", "MKS.L": "Consumer", "NXT.L": "Consumer",
    "DGE.L": "Consumer", "ABF.L": "Consumer", "BRBY.L": "Consumer",
    "IHG.L": "Consumer", "WTB.L": "Consumer", "CPG.L": "Consumer",
    "CCL.L": "Consumer", "OCDO.L": "Consumer", "JD.L": "Consumer",
    "ENT.L": "Consumer",
    # Industrials
    "AHT.L": "Industrials", "BNZL.L": "Industrials", "BT-A.L": "Telecom",
    "DCC.L": "Industrials", "FERG.L": "Industrials", "IMI.L": "Industrials",
    "ITRK.L": "Industrials", "PSON.L": "Industrials", "RS1.L": "Industrials",
    "SMIN.L": "Industrials", "SPX.L": "Industrials", "SWR.L": "Industrials",
    "TW.L": "Industrials", "BTRW.L": "Industrials", "PSN.L": "Industrials",
    "VTY.L": "Industrials", "MRO.L": "Industrials", "SGRO.L": "Real Estate",
    "BLND.L": "Real Estate", "LAND.L": "Real Estate",
    "ULVR.L": "Consumer", "WPP.L": "Consumer", "SMT.L": "Technology",
    "VOD.L": "Telecom",
}

SP500_SECTORS = {
    # Defence
    "LMT": "Defence", "RTX": "Defence", "NOC": "Defence", "GD": "Defence",
    # Mining / Materials
    "FCX": "Mining", "NEM": "Mining",
    # Utilities
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities",
    # Energy
    "XOM": "Energy", "CVX": "Energy",
    # Financials
    "JPM": "Financials", "GS": "Financials", "BAC": "Financials",
    "C": "Financials", "MS": "Financials", "WFC": "Financials",
    "V": "Financials", "MA": "Financials", "BLK": "Financials",
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Technology", "META": "Technology", "AVGO": "Technology",
    "AMD": "Technology", "QCOM": "Technology", "TXN": "Technology",
    "AMAT": "Technology", "NOW": "Technology", "PANW": "Technology",
    "CRM": "Technology", "PLTR": "Technology",
    # Healthcare
    "LLY": "Healthcare", "UNH": "Healthcare", "JNJ": "Healthcare",
    "MRK": "Healthcare", "ABBV": "Healthcare", "ABT": "Healthcare",
    # Consumer
    "AMZN": "Consumer", "TSLA": "Consumer", "COST": "Consumer",
    "PG": "Consumer", "HD": "Consumer", "NFLX": "Consumer",
    "PEP": "Consumer", "KO": "Consumer",
    # Industrials
    "CAT": "Industrials",
    # Diversified
    "BRK-B": "Financials",
}

# Cross-market pairs: (UK group label, UK tickers, US group label, US tickers)
CROSS_MARKET_PAIRS = [
    ("UK Defence",    ["BA.L", "RR.L"],
     "US Defence",    ["LMT", "RTX", "GD", "NOC"]),
    ("UK Mining",     ["GLEN.L", "RIO.L", "AAL.L", "ANTO.L"],
     "US Materials",  ["FCX", "NEM"]),
    ("UK Utilities",  ["UU.L", "NG.L", "SSE.L"],
     "US Utilities",  ["NEE", "DUK", "SO"]),
    ("UK Energy",     ["SHEL.L", "BP.L"],
     "US Energy",     ["XOM", "CVX"]),
    ("UK Financials", ["HSBA.L", "BARC.L", "STAN.L"],
     "US Financials", ["JPM", "GS", "BAC"]),
]

# Reference index tickers for each universe
INDEX_TICKERS = {
    "FTSE 100":    "^FTSE",
    "S&P 500":     "^GSPC",
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(ticker: str, days: int = 400) -> pd.DataFrame | None:
    """
    Fetch daily OHLCV. Handles both LSE (.L) and US tickers transparently.
    Returns None on any failure.
    """
    try:
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=days + 100)

        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            progress=False,
            auto_adjust=True,
            multi_level_index=False,
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in required):
            return None

        df = df[required].copy()
        df.dropna(subset=["Close", "Volume"], inplace=True)
        return df.tail(days)

    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_returns(ticker: str, periods: list[int]) -> dict:
    """
    Fetch percentage returns over the given calendar-day periods.
    periods = list of ints e.g. [7, 30, 90, 180]
    Returns dict {period: pct_return} or empty dict on failure.
    """
    try:
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=max(periods) + 30)
        df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(),
                         progress=False, auto_adjust=True, multi_level_index=False)
        if df is None or df.empty:
            return {}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return {}

        result = {}
        latest = float(df["Close"].iloc[-1])
        for p in periods:
            cutoff = end - datetime.timedelta(days=p)
            past = df[df.index.date <= cutoff]
            if past.empty:
                continue
            past_price = float(past["Close"].iloc[-1])
            result[p] = ((latest - past_price) / past_price) * 100
        return result
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# P/E RATIO FETCHER
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pe_ratio(ticker: str) -> float | None:
    """
    Fetch trailing P/E ratio from yfinance ticker.info['trailingPE'].

    Returns:
        float  — the trailing P/E if available and positive
        None   — if missing, negative, or any network/parsing error

    Cached for 1 hour alongside OHLCV data. Negative P/E values (loss-making
    companies) are normalised to None so they are excluded from sector averages.
    """
    try:
        info = yf.Ticker(ticker).info
        pe = info.get("trailingPE", None)
        if pe is None:
            return None
        pe_float = float(pe)
        # Negative or absurdly large P/E (>500) is meaningless — treat as N/A
        if pe_float <= 0 or pe_float > 500:
            return None
        return round(pe_float, 1)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    SMA50, Vol_MA20, Vol_Ratio, Vol_5d_Trend, Dist_SMA50_Pct.
    Also computes rolling Money Flow Score history (for exit-signal detection).
    """
    df = df.copy()

    # ── SMA50: trend filter (Felix's primary rule) ────────────────────────────
    df["SMA50"] = df["Close"].rolling(window=50, min_periods=50).mean()

    # ── 20-day average volume: baseline for spike detection ──────────────────
    df["Vol_MA20"] = df["Volume"].rolling(window=20, min_periods=20).mean()

    # ── Volume ratio: today vs 20-day average ────────────────────────────────
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA20"].replace(0, float("nan"))

    # ── 5-day volume trend: is volume sustained or just a one-day spike? ─────
    df["Vol_5d_Trend"] = (
        df["Volume"]
        .rolling(window=5, min_periods=5)
        .apply(lambda x: 1.0 if float(x.iloc[-1]) > float(x.iloc[0]) else 0.0, raw=False)
    )

    # ── % distance from SMA50 ────────────────────────────────────────────────
    df["Dist_SMA50_Pct"] = ((df["Close"] - df["SMA50"]) / df["SMA50"]) * 100

    return df


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bullish Accumulation  : Close > SMA50 AND Vol_Ratio > 1.5 AND rising 5d vol
    Bearish Distribution  : Close < SMA50 AND Vol_Ratio > 1.5
    """
    df = df.copy()
    df["Signal"]  = "Neutral"
    df["Bullish"] = False
    df["Bearish"] = False

    bullish_mask = (
        (df["Close"] > df["SMA50"])
        & (df["Vol_Ratio"] > 1.5)
        & (df["Vol_5d_Trend"] == 1.0)
    )
    df.loc[bullish_mask, "Signal"]  = "Bullish Accumulation"
    df.loc[bullish_mask, "Bullish"] = True

    bearish_mask = (
        (df["Close"] < df["SMA50"])
        & (df["Vol_Ratio"] > 1.5)
    )
    df.loc[bearish_mask, "Signal"]  = "Bearish Distribution"
    df.loc[bearish_mask, "Bearish"] = True

    return df


# ─────────────────────────────────────────────────────────────────────────────
# MONEY FLOW SCORE  (0 – 100)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_money_flow_score(row: pd.Series) -> int:
    """
    Composite 0–100 score:
      Trend    (0–50 pts) — how far above/below SMA50
      Volume   (0–35 pts) — size of volume spike
      Momentum (0–15 pts) — 5-day rising volume trend
    """
    score = 0.0

    dist = row.get("Dist_SMA50_Pct", 0.0)
    if pd.notna(dist):
        score += max(0.0, min(50.0, 25.0 + dist * 2.5))

    vol_ratio = row.get("Vol_Ratio", 1.0)
    if pd.notna(vol_ratio) and vol_ratio > 1.0:
        score += max(0.0, min(35.0, ((vol_ratio - 1.0) / 2.0) * 35.0))

    if pd.notna(row.get("Vol_5d_Trend")) and row.get("Vol_5d_Trend") == 1.0:
        score += 15.0

    return int(max(0, min(100, round(score))))


# ─────────────────────────────────────────────────────────────────────────────
# EXIT-SIGNAL WARNINGS  (new in v2)
# ─────────────────────────────────────────────────────────────────────────────

def detect_exit_warnings(df: pd.DataFrame) -> list[str]:
    """
    Given a fully-calculated DataFrame, return a list of exit-warning strings
    for the LATEST row.

    Three checks:
    1. Momentum Fading  — MFS > 70 in last 10 days but now < 50
    2. Volume Drying    — Vol_Ratio > 1.5 in last 10 days but now < 1.0 for 3+ days
    3. Overextended     — Price > 15% above SMA50
    """
    warnings = []
    if len(df) < 10:
        return warnings

    recent = df.tail(10).copy()

    # Compute rolling MFS for the last 10 rows
    recent_mfs = recent.apply(calculate_money_flow_score, axis=1)
    current_mfs = int(recent_mfs.iloc[-1])
    past_max_mfs = int(recent_mfs.iloc[:-1].max()) if len(recent_mfs) > 1 else 0

    # 1. Momentum Fading
    if past_max_mfs >= 70 and current_mfs < 50:
        warnings.append("⚠️ Momentum Fading")

    # 2. Volume Drying — last 3 rows all have Vol_Ratio < 1.0,
    #    AND at least one of the prior 7 had Vol_Ratio > 1.5
    if len(recent) >= 3:
        last3_dry    = (recent["Vol_Ratio"].iloc[-3:] < 1.0).all()
        prior7_spike = (recent["Vol_Ratio"].iloc[:-3] > 1.5).any()
        if last3_dry and prior7_spike:
            warnings.append("⚠️ Volume Drying")

    # 3. Overextended — price > 15% above SMA50
    latest = df.iloc[-1]
    dist   = latest.get("Dist_SMA50_Pct", 0.0)
    if pd.notna(dist) and dist > 15.0:
        warnings.append("⚠️ Extended")

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# POSITION SIZING  (Felix's 1% Rule)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_position_size(
    price: float,
    risk_gbp: float = 750.0,
    stop_loss_pct: float = 0.10,
    currency: str = "£",
) -> dict:
    """
    price       — current price in pence (UK) OR dollars (US).
    risk_gbp    — max cash at risk per trade.
    stop_loss_pct — fractional stop distance (0.10 = 10%).
    currency    — symbol prefix for display.
    """
    # For UK tickers price is in pence; convert to £ for maths
    if currency == "£":
        price_main = price / 100.0
    else:
        price_main = price

    risk_per_unit = price_main * stop_loss_pct
    if risk_per_unit == 0:
        return {}

    num_units      = risk_gbp / risk_per_unit
    position_value = num_units * price_main
    stop_price     = price_main * (1.0 - stop_loss_pct)
    reward_target  = position_value * (stop_loss_pct * 2)

    return {
        "Entry":          f"{price:.2f}{'p' if currency == '£' else '$'}",
        "Stop Loss":      f"{stop_price * (100 if currency == '£' else 1):.2f}{'p' if currency == '£' else '$'}",
        "Stop %":         f"{stop_loss_pct * 100:.0f}%",
        "Max Units":      f"{int(num_units):,}",
        "Position Value": f"{currency}{position_value:,.0f}",
        "Max Risk":       f"{currency}{risk_gbp:,.0f}",
        "2:1 Target":     f"{currency}{reward_target:,.0f}",
    }


def stop_loss_price_str(price: float, stop_pct: float, currency: str = "£") -> str:
    """Compact stop-loss price for the results table."""
    if currency == "£":
        stop = (price / 100.0) * (1.0 - stop_pct)
        return f"{stop * 100:.1f}p"
    return f"${price * (1.0 - stop_pct):.2f}"


def max_shares_str(price: float, risk: float, stop_pct: float, currency: str = "£") -> str:
    price_main = (price / 100.0) if currency == "£" else price
    rpu = price_main * stop_pct
    if rpu == 0:
        return "—"
    return f"{int(risk / rpu):,}"


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDER  (unchanged from v1)
# ─────────────────────────────────────────────────────────────────────────────

def build_chart(df: pd.DataFrame, ticker: str, company_name: str = "") -> go.Figure:
    title = f"{company_name} ({ticker})" if company_name else ticker

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.70, 0.30],
        subplot_titles=["", "Volume"],
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color="#00c853", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00c853",  decreasing_fillcolor="#ff1744",
        whiskerwidth=0.4,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["SMA50"], name="SMA 50",
        line=dict(color="#2196f3", width=2.5), opacity=0.95,
        hovertemplate="SMA50: %{y:.2f}<extra></extra>",
    ), row=1, col=1)

    bullish_days = df[df["Bullish"] == True]
    if not bullish_days.empty:
        fig.add_trace(go.Scatter(
            x=bullish_days.index, y=bullish_days["Low"] * 0.975,
            mode="markers", name="Bullish Accumulation",
            marker=dict(symbol="arrow-up", size=13, color="#00e676",
                        line=dict(color="#ffffff", width=1.5)),
            hovertemplate=(
                "<b>🟢 Bullish Accumulation</b><br>Date: %{x|%d %b %Y}<br>"
                "Close: %{customdata[0]:.2f}<br>Vol Ratio: %{customdata[1]:.2f}×<br>"
                "vs SMA50: %{customdata[2]:+.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                bullish_days["Close"],
                bullish_days["Vol_Ratio"].fillna(0),
                bullish_days["Dist_SMA50_Pct"].fillna(0),
            )),
        ), row=1, col=1)

    bearish_days = df[df["Bearish"] == True]
    if not bearish_days.empty:
        fig.add_trace(go.Scatter(
            x=bearish_days.index, y=bearish_days["High"] * 1.025,
            mode="markers", name="Bearish Distribution",
            marker=dict(symbol="arrow-down", size=13, color="#ff5252",
                        line=dict(color="#ffffff", width=1.5)),
            hovertemplate=(
                "<b>🔴 Bearish Distribution</b><br>Date: %{x|%d %b %Y}<br>"
                "Close: %{customdata[0]:.2f}<br>Vol Ratio: %{customdata[1]:.2f}×<br>"
                "vs SMA50: %{customdata[2]:+.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                bearish_days["Close"],
                bearish_days["Vol_Ratio"].fillna(0),
                bearish_days["Dist_SMA50_Pct"].fillna(0),
            )),
        ), row=1, col=1)

    volume_colors = [
        "#00c853" if (pd.notna(r) and r > 1.5) else "#ef5350"
        for r in df["Vol_Ratio"].fillna(0)
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume",
        marker_color=volume_colors, opacity=0.75,
        hovertemplate="Date: %{x|%d %b %Y}<br>Volume: %{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Vol_MA20"], name="Vol MA20",
        line=dict(color="#ffa726", width=1.5, dash="dot"), opacity=0.8,
        hovertemplate="20d Avg Vol: %{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    signal_window = df.tail(90)
    for idx, row_data in signal_window.iterrows():
        if row_data.get("Bullish"):
            fig.add_vrect(x0=idx, x1=idx,
                          fillcolor="rgba(0,200,83,0.12)", layer="below", line_width=0)
        elif row_data.get("Bearish"):
            fig.add_vrect(x0=idx, x1=idx,
                          fillcolor="rgba(255,23,68,0.10)", layer="below", line_width=0)

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>   |   FTSE Follow the Green Scanner",
                   font=dict(size=15, color="#e2e8f0"), x=0.01),
        paper_bgcolor="#0e1117", plot_bgcolor="#161b27",
        font=dict(color="#a0aec0", size=11),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0,
                    bgcolor="rgba(22,27,39,0.85)", bordercolor="#2d3748", borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=10, r=15, t=65, b=10),
        hovermode="x unified", height=640,
    )
    fig.update_xaxes(gridcolor="#1f2937", showgrid=True, zeroline=False,
                     showspikes=True, spikecolor="#4a5568", spikemode="across",
                     spikethickness=1, spikesnap="cursor")
    fig.update_yaxes(gridcolor="#1f2937", showgrid=True, zeroline=False)
    fig.update_yaxes(tickformat=".3s", row=2, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-TICKER SCANNER
# ─────────────────────────────────────────────────────────────────────────────

def scan_tickers(
    ticker_dict: dict,
    risk_gbp: float = 750.0,
    stop_pct: float = 0.10,
    currency: str = "£",
) -> pd.DataFrame:
    """
    Scan all tickers. Returns one row per ticker with:
      signal, MFS, vol ratio, % from SMA50,
      stop loss price, R:R ratio (always 2:1), max shares,
      backlog note flag, exit warnings,
      trailing P/E, sector avg P/E, and 💎 Value+Flow flag.
    """
    # Combined sector lookup (FTSE + S&P)
    all_sectors = {**FTSE_SECTORS, **SP500_SECTORS}

    results = []
    tickers = list(ticker_dict.items())
    total   = len(tickers)

    progress_bar = st.progress(0, text="Initialising scanner...")
    status_text  = st.empty()

    for i, (company, ticker) in enumerate(tickers):
        pct = (i + 1) / total
        progress_bar.progress(pct, text=f"Scanning {ticker}  ({i+1}/{total})")
        status_text.markdown(
            f"<small style='color:#718096;'>Loading: {ticker} — {company}</small>",
            unsafe_allow_html=True,
        )

        df = fetch_ohlcv(ticker)

        base = {
            "Company": company, "Ticker": ticker,
            "Price": None, "Signal": "No Data",
            "Warnings": "", "Notes": "",
            "% from SMA50": None, "20d Avg Vol": None,
            "Vol Ratio": None, "Money Flow Score": None,
            "Stop Loss": "—", "R:R": "2:1", "Max Units": "—",
            "Trailing P/E": None, "Sector": all_sectors.get(ticker, "Other"),
            "Sector Avg P/E": None, "💎 Value+Flow": "",
        }

        if df is None or len(df) < 55:
            results.append(base)
            continue

        try:
            df  = calculate_indicators(df)
            df  = detect_signals(df)
            latest = df.iloc[-1]
            mfs    = calculate_money_flow_score(latest)
            warns  = detect_exit_warnings(df)
            note   = "📋 " + BACKLOG_NOTES[ticker] if ticker in BACKLOG_NOTES else ""
            pe     = fetch_pe_ratio(ticker)   # None if unavailable

            price = float(latest["Close"])
            dist  = float(latest["Dist_SMA50_Pct"]) if pd.notna(latest["Dist_SMA50_Pct"]) else None

            results.append({
                "Company":          company,
                "Ticker":           ticker,
                "Price":            round(price, 2),
                "Signal":           str(latest["Signal"]),
                "Warnings":         " | ".join(warns),
                "Notes":            note,
                "% from SMA50":     round(dist, 2) if dist is not None else None,
                "20d Avg Vol":      int(latest["Vol_MA20"]) if pd.notna(latest["Vol_MA20"]) else None,
                "Vol Ratio":        round(float(latest["Vol_Ratio"]), 2) if pd.notna(latest["Vol_Ratio"]) else None,
                "Money Flow Score": mfs,
                "Stop Loss":        stop_loss_price_str(price, stop_pct, currency),
                "R:R":              "2:1",
                "Max Units":        max_shares_str(price, risk_gbp, stop_pct, currency),
                "Trailing P/E":     pe,
                "Sector":           all_sectors.get(ticker, "Other"),
                "Sector Avg P/E":   None,   # filled in post-loop
                "💎 Value+Flow":    "",      # filled in post-loop
            })

        except Exception:
            base["Signal"] = "Error"
            results.append(base)

    progress_bar.empty()
    status_text.empty()

    df_out = pd.DataFrame(results)

    # ── Post-loop: compute Sector Avg P/E and 💎 Value+Flow flag ─────────────
    # Sector Avg P/E: mean of valid (non-None) P/E values within each sector group.
    # Only stocks with real P/E data contribute to the average.
    if not df_out.empty and "Trailing P/E" in df_out.columns:
        sector_pe_map: dict[str, float] = {}
        for sector, grp in df_out.groupby("Sector"):
            valid_pes = grp["Trailing P/E"].dropna()
            valid_pes = valid_pes[valid_pes > 0]
            if not valid_pes.empty:
                sector_pe_map[sector] = round(float(valid_pes.mean()), 1)

        def _sector_avg(row: pd.Series) -> float | None:
            return sector_pe_map.get(row["Sector"], None)

        def _value_flow_flag(row: pd.Series) -> str:
            """
            💎 Value + Flow: Institution are buying (MFS > 60) BUT the stock is
            still cheaper than its sector peers (P/E below sector avg).
            This is the sweet spot: smart money accumulating before the re-rating.
            """
            pe      = row["Trailing P/E"]
            avg_pe  = row["Sector Avg P/E"]
            mfs     = row["Money Flow Score"]
            if (
                pe is not None and avg_pe is not None
                and pd.notna(pe) and pd.notna(avg_pe)
                and float(pe) < float(avg_pe)
                and mfs is not None and pd.notna(mfs)
                and int(mfs) >= 60
            ):
                return "💎 Value+Flow"
            return ""

        df_out["Sector Avg P/E"] = df_out.apply(_sector_avg, axis=1)
        df_out["💎 Value+Flow"]  = df_out.apply(_value_flow_flag, axis=1)

    return df_out


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR ROTATION HEATMAP  (new in v2)
# ─────────────────────────────────────────────────────────────────────────────

def build_sector_heatmap(
    sector_map: dict,
    ticker_dict: dict,
    index_ticker: str,
    universe_label: str,
) -> go.Figure:
    """
    Build a Plotly heatmap showing sector performance vs the parent index
    over 1w, 1m, 3m periods.

    Colour: green = outperforming, red = underperforming.
    The 'excess return' = sector avg return - index return.
    """
    periods      = [7, 30, 90]
    period_labels = ["1 Week", "1 Month", "3 Months"]

    # Fetch index returns
    idx_returns = fetch_returns(index_ticker, periods)

    # Group tickers by sector
    sector_tickers: dict[str, list[str]] = {}
    for ticker in ticker_dict.values():
        sector = sector_map.get(ticker, "Other")
        sector_tickers.setdefault(sector, []).append(ticker)

    sectors_list = sorted(sector_tickers.keys())

    heatmap_z     = []   # excess return matrix
    heatmap_text  = []   # annotation text

    status = st.empty()
    for sector in sectors_list:
        row_z    = []
        row_text = []
        tickers_in_sector = sector_tickers[sector]

        for p, label in zip(periods, period_labels):
            idx_ret = idx_returns.get(p, None)
            rets    = []
            for t in tickers_in_sector:
                r = fetch_returns(t, [p])
                if p in r and r[p] is not None:
                    rets.append(r[p])
                status.markdown(
                    f"<small style='color:#4a5568;'>Loading {label} data for {sector}…</small>",
                    unsafe_allow_html=True,
                )

            if not rets or idx_ret is None:
                row_z.append(None)
                row_text.append("n/a")
            else:
                avg_sector = float(np.mean(rets))
                excess     = avg_sector - float(idx_ret)
                row_z.append(round(excess, 2))
                row_text.append(f"{excess:+.1f}%<br>(sect {avg_sector:+.1f}%)")

        heatmap_z.append(row_z)
        heatmap_text.append(row_text)

    status.empty()

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_z,
        x=period_labels,
        y=sectors_list,
        text=heatmap_text,
        texttemplate="%{text}",
        colorscale=[
            [0.0, "#7f1d1d"],   # deep red  (underperform)
            [0.4, "#ef4444"],
            [0.5, "#2d3748"],   # neutral
            [0.6, "#22c55e"],
            [1.0, "#14532d"],   # deep green (outperform)
        ],
        zmid=0,
        colorbar=dict(
            title="Excess Return vs Index (%)",
            titlefont=dict(color="#a0aec0"),
            tickfont=dict(color="#a0aec0"),
        ),
        hovertemplate=(
            "<b>%{y} — %{x}</b><br>"
            "Excess vs " + universe_label + ": %{z:+.2f}%<extra></extra>"
        ),
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>Sector Rotation vs {universe_label}</b>   |   "
                 f"Green = outperforming index, Red = underperforming",
            font=dict(size=14, color="#e2e8f0"), x=0.01,
        ),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b27",
        font=dict(color="#a0aec0", size=11),
        height=max(350, len(sectors_list) * 42 + 120),
        margin=dict(l=120, r=20, t=80, b=40),
    )
    fig.update_xaxes(tickfont=dict(color="#e2e8f0"))
    fig.update_yaxes(tickfont=dict(color="#e2e8f0"))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-MARKET COMPARISON  (new in v2)
# ─────────────────────────────────────────────────────────────────────────────

def build_cross_market_chart(periods: list[int] = None) -> go.Figure:
    """
    Side-by-side bar chart comparing FTSE sector groups vs S&P equivalents
    over 1w, 1m, 3m, 6m.  Colours: blue = FTSE, orange = S&P.

    When the S&P bar leads the FTSE bar for the same sector, it's a potential
    lead-indicator that the FTSE equivalent may follow.
    """
    if periods is None:
        periods = [7, 30, 90, 180]
    period_labels = ["1 Week", "1 Month", "3 Months", "6 Months"]

    status = st.empty()
    rows = []

    for (uk_label, uk_tickers, us_label, us_tickers) in CROSS_MARKET_PAIRS:
        for p, plabel in zip(periods, period_labels):
            # UK group avg
            uk_rets = []
            for t in uk_tickers:
                r = fetch_returns(t, [p])
                if p in r:
                    uk_rets.append(r[p])
                status.markdown(
                    f"<small style='color:#4a5568;'>Fetching {t} ({plabel})…</small>",
                    unsafe_allow_html=True,
                )
            # US group avg
            us_rets = []
            for t in us_tickers:
                r = fetch_returns(t, [p])
                if p in r:
                    us_rets.append(r[p])
                status.markdown(
                    f"<small style='color:#4a5568;'>Fetching {t} ({plabel})…</small>",
                    unsafe_allow_html=True,
                )

            if uk_rets:
                rows.append({"Group": uk_label, "Period": plabel,
                             "Return (%)": round(float(np.mean(uk_rets)), 2),
                             "Market": "🇬🇧 FTSE"})
            if us_rets:
                rows.append({"Group": us_label, "Period": plabel,
                             "Return (%)": round(float(np.mean(us_rets)), 2),
                             "Market": "🇺🇸 S&P 500"})

    status.empty()

    if not rows:
        return go.Figure()

    df_plot = pd.DataFrame(rows)

    # One subplot per period
    fig = make_subplots(
        rows=1, cols=len(periods),
        subplot_titles=period_labels,
        shared_yaxes=False,
    )

    colours = {"🇬🇧 FTSE": "#3182ce", "🇺🇸 S&P 500": "#f6ad55"}
    shown   = set()

    for col_i, (p, plabel) in enumerate(zip(periods, period_labels), start=1):
        sub = df_plot[df_plot["Period"] == plabel]
        for market, colour in colours.items():
            msub = sub[sub["Market"] == market]
            show_legend = market not in shown
            shown.add(market)
            fig.add_trace(go.Bar(
                x=msub["Group"],
                y=msub["Return (%)"],
                name=market,
                marker_color=colour,
                opacity=0.85,
                showlegend=show_legend,
                legendgroup=market,
                hovertemplate="%{x}<br>Return: %{y:+.2f}%<extra>" + market + "</extra>",
            ), row=1, col=col_i)

    fig.update_layout(
        title=dict(
            text="<b>Cross-Market Comparison</b>   |   "
                 "S&P leading FTSE = potential FTSE entry signal",
            font=dict(size=14, color="#e2e8f0"), x=0.01,
        ),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b27",
        font=dict(color="#a0aec0", size=11),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                    bgcolor="rgba(22,27,39,0.85)", font=dict(size=11)),
        margin=dict(l=20, r=20, t=90, b=80),
        height=460,
    )
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=9))
    fig.update_yaxes(gridcolor="#1f2937", zeroline=True, zerolinecolor="#4a5568",
                     ticksuffix="%")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a2744 0%,#121827 100%);
                padding:22px 26px;border-radius:12px;margin-bottom:22px;
                border:1px solid #2d3748;">
        <h1 style="margin:0 0 6px 0;color:#90cdf4;font-size:1.75rem;font-weight:800;">
            📈 FTSE Follow the Green Scanner
        </h1>
        <p style="margin:0;color:#718096;font-size:0.92rem;line-height:1.5;">
            Institutional money flow · FTSE 100 &amp; S&amp;P 500 · Sector Rotation ·
            Cross-Market Signals<br>
            <span style="color:#4a5568;font-size:0.82rem;">
            ⚠️ Educational tool only — not financial advice.
            </span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        st.markdown("---")

        scan_mode = st.radio(
            "Scan Mode",
            ["🔎 Single Stock", "🇬🇧 FTSE 100", "🇺🇸 S&P 500",
             "📊 Sector ETFs", "🌍 Cross-Market", "📋 Custom List"],
            index=0,
        )

        selected_tickers: dict = {}
        currency = "£"

        if scan_mode == "🔎 Single Stock":
            all_stocks = {
                **{f"[FTSE] {k}": v for k, v in FTSE_100.items()},
                **{f"[S&P]  {k}": v for k, v in SP500_TOP50.items()},
                **{f"[ETF]  {k}": v for k, v in SECTOR_ETFS.items()},
            }
            company_list = sorted(all_stocks.keys())
            default_idx  = next(
                (i for i, k in enumerate(company_list) if "AstraZeneca" in k), 0
            )
            sel = st.selectbox("Select stock", company_list, index=default_idx)
            manual = st.text_input(
                "Or enter any ticker", placeholder="AAPL / SHEL.L",
                label_visibility="collapsed"
            ).strip().upper()
            if manual:
                if "." not in manual and not manual.endswith(".L"):
                    currency = "$"
                else:
                    currency = "£"
                selected_tickers = {manual: manual}
            else:
                ticker_val = all_stocks[sel]
                currency   = "£" if ticker_val.endswith(".L") else "$"
                selected_tickers = {sel: ticker_val}

        elif scan_mode == "🇬🇧 FTSE 100":
            selected_tickers = FTSE_100.copy()
            currency = "£"
            st.success(f"✅ {len(selected_tickers)} FTSE 100 stocks")

        elif scan_mode == "🇺🇸 S&P 500":
            selected_tickers = SP500_TOP50.copy()
            currency = "$"
            st.success(f"✅ {len(selected_tickers)} S&P 500 stocks")

        elif scan_mode == "📊 Sector ETFs":
            selected_tickers = SECTOR_ETFS.copy()
            currency = "$"
            st.success(f"✅ {len(selected_tickers)} ETFs")

        elif scan_mode == "🌍 Cross-Market":
            # Handled in its own tab — no normal scan
            pass

        else:  # Custom List
            uploaded = st.file_uploader("Upload .txt / .csv", type=["txt", "csv"])
            pasted   = st.text_area("Or paste tickers (one per line)", height=140,
                                    placeholder="BARC.L\nLLOY.L\nAAPL\nNVDA")
            raw = []
            if uploaded:
                raw = [t.strip().upper() for t in uploaded.read().decode().splitlines() if t.strip()]
            elif pasted:
                raw = [t.strip().upper() for t in pasted.splitlines() if t.strip()]
            selected_tickers = {t: t for t in raw}
            currency = "$" if raw and not raw[0].endswith(".L") else "£"
            if selected_tickers:
                st.success(f"✅ {len(selected_tickers)} tickers loaded")

        st.markdown("---")
        st.markdown("### 🔍 Filter & Sort")
        filter_mode = st.selectbox(
            "Filter", ["Show All", "🟢 Bullish Only", "🔴 Bearish Only",
                       "⚠️ Warnings Only", "⚪ Neutral Only"]
        )
        sort_by = st.selectbox(
            "Sort By",
            ["Money Flow Score ↓", "Volume Ratio ↓", "% above SMA50 ↓", "Company A→Z"]
        )

        st.markdown("---")
        st.markdown("### 💰 Risk Management")
        risk_amount   = st.number_input("Max risk per trade (£/$)", min_value=50,
                                        max_value=50000, value=750, step=50)
        stop_loss_pct = st.slider("Stop loss %", min_value=2, max_value=25, value=10) / 100.0

        st.markdown("---")
        st.markdown("""
        <div style="color:#4a5568;font-size:0.78rem;line-height:1.6;">
        <b style="color:#718096;">Felix's 5 Rules:</b><br>
        1. Price above SMA50<br>
        2. Volume spike &gt;1.5× avg<br>
        3. Rising 5-day volume trend<br>
        4. Risk ≤1% per trade<br>
        5. Target 2:1 reward-to-risk<br><br>
        <em>"Follow the green — follow the money."</em>
        </div>
        """, unsafe_allow_html=True)

    # ── Guard ──────────────────────────────────────────────────────────────────
    if scan_mode != "🌍 Cross-Market" and not selected_tickers:
        st.info("👈 Select tickers in the sidebar to begin.")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════════════════════════
    tab_scanner, tab_sector, tab_cross = st.tabs(
        ["📡 Scanner", "🌡️ Sector Rotation", "🌍 Cross-Market"]
    )

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1 — SCANNER
    # ──────────────────────────────────────────────────────────────────────────
    with tab_scanner:

        is_single = (scan_mode == "🔎 Single Stock") or (
            scan_mode == "📋 Custom List" and len(selected_tickers) == 1
        )

        # ── SINGLE STOCK VIEW ─────────────────────────────────────────────────
        if is_single:
            company_name, ticker = list(selected_tickers.items())[0]

            with st.spinner(f"Loading **{ticker}**…"):
                df = fetch_ohlcv(ticker)

            if df is None or df.empty:
                st.error(f"❌ No data for **{ticker}**. Check the symbol and try again.")
                return
            if len(df) < 55:
                st.warning(f"⚠️ Only {len(df)} days of data for {ticker} — need ≥55.")
                return

            df     = calculate_indicators(df)
            df     = detect_signals(df)
            latest = df.iloc[-1]
            prev   = df.iloc[-2] if len(df) > 1 else latest
            mfs    = calculate_money_flow_score(latest)
            warns  = detect_exit_warnings(df)
            signal = str(latest["Signal"])
            pe_val = fetch_pe_ratio(ticker)

            # Signal banner
            if signal == "Bullish Accumulation":
                st.markdown(f"""
                <div class="banner-bullish">
                    <div style="font-size:1.2rem;font-weight:800;color:#68d391;">
                        🟢 BULLISH ACCUMULATION — {ticker}
                    </div>
                    <div style="margin-top:6px;color:#9ae6b4;font-size:0.9rem;line-height:1.6;">
                        Price <b>above SMA50</b> · Volume
                        <b>{float(latest['Vol_Ratio']):.1f}× the 20-day average</b> ·
                        Volume rising 5 days<br>
                        <em>"Institutions are loading up. Follow the green."</em>
                    </div>
                </div>""", unsafe_allow_html=True)
            elif signal == "Bearish Distribution":
                st.markdown(f"""
                <div class="banner-bearish">
                    <div style="font-size:1.2rem;font-weight:800;color:#fc8181;">
                        🔴 BEARISH DISTRIBUTION — {ticker}
                    </div>
                    <div style="margin-top:6px;color:#feb2b2;font-size:0.9rem;line-height:1.6;">
                        Price <b>below SMA50</b> with volume spike
                        <b>{float(latest['Vol_Ratio']):.1f}×</b><br>
                        <em>"Smart money is exiting. Avoid new longs."</em>
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="banner-neutral">
                    <div style="font-size:1.1rem;font-weight:700;color:#a0aec0;">
                        ⚪ NEUTRAL — {ticker}
                    </div>
                    <div style="margin-top:4px;color:#718096;font-size:0.88rem;">
                        No unusual volume spike or trend confirmation.
                        <em>"When in doubt, stay out."</em>
                    </div>
                </div>""", unsafe_allow_html=True)

            # Exit warnings
            if warns:
                for w in warns:
                    st.warning(w)

            # Backlog note
            if ticker in BACKLOG_NOTES:
                st.info(f"📋 **Backlog / Contract Note:** {BACKLOG_NOTES[ticker]}")

            # Metrics row
            col1, col2, col3, col4, col5 = st.columns(5)
            day_chg = ((float(latest["Close"]) / float(prev["Close"])) - 1.0) * 100
            col1.metric("Price", f"{float(latest['Close']):.2f}{'p' if currency == '£' else '$'}",
                        delta=f"{day_chg:+.2f}%",
                        delta_color="normal" if day_chg >= 0 else "inverse")

            dist = float(latest["Dist_SMA50_Pct"]) if pd.notna(latest["Dist_SMA50_Pct"]) else 0.0
            col2.metric("vs SMA50", f"{dist:+.1f}%",
                        delta="Above trend" if dist > 0 else "Below trend",
                        delta_color="normal" if dist > 0 else "inverse")

            vr = float(latest["Vol_Ratio"]) if pd.notna(latest["Vol_Ratio"]) else 0.0
            col3.metric("Vol Ratio", f"{vr:.2f}×",
                        delta="🟢 SPIKE" if vr > 1.5 else "Normal",
                        delta_color="normal" if vr > 1.5 else "off")

            avg_vol = int(latest["Vol_MA20"]) if pd.notna(latest["Vol_MA20"]) else 0
            col4.metric("20d Avg Vol", f"{avg_vol:,}")

            score_lbl = "Strong 🔥" if mfs >= 70 else ("Moderate" if mfs >= 40 else "Weak ❄️")
            col5.metric("Money Flow Score", f"{mfs}/100", delta=score_lbl,
                        delta_color="normal" if mfs >= 70 else ("off" if mfs >= 40 else "inverse"))

            # Chart
            fig = build_chart(df, ticker, company_name)
            st.plotly_chart(fig, use_container_width=True)

            # Summary + Risk side by side
            st.markdown('<div class="section-header">📊 Signal Summary & Position Sizing</div>',
                        unsafe_allow_html=True)
            col_t1, col_t2 = st.columns(2)

            with col_t1:
                # Sector avg P/E for this single stock
                all_sectors_map = {**FTSE_SECTORS, **SP500_SECTORS}
                this_sector     = all_sectors_map.get(ticker, "Other")
                pe_display      = f"{pe_val:.1f}" if pe_val is not None else "N/A"

                summary = pd.DataFrame({
                    "Metric": ["Signal", "Close", "SMA50", "% from SMA50",
                               "Volume", "20d Avg Vol", "Vol Ratio", "Vol 5d Trend",
                               "Money Flow Score", "Trailing P/E", "Sector",
                               "Exit Warnings"],
                    "Value": [
                        signal,
                        f"{float(latest['Close']):.2f}{'p' if currency == '£' else '$'}",
                        f"{float(latest['SMA50']):.2f}" if pd.notna(latest["SMA50"]) else "N/A",
                        f"{dist:+.2f}%",
                        f"{int(latest['Volume']):,}",
                        f"{avg_vol:,}",
                        f"{vr:.2f}×",
                        "Rising ↑" if latest.get("Vol_5d_Trend") == 1.0 else "Flat/Falling ↓",
                        f"{mfs}/100 — {score_lbl}",
                        pe_display,
                        this_sector,
                        " | ".join(warns) if warns else "None",
                    ],
                })
                st.dataframe(summary, use_container_width=True, hide_index=True)

            with col_t2:
                risk_data = calculate_position_size(float(latest["Close"]),
                                                    risk_amount, stop_loss_pct, currency)
                rows_html = "".join(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:4px 0;border-bottom:1px solid #2d3748;">'
                    f'<span style="color:#718096;font-size:0.88rem;">{k}</span>'
                    f'<span style="color:#e2e8f0;font-weight:600;font-size:0.88rem;">{v}</span>'
                    f'</div>'
                    for k, v in risk_data.items()
                )
                st.markdown(f"""
                <div class="risk-box">
                    <div style="color:#90cdf4;font-weight:700;font-size:1rem;margin-bottom:10px;">
                        💰 Position Sizing — Felix's 1% Rule
                    </div>
                    {rows_html}
                    <div style="color:#4a5568;font-size:0.78rem;margin-top:10px;line-height:1.5;">
                        Max loss if price drops {stop_loss_pct*100:.0f}% to stop =
                        {currency}{risk_amount:,}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Signal history
            st.markdown('<div class="section-header">📋 Signal History (Last 60 Days)</div>',
                        unsafe_allow_html=True)
            hist = (df[df["Signal"] != "Neutral"]
                    .tail(60)[["Close", "Volume", "Vol_Ratio", "Dist_SMA50_Pct", "Signal"]]
                    .copy())
            if hist.empty:
                st.info("No bullish/bearish signals in the last 60 days.")
            else:
                hist.index = pd.to_datetime(hist.index).strftime("%d %b %Y")
                hist.columns = ["Close", "Volume", "Vol Ratio", "% from SMA50", "Signal"]
                hist = hist.round(2).iloc[::-1]
                st.dataframe(hist, use_container_width=True,
                             column_config={
                                 "Vol Ratio": st.column_config.NumberColumn(format="%.2f×"),
                                 "% from SMA50": st.column_config.NumberColumn(format="%+.2f%%"),
                                 "Volume": st.column_config.NumberColumn(format="%,d"),
                             })

            # Export
            st.markdown('<div class="section-header">📥 Export</div>', unsafe_allow_html=True)
            exp = df[["Open", "High", "Low", "Close", "Volume", "SMA50",
                      "Vol_MA20", "Vol_Ratio", "Dist_SMA50_Pct", "Signal"]].copy()
            exp.index.name = "Date"
            buf = io.StringIO(); exp.to_csv(buf)
            st.download_button("⬇️ Export to CSV", buf.getvalue(),
                               f"{ticker}_{datetime.date.today()}.csv", "text/csv")

        # ── MULTI-TICKER VIEW ─────────────────────────────────────────────────
        else:
            if scan_mode == "🌍 Cross-Market":
                st.info("Switch to the 🌍 Cross-Market tab to see that view.")
                return

            st.markdown(
                f'<div class="section-header">🔍 Scanning {len(selected_tickers)} Stocks</div>',
                unsafe_allow_html=True,
            )

            results_df = scan_tickers(selected_tickers, risk_amount, stop_loss_pct, currency)

            if results_df.empty:
                st.error("No results returned.")
                return

            valid_df   = results_df[~results_df["Signal"].isin(["No Data", "Error"])]
            bullish_n  = int((valid_df["Signal"] == "Bullish Accumulation").sum())
            bearish_n  = int((valid_df["Signal"] == "Bearish Distribution").sum())
            neutral_n  = int((valid_df["Signal"] == "Neutral").sum())
            warnings_n = int((valid_df["Warnings"] != "").sum())

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Scanned", len(valid_df))
            c2.metric("🟢 Bullish", bullish_n)
            c3.metric("🔴 Bearish", bearish_n)
            c4.metric("⚪ Neutral", neutral_n)
            c5.metric("⚠️ Warnings", warnings_n)

            st.markdown("---")

            # Filters
            filtered = results_df.copy()
            if filter_mode == "🟢 Bullish Only":
                filtered = filtered[filtered["Signal"] == "Bullish Accumulation"]
            elif filter_mode == "🔴 Bearish Only":
                filtered = filtered[filtered["Signal"] == "Bearish Distribution"]
            elif filter_mode == "⚠️ Warnings Only":
                filtered = filtered[filtered["Warnings"] != ""]
            elif filter_mode == "⚪ Neutral Only":
                filtered = filtered[filtered["Signal"] == "Neutral"]

            # Sort
            if sort_by == "Money Flow Score ↓":
                filtered = filtered.sort_values("Money Flow Score", ascending=False, na_position="last")
            elif sort_by == "Volume Ratio ↓":
                filtered = filtered.sort_values("Vol Ratio", ascending=False, na_position="last")
            elif sort_by == "% above SMA50 ↓":
                filtered = filtered.sort_values("% from SMA50", ascending=False, na_position="last")
            elif sort_by == "Company A→Z":
                filtered = filtered.sort_values("Company")

            st.markdown(f"**{len(filtered)} of {len(results_df)} tickers shown**")

            if not filtered.empty:
                # Column order for display
                display_cols = [
                    "Company", "Ticker", "Price", "Signal", "Warnings",
                    "💎 Value+Flow", "Money Flow Score", "Vol Ratio",
                    "% from SMA50", "Trailing P/E", "Sector Avg P/E",
                    "Stop Loss", "R:R", "Max Units", "20d Avg Vol", "Notes",
                ]
                show_df = filtered[[c for c in display_cols if c in filtered.columns]].copy()

                st.dataframe(
                    show_df,
                    use_container_width=True,
                    height=min(600, 65 + len(show_df) * 38),
                    hide_index=True,
                    column_config={
                        "Signal": st.column_config.TextColumn("Signal", width="medium"),
                        "Warnings": st.column_config.TextColumn("Warnings", width="medium"),
                        "💎 Value+Flow": st.column_config.TextColumn("💎 Value+Flow", width="medium"),
                        "Notes": st.column_config.TextColumn("📋 Notes", width="large"),
                        "% from SMA50": st.column_config.NumberColumn(format="%+.2f%%"),
                        "Vol Ratio": st.column_config.NumberColumn(format="%.2f×"),
                        "Money Flow Score": st.column_config.ProgressColumn(
                            "MF Score", min_value=0, max_value=100, format="%d", width="medium"
                        ),
                        "Price": st.column_config.NumberColumn(format="%.2f"),
                        "20d Avg Vol": st.column_config.NumberColumn(format="%,d"),
                        "Trailing P/E": st.column_config.NumberColumn(
                            "P/E (Trail.)", format="%.1f"
                        ),
                        "Sector Avg P/E": st.column_config.NumberColumn(
                            "Sector Avg P/E", format="%.1f"
                        ),
                    },
                )

                # Export
                st.markdown('<div class="section-header">📥 Export</div>', unsafe_allow_html=True)
                col_dl, _ = st.columns([1, 3])
                with col_dl:
                    buf = io.StringIO(); filtered.to_csv(buf, index=False)
                    st.download_button("⬇️ Export to CSV", buf.getvalue(),
                                       f"signals_{datetime.date.today()}.csv", "text/csv",
                                       use_container_width=True)

                # Drill-down chart
                st.markdown('<div class="section-header">📊 View Detailed Chart</div>',
                            unsafe_allow_html=True)
                chartable = filtered[~filtered["Signal"].isin(["No Data", "Error"])]
                if not chartable.empty:
                    labels = [
                        f"{r['Company']}  ({r['Ticker']})  — {r['Signal']}  |  Score: {r['Money Flow Score']}"
                        for _, r in chartable.iterrows()
                    ]
                    sel_label = st.selectbox("Select stock to chart:", labels)
                    if sel_label:
                        chart_ticker  = sel_label.split("(")[1].split(")")[0].strip()
                        chart_company = sel_label.split("(")[0].strip()
                        with st.spinner(f"Loading {chart_ticker}…"):
                            cdf = fetch_ohlcv(chart_ticker)
                        if cdf is not None and len(cdf) >= 55:
                            cdf = calculate_indicators(cdf)
                            cdf = detect_signals(cdf)
                            st.plotly_chart(build_chart(cdf, chart_ticker, chart_company),
                                            use_container_width=True)
                            # Risk for charted stock
                            ccy = "£" if chart_ticker.endswith(".L") else "$"
                            risk_data = calculate_position_size(
                                float(cdf.iloc[-1]["Close"]), risk_amount, stop_loss_pct, ccy
                            )
                            rows_html = "".join(
                                f'<div style="display:flex;justify-content:space-between;'
                                f'padding:4px 0;border-bottom:1px solid #2d3748;">'
                                f'<span style="color:#718096;font-size:0.88rem;">{k}</span>'
                                f'<span style="color:#e2e8f0;font-weight:600;font-size:0.88rem;">{v}</span>'
                                f'</div>'
                                for k, v in risk_data.items()
                            )
                            col_r, _ = st.columns([1, 1])
                            with col_r:
                                st.markdown(f"""
                                <div class="risk-box">
                                    <div style="color:#90cdf4;font-weight:700;margin-bottom:10px;">
                                        💰 Position Sizing — {chart_company}
                                    </div>
                                    {rows_html}
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.warning(f"Not enough data to chart {chart_ticker}.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2 — SECTOR ROTATION HEATMAP
    # ──────────────────────────────────────────────────────────────────────────
    with tab_sector:
        st.markdown("""
        <div class="section-header">🌡️ Sector Rotation vs Parent Index</div>
        """, unsafe_allow_html=True)

        st.markdown("""
        **How to read this:** Each cell shows how much a sector is outperforming (+) or
        underperforming (−) its parent index. **Green = smart money rotating in.
        Red = smart money rotating out.**

        > Felix's insight: *"If a sector is up 50% while the index is up 3%,
        institutions positioned months ago."* — This heatmap makes that instantly visible.
        """)

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            universe_choice = st.selectbox(
                "Universe", ["FTSE 100", "S&P 500"], key="sector_universe"
            )

        if universe_choice == "FTSE 100":
            sec_map     = FTSE_SECTORS
            tick_dict   = FTSE_100
            idx_ticker  = INDEX_TICKERS["FTSE 100"]
        else:
            sec_map     = SP500_SECTORS
            tick_dict   = SP500_TOP50
            idx_ticker  = INDEX_TICKERS["S&P 500"]

        run_heat = st.button("🔄 Run Sector Heatmap", key="run_heat",
                             help="Fetches returns for every ticker — takes ~60 seconds")
        if run_heat:
            with st.spinner("Building sector rotation heatmap…"):
                heat_fig = build_sector_heatmap(sec_map, tick_dict, idx_ticker, universe_choice)
            st.plotly_chart(heat_fig, use_container_width=True)

            st.markdown("""
            **Interpretation guide:**
            - **Dark green (+5% or more)** — sector strongly outperforming; institutional rotation in
            - **Light green (0–5%)** — mild outperformance; worth watching
            - **Red** — underperformance; institutions rotating out
            - **Look for sectors outperforming over 1m AND 3m** — sustained conviction, not noise
            """)
        else:
            st.info("👆 Click **Run Sector Heatmap** to fetch live performance data.")
            st.markdown("""
            *Note: The first run fetches ~80–100 return series from Yahoo Finance.
            Results are cached for 1 hour — subsequent runs are instant.*
            """)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3 — CROSS-MARKET COMPARISON
    # ──────────────────────────────────────────────────────────────────────────
    with tab_cross:
        st.markdown('<div class="section-header">🌍 Cross-Market Comparison</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        Comparing equivalent sectors between the FTSE 100 and S&P 500.

        **Key signal:** When the US sector consistently leads the UK equivalent,
        institutions have already positioned in the US. The UK version may follow —
        potentially offering an earlier entry with more upside remaining.

        > *"The US market is 6–12 months ahead. Watch what sectors are moving there,
        then find the FTSE equivalent."* — Felix's Cross-Market Rule
        """)

        pairs_to_show = st.multiselect(
            "Sector pairs to compare",
            options=[p[0] + " vs " + p[2] for p in CROSS_MARKET_PAIRS],
            default=[p[0] + " vs " + p[2] for p in CROSS_MARKET_PAIRS],
            key="cross_pairs",
        )

        run_cross = st.button("🔄 Run Cross-Market Analysis", key="run_cross")
        if run_cross:
            with st.spinner("Fetching cross-market data…"):
                cross_fig = build_cross_market_chart()
            st.plotly_chart(cross_fig, use_container_width=True)

            # Detailed table
            st.markdown('<div class="section-header">📋 Detailed Return Table</div>',
                        unsafe_allow_html=True)
            periods = [7, 30, 90, 180]
            plabels = ["1W", "1M", "3M", "6M"]
            table_rows = []
            status2 = st.empty()
            for (uk_lbl, uk_ticks, us_lbl, us_ticks) in CROSS_MARKET_PAIRS:
                if not any(uk_lbl in p for p in pairs_to_show):
                    continue
                for grp_label, grp_ticks, market in [(uk_lbl, uk_ticks, "🇬🇧 FTSE"),
                                                      (us_lbl, us_ticks, "🇺🇸 S&P")]:
                    row: dict = {"Group": grp_label, "Market": market}
                    for p, pl in zip(periods, plabels):
                        rets = []
                        for t in grp_ticks:
                            r = fetch_returns(t, [p])
                            if p in r:
                                rets.append(r[p])
                            status2.markdown(
                                f"<small style='color:#4a5568;'>Loading {t}…</small>",
                                unsafe_allow_html=True
                            )
                        row[pl] = round(float(np.mean(rets)), 2) if rets else None
                    table_rows.append(row)
            status2.empty()

            if table_rows:
                tbl = pd.DataFrame(table_rows)
                st.dataframe(
                    tbl,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        pl: st.column_config.NumberColumn(pl, format="%+.2f%%")
                        for pl in plabels
                    },
                )

            st.markdown("""
            **Reading the table:**
            - Find rows where the 🇺🇸 S&P return is significantly **higher** than the 🇬🇧 FTSE row
              for the same sector over 3M and 6M
            - That divergence = US is leading → FTSE equivalent may be a buying opportunity
            - Combine with a Bullish Accumulation signal in the Scanner tab for confirmation
            """)
        else:
            st.info("👆 Click **Run Cross-Market Analysis** to fetch live comparison data.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
