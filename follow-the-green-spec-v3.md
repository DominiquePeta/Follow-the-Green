# Follow-the-Green: Felix Methodology Spec v3

## Context

The app currently implements Felix's methodology using **SMA50 only** — which is his **trader** rule. The webinar makes a critical distinction the app is missing:

- **Investors** → use the **150-day moving average** as the primary trend filter
- **Traders** (high-risk / growth / tech stocks) → use the **50-day moving average**

Two additional gaps:
- Volume threshold of `1.5×` is too lenient for true institutional flow (Felix describes institutional distribution as `5–10×` normal volume)
- No hard "Buy Eligible" rule — Felix's covenant #1 is "never buy below the moving average"

This spec adds three changes. **Do not refactor anything else.**

---

## Change 1 — Investor/Trader Mode + SMA150

### 1.1 Add a global mode toggle

In the sidebar, **above** the `Scan Mode` radio (line ~1164), add:

```python
profile_mode = st.radio(
    "Profile",
    ["📊 Investor (SMA150)", "⚡ Trader (SMA50)"],
    index=0,
    help="Investors use the 150-day MA for safer, longer-term signals. "
         "Traders use the 50-day MA for faster signals on higher-volatility stocks."
)
is_investor = profile_mode.startswith("📊")
active_ma_period = 150 if is_investor else 50
active_ma_label = "SMA150" if is_investor else "SMA50"
```

`is_investor` and `active_ma_period` must be passed down to `calculate_indicators`, `detect_signals`, `calculate_money_flow_score`, `detect_exit_warnings`, `scan_tickers`, and `build_chart`.

### 1.2 Update `calculate_indicators(df, ma_period=50)`

Add `ma_period` parameter (default 50 to preserve current trader behaviour).

Compute **both** SMAs every time (cheap, and chart needs both for context):

```python
df["SMA50"]  = df["Close"].rolling(window=50,  min_periods=50).mean()
df["SMA150"] = df["Close"].rolling(window=150, min_periods=150).mean()
df["SMA_Active"] = df["SMA150"] if ma_period == 150 else df["SMA50"]
df["Dist_MA_Pct"] = ((df["Close"] - df["SMA_Active"]) / df["SMA_Active"]) * 100
```

Keep `Dist_SMA50_Pct` for backwards compatibility but **also** add `Dist_MA_Pct`. All downstream code should switch to `Dist_MA_Pct`.

### 1.3 Update `detect_signals(df)`

Change the signal masks to use `SMA_Active`:

```python
bullish_mask = (df["Close"] > df["SMA_Active"]) & (df["Vol_Ratio"] > 1.5) & (df["Vol_5d_Trend"] == 1.0)
bearish_mask = (df["Close"] < df["SMA_Active"]) & (df["Vol_Ratio"] > 1.5)
```

### 1.4 Update `calculate_money_flow_score(row)`

Read from `Dist_MA_Pct` instead of `Dist_SMA50_Pct`. No formula change.

### 1.5 Update `detect_exit_warnings(df)`

Read distance from `Dist_MA_Pct` instead of `Dist_SMA50_Pct`. Keep the 15% overextension threshold.

### 1.6 Update `fetch_ohlcv` and minimum data guard

- `fetch_ohlcv` currently fetches `days=400` — keep as is, sufficient for SMA150.
- In `scan_tickers`, change the `len(df) < 55` guard to:
  ```python
  min_required = 160 if is_investor else 55
  if df is None or len(df) < min_required:
      ...
  ```

### 1.7 Update `build_chart(df, ticker, company_name="", is_investor=False)`

- Plot **both** SMA50 and SMA150 as lines on the price chart
- The **active** MA gets the prominent blue line (`#2196f3`, width 2.5)
- The inactive MA gets a thinner dashed grey line (`#718096`, width 1.5, dash="dot")
- Legend labels: `"SMA 150 (Investor)"` and `"SMA 50 (Trader)"`
- Update the hover templates that reference `Dist_SMA50_Pct` to use `Dist_MA_Pct`

### 1.8 Update scanner results column

The results table column `"% from SMA50"` should be renamed dynamically to `"% from SMA150"` or `"% from SMA50"` based on `is_investor`. Use a single key `"% from MA"` internally and rename at display time.

### 1.9 Update sidebar tips

Replace the hardcoded "Felix's 5 Rules" block (lines ~1251–1261) with:

```python
ma_label = "SMA150" if is_investor else "SMA50"
mode_label = "Investor" if is_investor else "Trader"
st.markdown(f"""
<div style="color:#4a5568;font-size:0.78rem;line-height:1.6;">
<b style="color:#718096;">Felix's Rules ({mode_label} Mode):</b><br>
1. Price above {ma_label}<br>
2. Volume spike &gt;1.5× avg (or &gt;3× = Heavy)<br>
3. Rising 5-day volume trend<br>
4. Risk ≤1% per trade<br>
5. Target 2:1 reward-to-risk<br><br>
<em>"Follow the green — follow the money."</em>
</div>
""", unsafe_allow_html=True)
```

Also update the Filter & Sort dropdown (line ~1241) so `"% above SMA50 ↓"` becomes `f"% above {ma_label} ↓"`.

---

## Change 2 — Heavy Distribution / Heavy Accumulation Signals

