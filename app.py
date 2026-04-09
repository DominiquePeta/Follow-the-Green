import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import io

# ── Page Config (must be the very first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="FTSE Follow the Green Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS – Dark Theme ────────────────────────────────────────────────────
st.markdown(
    """
<style>
    /* Global */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
    }
    .main { background-color: #0e1117; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1c2333;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 14px 18px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #90cdf4;
        border-left: 4px solid #3182ce;
        padding-left: 10px;
        margin: 20px 0 12px 0;
    }

    /* Risk info box */
    .risk-box {
        background: #1a2744;
        border: 1px solid #3182ce;
        border-radius: 10px;
        padding: 18px;
        margin-top: 10px;
        line-height: 1.7;
    }

    /* Signal banners */
    .banner-bullish {
        background: #1a472a;
        border: 1px solid #2f855a;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
    }
    .banner-bearish {
        background: #4a1818;
        border: 1px solid #9b2c2c;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
    }
    .banner-neutral {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
    }

    /* Mobile responsive tweaks */
    @media (max-width: 768px) {
        [data-testid="metric-container"] { padding: 10px 12px; }
        .risk-box { padding: 12px; }
    }

    /* Dataframe polish */
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# FTSE 100 CONSTITUENTS
# Note: The FTSE 100 is reviewed quarterly. This list is accurate as of 2025.
# All tickers use the '.L' suffix for London Stock Exchange on Yahoo Finance.
# If a ticker returns no data, the scanner will skip it gracefully.
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
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(ticker: str, days: int = 400) -> pd.DataFrame | None:
    """
    Fetch daily OHLCV (Open, High, Low, Close, Volume) data via yfinance.

    We pull 400 days because:
      - SMA50 needs 50 days of data to produce its first value
      - 20-day avg volume needs 20 days
      - We want ~6 months of chart history for visual context
      - Buffer added for weekends/bank holidays (actual trading days < calendar days)

    Returns None if the ticker is invalid, has no data, or the network call fails.
    Cache is set to 1 hour so the app doesn't re-fetch on every interaction.
    """
    try:
        end = datetime.date.today()
        # Fetch extra calendar days to account for weekends & holidays
        start = end - datetime.timedelta(days=days + 100)

        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            progress=False,
            auto_adjust=True,   # Adjusts for splits & dividends automatically
            multi_level_index=False,  # Flatten columns for single ticker
        )

        if df is None or df.empty:
            return None

        # yfinance sometimes returns MultiIndex columns even for single tickers
        # depending on version — normalise here
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in required_cols):
            return None

        df = df[required_cols].copy()
        df.dropna(subset=["Close", "Volume"], inplace=True)

        # Keep only the last `days` trading sessions so the chart isn't cluttered
        df = df.tail(days)

        return df

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATOR CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators used in Felix's "Follow the Green" method.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  INDICATOR 1 — SMA50 (50-Day Simple Moving Average)                    │
    │  Felix uses the 50 SMA as the primary TREND FILTER.                    │
    │  → Price ABOVE SMA50 = uptrend  → only consider long trades here       │
    │  → Price BELOW SMA50 = downtrend → stay out or expect more weakness    │
    │  Why SMA50? It smooths out short-term noise while still being          │
    │  responsive enough to catch medium-term trend changes.                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  INDICATOR 2 — Vol_MA20 (20-Day Average Volume)                        │
    │  Establishes the "normal" level of trading activity.                   │
    │  A self-adjusting baseline — if a stock naturally trades more in       │
    │  summer, the average adjusts, so spikes are always meaningful.         │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  INDICATOR 3 — Vol_Ratio (Today's Volume / 20-Day Average)             │
    │  This is the KEY signal metric. A ratio > 1.5 means volume is         │
    │  50% above normal — clear sign of unusual institutional participation. │
    │  Felix's threshold: 1.5× minimum; ideally 2×+ for strongest signals.  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  INDICATOR 4 — Vol_5d_Trend (Is volume rising over 5 days?)           │
    │  A single volume spike can be noise (ex-dividend date, index           │
    │  rebalancing, one large trade). A 5-day rising trend = sustained       │
    │  accumulation by institutions loading a position over multiple days.   │
    └─────────────────────────────────────────────────────────────────────────┘
    """
    df = df.copy()

    # ── SMA50: 50-day Simple Moving Average on Close price ────────────────────
    df["SMA50"] = df["Close"].rolling(window=50, min_periods=50).mean()

    # ── Vol_MA20: 20-day rolling average volume ───────────────────────────────
    df["Vol_MA20"] = df["Volume"].rolling(window=20, min_periods=20).mean()

    # ── Vol_Ratio: current volume relative to the 20-day average ─────────────
    # Guard against division by zero on days with no volume data
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA20"].replace(0, float("nan"))

    # ── Vol_5d_Trend: is volume higher at day 5 than day 1? ─────────────────
    # Simple but effective: compares the last day vs the first day of the window.
    # Returns 1.0 if trend is up, 0.0 if flat or down.
    df["Vol_5d_Trend"] = (
        df["Volume"]
        .rolling(window=5, min_periods=5)
        .apply(lambda x: 1.0 if float(x.iloc[-1]) > float(x.iloc[0]) else 0.0, raw=False)
    )

    # ── Dist_SMA50_Pct: % distance of price from the 50 SMA ──────────────────
    # Useful for finding stocks near their SMA50 (potential breakout/breakdown)
    # vs stocks already extended far above/below (higher risk).
    df["Dist_SMA50_Pct"] = ((df["Close"] - df["SMA50"]) / df["SMA50"]) * 100

    return df


# ─────────────────────────────────────────────────────────────────────────────
# BIG MONEY SIGNAL DETECTION
# ─────────────────────────────────────────────────────────────────────────────


def detect_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect Bullish Accumulation and Bearish Distribution signals.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  SIGNAL 1 — BULLISH ACCUMULATION (🟢)                                  │
    │                                                                         │
    │  Condition:                                                             │
    │    Close > SMA50           (Price is in an uptrend)                    │
    │    AND Vol_Ratio > 1.5     (Volume is spiking — institutions buying)   │
    │    AND Vol_5d_Trend = 1    (Volume has been rising for 5 days)         │
    │                                                                         │
    │  Why this = Felix's "accumulation":                                     │
    │    Institutions cannot buy millions of shares in one day without        │
    │    crashing the price. They spread their buying over many sessions.     │
    │    A 5-day rising volume trend + above-average volume = they are        │
    │    LOADING UP. The fact that price is above SMA50 confirms the trend   │
    │    is supporting their conviction. This is the "green" to follow.      │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  SIGNAL 2 — BEARISH DISTRIBUTION (🔴)                                  │
    │                                                                         │
    │  Condition:                                                             │
    │    Close < SMA50           (Price is in a downtrend)                   │
    │    AND Vol_Ratio > 1.5     (Volume is spiking — institutions selling)  │
    │                                                                         │
    │  Why this = Felix's "distribution":                                     │
    │    When smart money decides to EXIT a position, they sell into          │
    │    any remaining buying interest. The result: high volume on DOWN       │
    │    days below the trend line. Felix calls this "distribution" —        │
    │    institutions are handing shares to retail investors at peak          │
    │    prices before the real move down. STAY OUT of these stocks.         │
    └─────────────────────────────────────────────────────────────────────────┘
    """
    df = df.copy()

    # Initialise signal columns
    df["Signal"] = "Neutral"
    df["Bullish"] = False
    df["Bearish"] = False

    # ── BULLISH ACCUMULATION: Three-part confirmation ─────────────────────────
    # Felix's rule: all three conditions must be TRUE simultaneously.
    # This triple-filter greatly reduces false signals.
    bullish_mask = (
        (df["Close"] > df["SMA50"])     # Uptrend confirmed
        & (df["Vol_Ratio"] > 1.5)        # Volume spike: 50%+ above 20-day average
        & (df["Vol_5d_Trend"] == 1.0)    # 5-day rising volume trend: sustained buying
    )
    df.loc[bullish_mask, "Signal"] = "Bullish Accumulation"
    df.loc[bullish_mask, "Bullish"] = True

    # ── BEARISH DISTRIBUTION: Two-part warning ────────────────────────────────
    # Simpler threshold — price weakness + volume spike is enough for caution.
    # We don't require a 5-day trend because a single large sell-off is warning enough.
    bearish_mask = (
        (df["Close"] < df["SMA50"])     # Downtrend: price below trend line
        & (df["Vol_Ratio"] > 1.5)        # Volume spike: unusual selling pressure
    )
    df.loc[bearish_mask, "Signal"] = "Bearish Distribution"
    df.loc[bearish_mask, "Bearish"] = True

    # Note: A stock can't simultaneously be above and below SMA50,
    # so bullish and bearish masks are always mutually exclusive.

    return df


# ─────────────────────────────────────────────────────────────────────────────
# MONEY FLOW SCORE (0–100)
# ─────────────────────────────────────────────────────────────────────────────


def calculate_money_flow_score(row: pd.Series) -> int:
    """
    Composite score from 0 (very bearish) to 100 (very bullish).

    Three components (mirroring Felix's mental checklist):

    1. Trend Score (0–50 pts):
       Where is the price relative to SMA50?
       → Far above SMA50 → up to 50 pts
       → At SMA50 → 25 pts (neutral)
       → Far below SMA50 → 0 pts

    2. Volume Score (0–35 pts):
       How large is the volume spike?
       → 3× average = max 35 pts
       → 1.5× average = ~17 pts
       → Average or below = 0 pts

    3. Momentum Score (0–15 pts):
       Is volume trending upward over 5 days?
       → Yes = 15 pts (sustained accumulation confirmed)
       → No  = 0 pts

    Felix's guideline: "Look for scores of 70+ with a clean chart setup.
    That's where the best risk/reward setups live."

    Score guide:
        70–100 = Strong bullish money flow (potential buy setup)
        50–69  = Moderate / building
        30–49  = Weak / neutral
        0–29   = Bearish distribution / avoid
    """
    score = 0

    # ── Component 1: Trend (SMA50 position) — 0 to 50 points ─────────────────
    dist_pct = row.get("Dist_SMA50_Pct", 0.0)
    if pd.notna(dist_pct):
        # Map dist_pct from [-10%, +10%] → [0, 50] linearly, clamp at edges
        trend_score = 25 + (dist_pct * 2.5)          # 0% → 25, +10% → 50, -10% → 0
        trend_score = max(0.0, min(50.0, trend_score))
        score += trend_score

    # ── Component 2: Volume surge — 0 to 35 points ───────────────────────────
    vol_ratio = row.get("Vol_Ratio", 1.0)
    if pd.notna(vol_ratio) and vol_ratio > 1.0:
        # Maps 1.0× → 0 pts, 3.0× → 35 pts (linear, capped at 35)
        vol_score = ((vol_ratio - 1.0) / 2.0) * 35
        vol_score = max(0.0, min(35.0, vol_score))
        score += vol_score

    # ── Component 3: Volume momentum — 0 or 15 points ────────────────────────
    vol_trend = row.get("Vol_5d_Trend", 0.0)
    if pd.notna(vol_trend) and vol_trend == 1.0:
        score += 15  # 5-day rising volume trend = sustained smart money activity

    return int(max(0, min(100, round(score))))


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────────────────────────────────────────────────


def build_chart(df: pd.DataFrame, ticker: str, company_name: str = "") -> go.Figure:
    """
    Build an interactive Plotly chart matching Felix's webinar style:

    Panel 1 (70% height) — Candlestick chart:
        • Green candles  = up days (close > open)
        • Red candles    = down days (close < open)
        • Thick blue line = SMA50 (the trend filter)
        • Green arrows ↑  = Bullish Accumulation signals
        • Red arrows ↓    = Bearish Distribution signals

    Panel 2 (30% height) — Volume bars:
        • GREEN bar = volume > 1.5× 20-day average (big money active)
        • RED bar   = normal volume (no institutional signal)
        • Orange dotted line = 20-day average volume baseline
    """
    title = f"{company_name} ({ticker})" if company_name else ticker

    # Two-panel layout: price chart + volume bar chart
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,      # Lock x-axis zoom/pan between panels
        vertical_spacing=0.04,
        row_heights=[0.70, 0.30],
        subplot_titles=["", "Volume"],
    )

    # ── Panel 1a: Candlestick Chart ───────────────────────────────────────────
    # Green body = buying pressure (close > open)
    # Red body   = selling pressure (close < open)
    # Felix uses candlesticks to see the daily battle between bulls and bears.
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00c853",    # Green wick on up days
            decreasing_line_color="#ff1744",    # Red wick on down days
            increasing_fillcolor="#00c853",     # Solid green body
            decreasing_fillcolor="#ff1744",     # Solid red body
            whiskerwidth=0.4,
        ),
        row=1,
        col=1,
    )

    # ── Panel 1b: SMA50 Line ──────────────────────────────────────────────────
    # Thick, bright blue line — the primary trend filter.
    # Felix's simple rule: trade in the direction of this line.
    # Price crossing ABOVE → potential entry signal
    # Price crossing BELOW → exit or stand aside
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA50"],
            name="SMA 50",
            line=dict(color="#2196f3", width=2.5),   # Thick blue (matches Felix's chart)
            opacity=0.95,
            hovertemplate="SMA50: %{y:.2f}p<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # ── Panel 1c: Bullish Accumulation Arrows (↑) ────────────────────────────
    # Green up-arrows placed just BELOW each bullish signal candle.
    # This is where Felix says: "This is the footprint of smart money buying."
    bullish_days = df[df["Bullish"] == True]
    if not bullish_days.empty:
        fig.add_trace(
            go.Scatter(
                x=bullish_days.index,
                y=bullish_days["Low"] * 0.975,   # Position slightly below the low
                mode="markers",
                name="Bullish Accumulation",
                marker=dict(
                    symbol="arrow-up",
                    size=13,
                    color="#00e676",                # Bright lime green
                    line=dict(color="#ffffff", width=1.5),
                ),
                hovertemplate=(
                    "<b>🟢 Bullish Accumulation</b><br>"
                    "Date: %{x|%d %b %Y}<br>"
                    "Close: %{customdata[0]:.2f}p<br>"
                    "Vol Ratio: %{customdata[1]:.2f}×<br>"
                    "vs SMA50: %{customdata[2]:+.1f}%<br>"
                    "<extra></extra>"
                ),
                customdata=list(
                    zip(
                        bullish_days["Close"],
                        bullish_days["Vol_Ratio"].fillna(0),
                        bullish_days["Dist_SMA50_Pct"].fillna(0),
                    )
                ),
            ),
            row=1,
            col=1,
        )

    # ── Panel 1d: Bearish Distribution Arrows (↓) ────────────────────────────
    # Red down-arrows placed just ABOVE each bearish signal candle.
    # Felix's warning: "Smart money is unloading here — don't be the buyer."
    bearish_days = df[df["Bearish"] == True]
    if not bearish_days.empty:
        fig.add_trace(
            go.Scatter(
                x=bearish_days.index,
                y=bearish_days["High"] * 1.025,  # Position slightly above the high
                mode="markers",
                name="Bearish Distribution",
                marker=dict(
                    symbol="arrow-down",
                    size=13,
                    color="#ff5252",                # Bright red
                    line=dict(color="#ffffff", width=1.5),
                ),
                hovertemplate=(
                    "<b>🔴 Bearish Distribution</b><br>"
                    "Date: %{x|%d %b %Y}<br>"
                    "Close: %{customdata[0]:.2f}p<br>"
                    "Vol Ratio: %{customdata[1]:.2f}×<br>"
                    "vs SMA50: %{customdata[2]:+.1f}%<br>"
                    "<extra></extra>"
                ),
                customdata=list(
                    zip(
                        bearish_days["Close"],
                        bearish_days["Vol_Ratio"].fillna(0),
                        bearish_days["Dist_SMA50_Pct"].fillna(0),
                    )
                ),
            ),
            row=1,
            col=1,
        )

    # ── Panel 2a: Volume Bars ─────────────────────────────────────────────────
    # GREEN bar = volume spike (> 1.5× average) → big money is active
    # RED bar   = normal or low volume → no special signal
    # This colour coding makes it instantly obvious when unusual activity occurs.
    volume_colors = [
        "#00c853" if (pd.notna(r) and r > 1.5) else "#ef5350"
        for r in df["Vol_Ratio"].fillna(0)
    ]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=volume_colors,
            opacity=0.75,
            hovertemplate=(
                "Date: %{x|%d %b %Y}<br>"
                "Volume: %{y:,.0f}<br>"
                "<extra></extra>"
            ),
        ),
        row=2,
        col=1,
    )

    # ── Panel 2b: 20-day Average Volume Line ──────────────────────────────────
    # Orange dotted line shows the "normal" baseline.
    # Bars shooting above this line = unusual interest.
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Vol_MA20"],
            name="Vol MA20",
            line=dict(color="#ffa726", width=1.5, dash="dot"),
            opacity=0.8,
            hovertemplate="20d Avg Vol: %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # ── Signal Shading: Highlight signal days with subtle background ──────────
    # Only shade the last 90 days to keep the chart readable
    signal_window = df.tail(90)
    for idx, row_data in signal_window.iterrows():
        if row_data.get("Bullish"):
            fig.add_vrect(
                x0=idx,
                x1=idx,
                fillcolor="rgba(0, 200, 83, 0.12)",
                layer="below",
                line_width=0,
            )
        elif row_data.get("Bearish"):
            fig.add_vrect(
                x0=idx,
                x1=idx,
                fillcolor="rgba(255, 23, 68, 0.10)",
                layer="below",
                line_width=0,
            )

    # ── Chart Layout: Dark Theme ──────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>   |   FTSE Follow the Green Scanner",
            font=dict(size=15, color="#e2e8f0"),
            x=0.01,
        ),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b27",
        font=dict(color="#a0aec0", size=11),
        xaxis_rangeslider_visible=False,   # Hide the default rangeslider (cleaner)
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(22, 27, 39, 0.85)",
            bordercolor="#2d3748",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=10, r=15, t=65, b=10),
        hovermode="x unified",
        height=640,
    )

    # Grid and spike lines for readability
    fig.update_xaxes(
        gridcolor="#1f2937",
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikecolor="#4a5568",
        spikemode="across",
        spikethickness=1,
        spikesnap="cursor",
    )
    fig.update_yaxes(gridcolor="#1f2937", showgrid=True, zeroline=False)

    # Format volume y-axis with compact notation (e.g. 10M, 50k)
    fig.update_yaxes(tickformat=".3s", row=2, col=1)

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SCANNER — Process multiple tickers in sequence
# ─────────────────────────────────────────────────────────────────────────────


def scan_tickers(ticker_dict: dict) -> pd.DataFrame:
    """
    Scan all provided tickers, calculate indicators & signals, and return
    a summary DataFrame with one row per ticker.

    Columns returned:
        Company, Ticker, Price (p), Signal, % from SMA50,
        20d Avg Vol, Vol Ratio, Money Flow Score
    """
    results = []
    tickers = list(ticker_dict.items())
    total = len(tickers)

    progress_bar = st.progress(0, text="Initialising scanner...")
    status_text = st.empty()

    for i, (company, ticker) in enumerate(tickers):
        pct = (i + 1) / total
        progress_bar.progress(pct, text=f"Scanning {ticker}  ({i+1}/{total})")
        status_text.markdown(
            f"<small style='color:#718096;'>Loading: {ticker} — {company}</small>",
            unsafe_allow_html=True,
        )

        df = fetch_ohlcv(ticker)

        base_row = {
            "Company": company,
            "Ticker": ticker,
            "Price (p)": None,
            "Signal": "No Data",
            "% from SMA50": None,
            "20d Avg Vol": None,
            "Vol Ratio": None,
            "Money Flow Score": None,
        }

        # Need at least 55 rows to compute SMA50 (50 days) with some buffer
        if df is None or len(df) < 55:
            results.append(base_row)
            continue

        try:
            df = calculate_indicators(df)
            df = detect_signals(df)
            latest = df.iloc[-1]
            mfs = calculate_money_flow_score(latest)

            results.append({
                "Company": company,
                "Ticker": ticker,
                "Price (p)": round(float(latest["Close"]), 2),
                "Signal": str(latest["Signal"]),
                "% from SMA50": (
                    round(float(latest["Dist_SMA50_Pct"]), 2)
                    if pd.notna(latest["Dist_SMA50_Pct"])
                    else None
                ),
                "20d Avg Vol": (
                    int(latest["Vol_MA20"])
                    if pd.notna(latest["Vol_MA20"])
                    else None
                ),
                "Vol Ratio": (
                    round(float(latest["Vol_Ratio"]), 2)
                    if pd.notna(latest["Vol_Ratio"])
                    else None
                ),
                "Money Flow Score": mfs,
            })

        except Exception:
            base_row["Signal"] = "Error"
            results.append(base_row)

    progress_bar.empty()
    status_text.empty()

    return pd.DataFrame(results)


# ─────────────────────────────────────────────────────────────────────────────
# RISK MANAGEMENT HELPER
# ─────────────────────────────────────────────────────────────────────────────


def calculate_position_size(
    price_pence: float,
    risk_gbp: float = 750.0,
    stop_loss_pct: float = 0.10,
) -> dict:
    """
    Felix's 1% Rule Position Sizing.

    The core principle:
        "Never risk more than 1% of your account on any single trade."

    Here we use a fixed £750 risk amount (user's "1% of portfolio").
    The stop loss is set at X% below the entry price.

    Formula:
        Risk per share (£) = Entry price (£) × Stop loss %
        Max shares         = Total risk (£) / Risk per share (£)
        Position value (£) = Max shares × Entry price (£)

    Example at 10% stop:
        Stock at 500p = £5.00
        Risk per share = £5.00 × 10% = £0.50
        Max shares = £750 / £0.50 = 1,500 shares
        Position value = 1,500 × £5.00 = £7,500

    If the stock drops 10% → you lose exactly £750 (your 1% rule limit).
    This keeps any single loss from materially damaging your portfolio.
    """
    price_gbp = price_pence / 100.0           # Convert pence → pounds
    risk_per_share = price_gbp * stop_loss_pct
    num_shares = risk_gbp / risk_per_share
    position_value = num_shares * price_gbp
    stop_price_pence = price_pence * (1.0 - stop_loss_pct)
    potential_reward = position_value * (stop_loss_pct * 2)  # Assumes 2:1 reward/risk

    return {
        "Entry Price": f"{price_pence:.2f}p  (£{price_gbp:.2f})",
        "Stop Loss Price": f"{stop_price_pence:.2f}p  (£{stop_price_pence/100:.2f})",
        "Stop Loss %": f"{stop_loss_pct * 100:.0f}% below entry",
        "Max Shares to Buy": f"{int(num_shares):,} shares",
        "Max Position Value": f"£{position_value:,.0f}",
        "Max Risk (£)": f"£{risk_gbp:,.0f}",
        "Target Reward (2:1)": f"£{potential_reward:,.0f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────


def main():

    # ── App Header ─────────────────────────────────────────────────────────────
    st.markdown(
        """
    <div style="background: linear-gradient(135deg, #1a2744 0%, #121827 100%);
                padding: 22px 26px; border-radius: 12px; margin-bottom: 22px;
                border: 1px solid #2d3748;">
        <h1 style="margin:0 0 6px 0; color:#90cdf4; font-size:1.75rem; font-weight:800;">
            📈 FTSE Follow the Green Scanner
        </h1>
        <p style="margin:0; color:#718096; font-size:0.92rem; line-height:1.5;">
            Detect institutional money flow in FTSE 100 stocks using Felix's
            <em>"Follow the Money"</em> methodology.<br>
            <span style="color:#4a5568; font-size:0.82rem;">
            ⚠️ Educational tool only — not financial advice. Always do your own research.
            </span>
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Scanner Settings")
        st.markdown("---")

        # ── Mode Selection ──────────────────────────────────────────────────
        scan_mode = st.radio(
            "Scan Mode",
            ["🔎 Single Stock", "📋 Custom List", "🇬🇧 Full FTSE 100"],
            index=0,
            help=(
                "Single Stock: chart one ticker in detail\n"
                "Custom List: paste or upload your own tickers\n"
                "Full FTSE 100: scan all ~80 FTSE 100 stocks (takes ~2 min)"
            ),
        )

        selected_tickers = {}

        # ── Single Stock Mode ──────────────────────────────────────────────
        if scan_mode == "🔎 Single Stock":
            company_list = sorted(FTSE_100.keys())
            selected_company = st.selectbox(
                "Select FTSE 100 Stock", company_list, index=company_list.index("AstraZeneca")
            )

            st.markdown("<small style='color:#4a5568;'>Or override with any ticker:</small>", unsafe_allow_html=True)
            manual_ticker = st.text_input(
                "Custom ticker (e.g. VOD.L)",
                placeholder="TICKER.L",
                label_visibility="collapsed",
            ).strip().upper()

            if manual_ticker:
                # Add .L suffix if user forgot it
                if not manual_ticker.endswith(".L"):
                    manual_ticker += ".L"
                selected_tickers = {manual_ticker: manual_ticker}
            else:
                selected_tickers = {selected_company: FTSE_100[selected_company]}

        # ── Custom List Mode ────────────────────────────────────────────────
        elif scan_mode == "📋 Custom List":
            uploaded = st.file_uploader(
                "Upload .txt / .csv (one ticker per line)",
                type=["txt", "csv"],
            )
            pasted = st.text_area(
                "Or paste tickers (one per line)",
                height=140,
                placeholder="BARC.L\nLLOY.L\nAZN.L\nSHEL.L",
            )

            raw = []
            if uploaded:
                content = uploaded.read().decode("utf-8")
                raw = [t.strip().upper() for t in content.splitlines() if t.strip()]
            elif pasted:
                raw = [t.strip().upper() for t in pasted.splitlines() if t.strip()]

            # Auto-append .L if missing
            raw = [t if t.endswith(".L") else f"{t}.L" for t in raw]
            selected_tickers = {t: t for t in raw}

            if selected_tickers:
                st.success(f"✅ {len(selected_tickers)} tickers loaded")

        # ── Full FTSE 100 Mode ──────────────────────────────────────────────
        else:
            selected_tickers = FTSE_100.copy()
            st.success(f"✅ {len(selected_tickers)} FTSE 100 stocks loaded")
            st.info("⏱️ Full scan takes approximately 2–3 minutes.")

        st.markdown("---")

        # ── Filters ─────────────────────────────────────────────────────────
        st.markdown("### 🔍 Filter & Sort")

        filter_mode = st.selectbox(
            "Filter Signals",
            ["Show All", "🟢 Bullish Only", "🔴 Bearish Only", "⚪ Neutral Only"],
        )

        sort_by = st.selectbox(
            "Sort Results By",
            [
                "Money Flow Score ↓",
                "Volume Ratio ↓",
                "% above SMA50 ↓",
                "Company A→Z",
            ],
        )

        st.markdown("---")

        # ── Risk Settings ────────────────────────────────────────────────────
        st.markdown("### 💰 Risk Management")
        risk_amount = st.number_input(
            "Max risk per trade (£)",
            min_value=50,
            max_value=10000,
            value=750,
            step=50,
            help="Felix's 1% Rule: this should be ~1% of your total portfolio.",
        )
        stop_loss_pct = (
            st.slider(
                "Stop loss %",
                min_value=2,
                max_value=25,
                value=10,
                help="% below entry price where you'd exit the trade.",
            )
            / 100.0
        )

        st.markdown("---")
        st.markdown(
            """
        <div style="color:#4a5568; font-size:0.78rem; line-height:1.6;">
        <b style="color:#718096;">Felix's Core Rules:</b><br>
        1. Price must be above SMA50<br>
        2. Volume must spike (>1.5× avg)<br>
        3. Volume trend must be rising<br>
        4. Risk no more than 1% per trade<br>
        5. Target 2:1 reward-to-risk minimum<br><br>
        <em>"Follow the green — follow the money."</em>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ── No tickers selected guard ─────────────────────────────────────────────
    if not selected_tickers:
        st.info("👈 Select stocks in the sidebar to begin scanning.")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # SINGLE STOCK DETAILED VIEW
    # ══════════════════════════════════════════════════════════════════════════
    is_single = (scan_mode == "🔎 Single Stock") or (
        scan_mode == "📋 Custom List" and len(selected_tickers) == 1
    )

    if is_single:
        company_name, ticker = list(selected_tickers.items())[0]

        with st.spinner(f"Loading data for **{ticker}**..."):
            df = fetch_ohlcv(ticker)

        # ── Error handling ────────────────────────────────────────────────────
        if df is None or df.empty:
            st.error(
                f"❌ Could not load data for **{ticker}**.\n\n"
                "Please check:\n"
                "- The ticker symbol is correct (must end in `.L` for LSE)\n"
                "- Your internet connection\n"
                "- Yahoo Finance may have changed this ticker"
            )
            return

        if len(df) < 55:
            st.warning(
                f"⚠️ Insufficient data for **{ticker}** "
                f"(found {len(df)} trading days, need at least 55 for SMA50)."
            )
            return

        df = calculate_indicators(df)
        df = detect_signals(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        mfs = calculate_money_flow_score(latest)

        signal = str(latest["Signal"])

        # ── Signal Banner ─────────────────────────────────────────────────────
        if signal == "Bullish Accumulation":
            st.markdown(
                f"""
            <div class="banner-bullish">
                <div style="font-size:1.25rem; font-weight:800; color:#68d391;">
                    🟢 BULLISH ACCUMULATION DETECTED — {ticker}
                </div>
                <div style="margin-top:6px; color:#9ae6b4; font-size:0.92rem; line-height:1.6;">
                    Price is <strong>above the 50 SMA</strong>, volume is
                    <strong>{float(latest['Vol_Ratio']):.1f}× the 20-day average</strong>,
                    and volume has been <strong>rising for 5 days</strong>.<br>
                    Felix's signal: <em>"Institutions are loading up. Follow the green."</em>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        elif signal == "Bearish Distribution":
            st.markdown(
                f"""
            <div class="banner-bearish">
                <div style="font-size:1.25rem; font-weight:800; color:#fc8181;">
                    🔴 BEARISH DISTRIBUTION SIGNAL — {ticker}
                </div>
                <div style="margin-top:6px; color:#feb2b2; font-size:0.92rem; line-height:1.6;">
                    Price is <strong>below the 50 SMA</strong> with a volume spike of
                    <strong>{float(latest['Vol_Ratio']):.1f}× normal</strong>.<br>
                    Felix's warning: <em>"Smart money is exiting. Avoid new longs."</em>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div class="banner-neutral">
                <div style="font-size:1.15rem; font-weight:700; color:#a0aec0;">
                    ⚪ NEUTRAL — No Big Money Signal Today — {ticker}
                </div>
                <div style="margin-top:6px; color:#718096; font-size:0.9rem;">
                    No unusual volume spike or trend confirmation detected.
                    Continue monitoring. <em>"When in doubt, stay out."</em>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Key Metric Cards ──────────────────────────────────────────────────
        col1, col2, col3, col4, col5 = st.columns(5)

        day_change_pct = ((float(latest["Close"]) / float(prev["Close"])) - 1.0) * 100
        with col1:
            st.metric(
                "Current Price",
                f"{float(latest['Close']):.2f}p",
                delta=f"{day_change_pct:+.2f}% today",
                delta_color="normal" if day_change_pct >= 0 else "inverse",
            )

        dist = float(latest["Dist_SMA50_Pct"]) if pd.notna(latest["Dist_SMA50_Pct"]) else 0.0
        with col2:
            st.metric(
                "vs 50 SMA",
                f"{dist:+.1f}%",
                delta="Above trend" if dist > 0 else "Below trend",
                delta_color="normal" if dist > 0 else "inverse",
            )

        vol_ratio = float(latest["Vol_Ratio"]) if pd.notna(latest["Vol_Ratio"]) else 0.0
        with col3:
            st.metric(
                "Volume Ratio",
                f"{vol_ratio:.2f}×",
                delta="🟢 SPIKE" if vol_ratio > 1.5 else "Normal",
                delta_color="normal" if vol_ratio > 1.5 else "off",
            )

        avg_vol = int(latest["Vol_MA20"]) if pd.notna(latest["Vol_MA20"]) else 0
        with col4:
            st.metric("20d Avg Volume", f"{avg_vol:,}")

        score_label = "Strong 🔥" if mfs >= 70 else ("Moderate" if mfs >= 40 else "Weak ❄️")
        with col5:
            st.metric(
                "Money Flow Score",
                f"{mfs} / 100",
                delta=score_label,
                delta_color="normal" if mfs >= 70 else ("off" if mfs >= 40 else "inverse"),
            )

        # ── Chart ─────────────────────────────────────────────────────────────
        fig = build_chart(df, ticker, company_name)
        st.plotly_chart(fig, use_container_width=True)

        # ── Signal Summary Table ──────────────────────────────────────────────
        st.markdown(
            '<div class="section-header">📊 Current Signal Summary</div>',
            unsafe_allow_html=True,
        )

        summary_data = {
            "Metric": [
                "Current Signal",
                "Last Close",
                "50-Day SMA",
                "% Distance from SMA50",
                "Today's Volume",
                "20-Day Avg Volume",
                "Volume Ratio (× avg)",
                "Volume 5d Trend",
                "Money Flow Score",
            ],
            "Value": [
                signal,
                f"{float(latest['Close']):.2f}p",
                f"{float(latest['SMA50']):.2f}p" if pd.notna(latest["SMA50"]) else "N/A",
                f"{dist:+.2f}%",
                f"{int(latest['Volume']):,}",
                f"{avg_vol:,}",
                f"{vol_ratio:.2f}×",
                "Rising ↑" if latest.get("Vol_5d_Trend") == 1.0 else "Flat/Falling ↓",
                f"{mfs}/100 — {score_label}",
            ],
        }

        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            st.dataframe(
                pd.DataFrame(summary_data),
                use_container_width=True,
                hide_index=True,
            )

        # ── Risk Management Panel ─────────────────────────────────────────────
        with col_t2:
            risk_data = calculate_position_size(
                float(latest["Close"]), risk_amount, stop_loss_pct
            )
            rows_html = "".join(
                f'<div style="display:flex; justify-content:space-between; padding:4px 0; '
                f'border-bottom:1px solid #2d3748;">'
                f'<span style="color:#718096; font-size:0.88rem;">{k}</span>'
                f'<span style="color:#e2e8f0; font-weight:600; font-size:0.88rem;">{v}</span>'
                f"</div>"
                for k, v in risk_data.items()
            )
            st.markdown(
                f"""
            <div class="risk-box">
                <div style="color:#90cdf4; font-weight:700; font-size:1rem; margin-bottom:10px;">
                    💰 Position Sizing — Felix's 1% Rule
                </div>
                {rows_html}
                <div style="color:#4a5568; font-size:0.78rem; margin-top:10px; line-height:1.5;">
                    If price drops {stop_loss_pct*100:.0f}% to the stop, max loss = £{risk_amount:,}.
                    Target at least 2× that in profit before entering.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Recent Signal History ─────────────────────────────────────────────
        st.markdown(
            '<div class="section-header">📋 Recent Signal History (Last 60 Days)</div>',
            unsafe_allow_html=True,
        )

        history = (
            df[df["Signal"] != "Neutral"]
            .tail(60)[["Close", "Volume", "Vol_Ratio", "Dist_SMA50_Pct", "Signal"]]
            .copy()
        )

        if history.empty:
            st.info("No bullish or bearish signals in the last 60 days for this ticker.")
        else:
            history.index = pd.to_datetime(history.index).strftime("%d %b %Y")
            history.columns = ["Close (p)", "Volume", "Vol Ratio (×)", "% from SMA50", "Signal"]
            history["Close (p)"] = history["Close (p)"].round(2)
            history["Vol Ratio (×)"] = history["Vol Ratio (×)"].round(2)
            history["% from SMA50"] = history["% from SMA50"].round(2)
            history = history.iloc[::-1]   # Most recent first

            st.dataframe(
                history,
                use_container_width=True,
                column_config={
                    "Signal": st.column_config.TextColumn("Signal", width="large"),
                    "Vol Ratio (×)": st.column_config.NumberColumn(format="%.2f×"),
                    "% from SMA50": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Volume": st.column_config.NumberColumn(format="%,d"),
                },
            )

        # ── Export ────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="section-header">📥 Export Data</div>',
            unsafe_allow_html=True,
        )
        export_df = df[["Open", "High", "Low", "Close", "Volume", "SMA50", "Vol_MA20", "Vol_Ratio", "Dist_SMA50_Pct", "Signal"]].copy()
        export_df.index.name = "Date"
        csv_buf = io.StringIO()
        export_df.to_csv(csv_buf)
        st.download_button(
            "⬇️ Export Full History to CSV",
            data=csv_buf.getvalue(),
            file_name=f"{ticker}_signals_{datetime.date.today().isoformat()}.csv",
            mime="text/csv",
        )

    # ══════════════════════════════════════════════════════════════════════════
    # MULTI-TICKER SCAN VIEW
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown(
            f'<div class="section-header">🔍 Scanning {len(selected_tickers)} Stocks...</div>',
            unsafe_allow_html=True,
        )

        results_df = scan_tickers(selected_tickers)

        if results_df.empty:
            st.error("Scanner returned no results. Please check your ticker list.")
            return

        # ── Summary Statistics ─────────────────────────────────────────────────
        valid_df = results_df[~results_df["Signal"].isin(["No Data", "Error"])]
        bullish_n = int((valid_df["Signal"] == "Bullish Accumulation").sum())
        bearish_n = int((valid_df["Signal"] == "Bearish Distribution").sum())
        neutral_n = int((valid_df["Signal"] == "Neutral").sum())
        total_n = len(valid_df)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Stocks Scanned", total_n)
        c2.metric("🟢 Bullish Accumulation", bullish_n)
        c3.metric("🔴 Bearish Distribution", bearish_n)
        c4.metric("⚪ Neutral", neutral_n)

        st.markdown("---")

        # ── Apply Filters ──────────────────────────────────────────────────────
        filtered = results_df.copy()

        if filter_mode == "🟢 Bullish Only":
            filtered = filtered[filtered["Signal"] == "Bullish Accumulation"]
        elif filter_mode == "🔴 Bearish Only":
            filtered = filtered[filtered["Signal"] == "Bearish Distribution"]
        elif filter_mode == "⚪ Neutral Only":
            filtered = filtered[filtered["Signal"] == "Neutral"]

        # ── Apply Sort ─────────────────────────────────────────────────────────
        if sort_by == "Money Flow Score ↓":
            filtered = filtered.sort_values("Money Flow Score", ascending=False, na_position="last")
        elif sort_by == "Volume Ratio ↓":
            filtered = filtered.sort_values("Vol Ratio", ascending=False, na_position="last")
        elif sort_by == "% above SMA50 ↓":
            filtered = filtered.sort_values("% from SMA50", ascending=False, na_position="last")
        elif sort_by == "Company A→Z":
            filtered = filtered.sort_values("Company")

        st.markdown(
            f"**Showing {len(filtered)} of {len(results_df)} tickers** "
            f"(filter: {filter_mode} | sort: {sort_by})"
        )

        # ── Results Table ──────────────────────────────────────────────────────
        if filtered.empty:
            st.info("No tickers match the current filter. Try **Show All**.")
        else:
            st.dataframe(
                filtered,
                use_container_width=True,
                height=min(550, 65 + len(filtered) * 38),
                hide_index=True,
                column_config={
                    "Signal": st.column_config.TextColumn("Signal", width="large"),
                    "% from SMA50": st.column_config.NumberColumn(
                        "% from SMA50", format="%+.2f%%"
                    ),
                    "Vol Ratio": st.column_config.NumberColumn(
                        "Vol Ratio", format="%.2f×"
                    ),
                    "Money Flow Score": st.column_config.ProgressColumn(
                        "Money Flow Score",
                        min_value=0,
                        max_value=100,
                        format="%d",
                        width="medium",
                    ),
                    "Price (p)": st.column_config.NumberColumn(
                        "Price (p)", format="%.2f"
                    ),
                    "20d Avg Vol": st.column_config.NumberColumn(
                        "20d Avg Vol", format="%,d"
                    ),
                },
            )

            # ── Export Signals to CSV ──────────────────────────────────────────
            st.markdown(
                '<div class="section-header">📥 Export Signals</div>',
                unsafe_allow_html=True,
            )
            col_dl, _ = st.columns([1, 3])
            with col_dl:
                csv_buf = io.StringIO()
                filtered.to_csv(csv_buf, index=False)
                st.download_button(
                    label="⬇️ Export to CSV",
                    data=csv_buf.getvalue(),
                    file_name=f"ftse_signals_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            # ── Drill-Down Chart ───────────────────────────────────────────────
            st.markdown(
                '<div class="section-header">📊 View Detailed Chart</div>',
                unsafe_allow_html=True,
            )

            chartable = filtered[~filtered["Signal"].isin(["No Data", "Error"])]
            if chartable.empty:
                st.info("No valid tickers available to chart.")
            else:
                ticker_labels = [
                    f"{row['Company']}  ({row['Ticker']})  — {row['Signal']}  |  Score: {row['Money Flow Score']}"
                    for _, row in chartable.iterrows()
                ]
                selected_label = st.selectbox(
                    "Select a stock to view its chart:", ticker_labels
                )

                if selected_label:
                    # Parse ticker from label
                    chart_ticker = selected_label.split("(")[1].split(")")[0].strip()
                    chart_company = selected_label.split("(")[0].strip()

                    with st.spinner(f"Loading chart for **{chart_ticker}**..."):
                        chart_df = fetch_ohlcv(chart_ticker)

                    if chart_df is not None and len(chart_df) >= 55:
                        chart_df = calculate_indicators(chart_df)
                        chart_df = detect_signals(chart_df)
                        st.plotly_chart(
                            build_chart(chart_df, chart_ticker, chart_company),
                            use_container_width=True,
                        )

                        # Risk panel for the charted stock
                        chart_price = float(chart_df.iloc[-1]["Close"])
                        risk_data = calculate_position_size(chart_price, risk_amount, stop_loss_pct)
                        rows_html = "".join(
                            f'<div style="display:flex; justify-content:space-between; '
                            f'padding:4px 0; border-bottom:1px solid #2d3748;">'
                            f'<span style="color:#718096; font-size:0.88rem;">{k}</span>'
                            f'<span style="color:#e2e8f0; font-weight:600; font-size:0.88rem;">{v}</span>'
                            f"</div>"
                            for k, v in risk_data.items()
                        )
                        col_r, _ = st.columns([1, 1])
                        with col_r:
                            st.markdown(
                                f"""
                            <div class="risk-box">
                                <div style="color:#90cdf4; font-weight:700; margin-bottom:10px;">
                                    💰 Position Sizing — {chart_company}
                                </div>
                                {rows_html}
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.warning(
                            f"Not enough data to chart **{chart_ticker}** "
                            f"(need at least 55 trading days)."
                        )


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
