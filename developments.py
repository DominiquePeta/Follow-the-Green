"""
developments.py — "Developments to Watch" tab.

Pure keyword scanner: no pre-defined themes, no curated baskets.
Scans SEC EDGAR + UK RNS announcements for a flat list of emerging
keywords, surfaces which FTSE 100 / S&P 500 large-caps mention them.
Plus ClinicalTrials.gov for biotech-flavoured keywords.
"""
from __future__ import annotations

import datetime as _dt
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st

try:
    import feedparser  # type: ignore
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False

from keywords import EMERGING_KEYWORDS, BIOTECH_KEYWORD_HINTS


SEC_FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index"
CLINICALTRIALS_URL = "https://clinicaltrials.gov/api/v2/studies"
SEC_HEADERS = {"User-Agent": "Follow-the-Green Research research@example.com"}


@st.cache_data(ttl=14400, show_spinner=False)
def sec_fulltext_search(keyword: str, days: int = 90) -> list[dict]:
    end = _dt.date.today()
    start = end - _dt.timedelta(days=days)
    params = {
        "q": f'"{keyword}"',
        "forms": "10-K,10-Q,8-K,6-K,20-F",
        "dateRange": "custom",
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
    }
    try:
        r = requests.get(SEC_FULLTEXT_URL, params=params, headers=SEC_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])
    except Exception:
        return []
    out = []
    for h in hits[:30]:
        src = h.get("_source", {})
        ciks = src.get("ciks", [])
        names = src.get("display_names", [])
        cik = ciks[0] if ciks else ""
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}" if cik else ""
        out.append({
            "company": names[0] if names else "Unknown",
            "form": src.get("form", "?"),
            "date": src.get("file_date", ""),
            "url": url,
            "keyword": keyword,
        })
    return out


@st.cache_data(ttl=14400, show_spinner=False)
def lse_rns_search(keyword: str, days: int = 90) -> list[dict]:
    if not _HAS_FEEDPARSER:
        return []
    query = f'"{keyword}" (site:investegate.co.uk OR site:londonstockexchange.com)'
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-GB&gl=GB&ceid=GB:en"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    out = []
    cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=days)
    for entry in feed.entries[:20]:
        title = entry.get("title", "")
        published = entry.get("published_parsed")
        if published:
            try:
                dt = _dt.datetime(*published[:6])
                if dt < cutoff:
                    continue
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = entry.get("published", "")
        else:
            date_str = entry.get("published", "")
        out.append({
            "company": title.split(" - ")[0] if " - " in title else title[:60],
            "headline": title,
            "date": date_str,
            "url": entry.get("link", ""),
            "keyword": keyword,
        })
    return out


def _is_large_cap(company_name: str, large_caps: dict) -> tuple[bool, str | None]:
    cname = company_name.upper().strip()
    for name, ticker in large_caps.items():
        if name.upper() in cname or cname in name.upper():
            return True, ticker
        first = name.split()[0].upper() if name.split() else ""
        if len(first) >= 4 and first in cname:
            return True, ticker
    return False, None


def scan_all_keywords(ftse_tickers: dict, sp500_tickers: dict, days: int = 90) -> pd.DataFrame:
    """Single-pass scan across every emerging keyword. Returns deduped DataFrame."""
    rows = []
    progress = st.progress(0.0, text="Scanning keywords…")
    total = len(EMERGING_KEYWORDS)

    for i, kw in enumerate(EMERGING_KEYWORDS):
        progress.progress((i + 1) / total, text=f"Scanning: {kw}")

        for hit in sec_fulltext_search(kw, days=days):
            is_match, ticker = _is_large_cap(hit["company"], sp500_tickers)
            if not is_match:
                continue
            rows.append({
                "Keyword": kw, "Ticker": ticker, "Company": hit["company"],
                "Region": "US", "Source": f"SEC {hit['form']}",
                "Date": hit["date"], "Link": hit["url"],
            })

        for hit in lse_rns_search(kw, days=days):
            is_match, ticker = _is_large_cap(hit["company"], ftse_tickers)
            if not is_match:
                continue
            rows.append({
                "Keyword": kw, "Ticker": ticker, "Company": hit["company"],
                "Region": "UK", "Source": "RNS / News",
                "Date": hit["date"], "Link": hit["url"],
            })

    progress.empty()
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["Keyword", "Ticker", "Date"]).sort_values("Date", ascending=False)
        # Aggregate stats per keyword
        agg = df.groupby("Keyword").agg(
            Mentions=("Ticker", "count"),
            UniqueIncumbents=("Ticker", "nunique"),
            LatestDate=("Date", "max"),
        ).reset_index().sort_values("UniqueIncumbents", ascending=False)
        df = df.merge(agg[["Keyword", "UniqueIncumbents"]], on="Keyword", how="left")
    return df