### 2.1 Add tiered volume signals in `detect_signals`

Add two new signal levels above the existing `1.5×` threshold. Felix's description of true institutional flow is `5–10×` normal volume — `3×` is a conservative floor.

```python
df["Signal"]  = "Neutral"
df["Bullish"] = False
df["Bearish"] = False
df["Heavy"]   = False  # NEW — flags institutional-grade volume

# Existing soft signals (unchanged)
soft_bullish = (df["Close"] > df["SMA_Active"]) & (df["Vol_Ratio"] > 1.5) & (df["Vol_5d_Trend"] == 1.0)
soft_bearish = (df["Close"] < df["SMA_Active"]) & (df["Vol_Ratio"] > 1.5)

# NEW: heavy signals — likely institutional
heavy_bullish = (df["Close"] > df["SMA_Active"]) & (df["Vol_Ratio"] > 3.0) & (df["Vol_5d_Trend"] == 1.0)
heavy_bearish = (df["Close"] < df["SMA_Active"]) & (df["Vol_Ratio"] > 3.0)

df.loc[soft_bullish, "Signal"]  = "Bullish Accumulation"
df.loc[soft_bullish, "Bullish"] = True
df.loc[soft_bearish, "Signal"]  = "Bearish Distribution"
df.loc[soft_bearish, "Bearish"] = True

# Heavy overrides soft
df.loc[heavy_bullish, "Signal"]  = "🟢🟢 Heavy Accumulation"
df.loc[heavy_bullish, "Heavy"]   = True
df.loc[heavy_bearish, "Signal"]  = "🔴🔴 Heavy Distribution"
df.loc[heavy_bearish, "Heavy"]   = True
```

### 2.2 Update the filter dropdown

In the sidebar `Filter & Sort` section, add two new filter options:

```python
filter_mode = st.selectbox(
    "Filter",
    ["Show All", "🟢 Bullish Only", "🔴 Bearish Only",
     "🟢🟢 Heavy Accumulation Only", "🔴🔴 Heavy Distribution Only",
     "⚠️ Warnings Only", "⚪ Neutral Only"]
)
```

Wire the new filters through to the results-filtering logic.

### 2.3 Update chart markers

In `build_chart`, add a third and fourth marker series for heavy signals:
- Heavy Accumulation: larger arrow-up marker (size 18 instead of 13), brighter green `#00ff00`
- Heavy Distribution: larger arrow-down marker (size 18), brighter red `#ff0000`

Plot heavy markers **after** the soft markers so they appear on top.

---

## Change 3 — Buy Eligible Flag (Covenant #1)

### 3.1 Add column to `scan_tickers` output

After computing `dist`, add:

```python
buy_eligible = bool(price > float(latest["SMA_Active"])) if pd.notna(latest["SMA_Active"]) else False
```

Add to the result dict:
```python
"Buy Eligible": "✅" if buy_eligible else "🚫",
```

### 3.2 Add filter option

Extend the filter dropdown again:
```python
"✅ Buy Eligible Only",
"🚫 Never Buy (below MA)",
```

### 3.3 Display

The `Buy Eligible` column should appear **immediately after** `Signal` in the displayed dataframe. It's the most actionable column in the table — a hard yes/no Felix rule.

---

## Non-Goals

Do not implement any of the following — they're out of scope for this iteration:

- Swing-low exit refinement
- Predetermined exit journal / trade log
- Portfolio-level outcome dashboard (big win / small win / small loss tracking)
- Higher-highs / lower-highs structural volume analysis
- Changes to position sizing, P/E, sector heatmap, cross-market, or Value+Flow logic

---

## Acceptance Criteria

When done, the following must all be true:

1. Toggling between Investor and Trader mode visibly changes which MA line is bold on the chart and switches every threshold, label, and signal in the app
2. In Investor mode, a stock with fewer than 160 days of data shows "No Data" rather than erroring
3. `Heavy Accumulation` and `Heavy Distribution` appear in the Signal column when volume exceeds 3× average with the matching trend direction
4. The Buy Eligible column shows ✅ or 🚫 for every scanned stock and matches `Close > active MA`
5. Filtering by Heavy / Buy Eligible / Never Buy returns the expected subset
6. The existing trader-mode behaviour with SMA50 is **identical** to the current app when Trader mode is selected (regression test: scan FTSE 100 in Trader mode, compare Money Flow Scores — should match exactly)
7. No changes to position sizing, P/E logic, sector heatmap, or cross-market tab

---

## Implementation Order

Do the changes in this order — each one is testable before moving to the next:

1. Change 1.2 + 1.4 + 1.5 (calculate_indicators, money flow, exit warnings — add `Dist_MA_Pct` infrastructure with `is_investor=False` default — should be a no-op)
2. Change 1.3 (detect_signals using SMA_Active)
3. Change 1.1 + 1.6 + 1.8 + 1.9 (sidebar toggle, data guard, dynamic column rename, sidebar tips)
4. Change 1.7 (chart with both MA lines)
5. Change 2 (heavy signals + filters + chart markers)
6. Change 3 (Buy Eligible flag + filters)

After each step, run the app locally with a single FTSE stock (e.g. AstraZeneca AZN.L) and confirm nothing has broken before proceeding.
