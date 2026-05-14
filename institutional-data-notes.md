# Institutional Data Integration Notes

Documentation for the three institutional data sources added in the
`🔬 Institutional Data (Beta)` sidebar section.

---

## Integration 1 — SEC EDGAR Form 4 Insider Buys

### What it does
Counts open-market and private purchase transactions (transaction code **P**)
filed on Form 4 by Directors and Officers for a given US ticker over the last
90 days.

### Endpoint
```
# CIK lookup (ticker → 10-digit CIK)
GET https://www.sec.gov/files/company_tickers.json

# Company submissions (filings list)
GET https://data.sec.gov/submissions/CIK{cik_padded}.json

# Individual Form 4 XML
GET https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_clean}/{primary_doc}
```

### Authentication
No API key required. EDGAR requires a descriptive `User-Agent` header:
```
User-Agent: Follow-the-Green Research research@example.com
```

### Rate limits
EDGAR asks for a maximum of **10 requests per second**. The integration caps
at 20 Form 4 filings per ticker and uses `@st.cache_data(ttl=86400)` (24-hour
cache), so the burst only happens once per ticker per day.

### Free tier limits
Unlimited — EDGAR is a US federal government system with no access tiers.

### Known failure modes
| Symptom | Cause | Mitigation |
|---|---|---|
| Column shows `N/A` | Ticker not found in EDGAR CIK map (e.g. foreign ADR listed under a different symbol) | Check EDGAR directly at `https://www.sec.gov/cgi-bin/browse-edgar` |
| Column shows `N/A` | Form 4 XML uses an unexpected structure or namespace | Logged silently; filing is skipped |
| Column shows `0` | Insiders filed Form 4s but only for sales/gifts, not purchases | Expected — no open-market buys in the window |
| Slow scan | First run populates the 24-hour cache; subsequent runs are instant | Users see normal Streamlit progress bar |

### Column output
- `Insider Buys (90d)` — integer count of qualifying purchase transactions
- `None` displayed as blank; `0` displayed as `0`

### Triple Confluence upgrade
When **SEC Form 4 Insider Buys** is toggled ON, the `💎 Value+Flow` flag is
upgraded to `💎💎 Triple Confluence` for any row where:
- Money Flow Score ≥ 60 (institutional volume accumulation)
- P/E < Sector Average P/E (undervalued vs peers)
- Insider Buys (90d) > 0 (management buying their own shares)

---

## Integration 2 — FMP 13F Institutional Holdings (STUB)

### Current status
**Disabled** — the FMP 13F endpoint requires a registered API key even on
the free tier. The `📊 FMP 13F Net Position Δ` toggle is rendered as
`disabled=True` in the sidebar and the `fetch_13f_change()` function always
returns `None`.

### Endpoint (when activated)
```
GET https://financialmodelingprep.com/api/v3/institutional-holder/{symbol}?apikey={key}
```
Response contains a list of institutional holders with `shares` and
`dateReported`. To compute net change, compare the two most recent quarters.

### Free tier
- Register at: https://financialmodelingprep.com/developer/docs/
- Free tier: 250 requests/day, no credit card required
- The `institutional-holder` endpoint is available on the free tier

### Activation path
1. Register at FMP and obtain a free API key.
2. Add the key to `.streamlit/secrets.toml`:
   ```toml
   [fmp]
   api_key = "your_key_here"
   ```
   Or set the environment variable `FMP_API_KEY=your_key_here`.
3. Replace the stub in `app.py`:

```python
# Replace fetch_13f_change() with:
@st.cache_data(ttl=86400 * 7, show_spinner=False)
def fetch_13f_change(ticker: str) -> str | None:
    """
    Fetch the most recent quarter-on-quarter change in institutional holdings
    from FMP's 13F endpoint. Returns "▲ Added", "▼ Reduced", "— Unchanged",
    or None on failure.
    """
    try:
        import os
        api_key = (
            st.secrets.get("fmp", {}).get("api_key")
            or os.environ.get("FMP_API_KEY")
        )
        if not api_key:
            return None
        url = (
            f"https://financialmodelingprep.com/api/v3"
            f"/institutional-holder/{ticker}?apikey={api_key}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2:
            return None
        # Most recent two quarters, sorted by date descending
        data.sort(key=lambda x: x.get("dateReported", ""), reverse=True)
        latest_shares = int(data[0].get("shares", 0))
        prev_shares   = int(data[1].get("shares", 0))
        if latest_shares > prev_shares:
            return "▲ Added"
        elif latest_shares < prev_shares:
            return "▼ Reduced"
        else:
            return "— Unchanged"
    except Exception:
        return None
```

4. In the sidebar section, remove `disabled=True` from the `use_13f_data` toggle.

### Known failure modes
| Symptom | Cause |
|---|---|
| `{"Error Message": "..."}` in response | Invalid or expired API key |
| Empty list `[]` | FMP has no 13F data for that ticker (common for non-US or small-cap) |
| 429 Too Many Requests | Free tier rate limit (250/day) exceeded |

---

## Integration 3 — FCA Short Position Register

### What it does
Downloads the FCA's daily short position register as an XLSX file and
matches each FTSE 100 ticker to its disclosed short positions, summing all
position holders per company.

### Endpoint
```
GET https://www.fca.org.uk/publication/data/short-positions-daily-update.xlsx
```

### Authentication
No API key required — public FCA publication.

### Cache TTL
12 hours (`ttl=43200`). The FCA typically updates the register daily on
business days; 12-hour cache balances freshness against download overhead.

### Free tier limits
Unlimited — public FCA regulatory data.

### XLSX structure
The file contains these columns (after 2–4 metadata header rows):
| Column | Description |
|---|---|
| Position Holder | Name of the entity holding the short |
| Issuer Name | Company name (used for matching to FTSE tickers) |
| ISIN of Share or Unit | ISIN code (not currently used for matching) |
| Net Short Position (%) | Short as a % of total issued share capital |
| Date Position Was Created | Original disclosure date |
| Date of Most Recent Position | Last updated date |

### Name matching
The FCA uses full legal names (e.g. `ASTRAZENECA PLC`) while the app uses
common names (e.g. `AstraZeneca`). The `_match_fca_short()` function uses
a four-level matching strategy:
1. Exact upper-case match
2. App name is a substring of FCA name
3. FCA name is a substring of app name
4. First significant word (≥ 4 characters) with a unique result

### Column output
- `Short %` — formatted string, e.g. `"3.25% 🩸"` (≥ 3 %) or `"1.20%"` (< 3 %)
- `None` (blank) if no match found or toggle is OFF

### Known failure modes
| Symptom | Cause | Mitigation |
|---|---|---|
| Column blank for known shorted stock | Name-matching failed | Check FCA register manually; update `_match_fca_short()` with a direct override dict |
| Download timeout | FCA website occasionally slow | TTL cache means this only blocks once per 12 hours; subsequent loads use cached data |
| `openpyxl` parse error | FCA changed XLSX format | Update `header` detection logic in `fetch_fca_shorts()` |
| All columns blank | FCA changed the file URL | Update `url` in `fetch_fca_shorts()` |

---

## Upgrading to Paid Data Sources

If you later want higher reliability or more data depth:

| Current (Free) | Paid Alternative | Notes |
|---|---|---|
| SEC EDGAR Form 4 (self-parsed) | Refinitiv / Bloomberg insider feed | Pre-parsed, cleaner data |
| FMP 13F (free tier, 250 req/day) | FMP paid tier or Quandl | Higher rate limits, more history |
| FCA XLSX (daily batch) | S3MI / FinancialModellingPrep | Real-time short data |

All three integrations are isolated in their own cached functions, making it
straightforward to swap in a paid source by replacing only the fetch function
body while keeping the rest of the app unchanged.