@st.cache_data(ttl=14400, show_spinner=False)
def clinicaltrials_search(term: str, max_studies: int = 15) -> list[dict]:
    params = {
        "query.term": term,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED",
        "filter.advanced": "AREA[Phase](PHASE2 OR PHASE3)",
        "pageSize": max_studies,
        "format": "json",
    }
    try:
        r = requests.get(CLINICALTRIALS_URL, params=params, timeout=20)
        r.raise_for_status()
        studies = r.json().get("studies", [])
    except Exception:
        return []
    out = []
    today = _dt.date.today()
    for s in studies:
        proto = s.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsor = proto.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
        nct_id = ident.get("nctId", "")
        completion = status.get("completionDateStruct", {}).get("date", "")
        is_upcoming = False
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                if _dt.datetime.strptime(completion, fmt).date() >= today:
                    is_upcoming = True
                break
            except Exception:
                continue
        phases = design.get("phases", [])
        out.append({
            "Keyword": term,
            "Phase": " / ".join(phases) if phases else "—",
            "Status": status.get("overallStatus", ""),
            "Sponsor": sponsor.get("name", ""),
            "Completion": completion,
            "Upcoming?": "📅 Yes" if is_upcoming else "—",
            "Title": ident.get("briefTitle", "")[:80],
            "Link": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
        })
    out.sort(key=lambda x: (x["Upcoming?"] != "📅 Yes", x["Completion"]))
    return out


def render_developments_tab(ftse_tickers: dict, sp500_tickers: dict) -> None:
    st.markdown("## 🔬 Developments to Watch")
    st.caption(
        "Pure emerging-keyword scanner. Watches SEC filings + UK RNS for early signs "
        "that FTSE 100 / S&P 500 incumbents are quietly positioning into new themes. "
        "Edit `keywords.py` to add or remove keywords."
    )

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        generate = st.button("🔄 Scan Keywords", type="primary", use_container_width=True)
    with col_b:
        days_window = st.selectbox("Lookback (days)", options=[30, 60, 90, 180], index=2)
    with col_c:
        st.caption(
            f"📅 {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · "
            f"{len(EMERGING_KEYWORDS)} keywords · Cached 4h · "
            f"First run ~60s, subsequent runs near-instant."
        )

    if not generate and "dev_scan_at" not in st.session_state:
        st.info(
            f"👆 Click **Scan Keywords** to run the scanner across all {len(EMERGING_KEYWORDS)} "
            "emerging keywords. Surfaces incumbents quietly mentioning new themes."
        )
        return

    if generate:
        st.session_state["dev_scan_at"] = _dt.datetime.utcnow().isoformat()

    with st.spinner(f"Scanning {len(EMERGING_KEYWORDS)} keywords…"):
        df = scan_all_keywords(ftse_tickers, sp500_tickers, days=days_window)

    if df.empty:
        st.warning("No incumbent mentions found across any keyword. Try widening the lookback window.")
        return

    # ── Summary: keywords ranked by unique-incumbent count ─────────────────
    st.markdown("---")
    st.markdown("### 🎯 Trending keywords (ranked by unique incumbents mentioning)")
    summary = df.groupby("Keyword").agg(
        Mentions=("Ticker", "count"),
        UniqueIncumbents=("Ticker", "nunique"),
        LatestDate=("Date", "max"),
        IsBiotech=("Keyword", lambda x: "🧬" if x.iloc[0] in BIOTECH_KEYWORD_HINTS else ""),
    ).reset_index().sort_values(["UniqueIncumbents", "Mentions"], ascending=False)
    summary.columns = ["Keyword", "Mentions", "Unique Incumbents", "Latest", "Biotech?"]
    st.dataframe(summary, use_container_width=True, hide_index=True)

    # ── Promotion candidates: 2+ incumbents ────────────────────────────────
    promo = df[df["UniqueIncumbents"] >= 2].copy()
    if not promo.empty:
        st.markdown("---")
        st.markdown("### 🚨 Promotion candidates (2+ incumbents mentioning)")
        st.caption("Keywords where multiple large-caps are positioning — strongest early signal.")
        display = promo[["Keyword", "Date", "Region", "Ticker", "Company", "Source"]].head(50)
        st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Per-keyword drill-down ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Drill-down by keyword")
    keyword_choice = st.selectbox(
        "Pick a keyword to see all incumbent mentions + biotech trial catalysts (if applicable)",
        options=summary["Keyword"].tolist(),
    )
    sub = df[df["Keyword"] == keyword_choice]
    st.dataframe(
        sub[["Date", "Region", "Ticker", "Company", "Source"]],
        use_container_width=True, hide_index=True,
    )
    with st.popover(f"🔗 Source links ({len(sub)})"):
        for _, r in sub.iterrows():
            st.markdown(f"- **{r['Ticker']}** ({r['Date']}) — [{r['Source']}]({r['Link']})")

    # Biotech catalyst lookup for biotech-flavoured keywords
    if keyword_choice in BIOTECH_KEYWORD_HINTS:
        st.markdown(f"#### 📅 Trial catalysts for **{keyword_choice}**")
        with st.spinner("Pulling ClinicalTrials.gov…"):
            trials = clinicaltrials_search(keyword_choice)
        if trials:
            trials_df = pd.DataFrame(trials)
            st.dataframe(
                trials_df[["Upcoming?", "Phase", "Status", "Sponsor", "Completion", "Title"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No Phase 2/3 trials found.")
