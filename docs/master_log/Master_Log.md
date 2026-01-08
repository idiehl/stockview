# Tradeview — Master Log

**Project slug:** `SV`  
**Current cycle:** `C01`  
**Started:** 2026-01-03

> This log is the running version history. Append new entries to the end.
> Each entry ID uses: `SV-<CYCLE>-<YYYYMMDD>-<NNN>`.

## Index
- (Add one bullet per entry: `[ID] — Title`)
- [SV-C01-20260106-001] — Watchlist sigma metrics + portfolio analytics
- [SV-C01-20260106-002] — Rebrand to Tradeview + UI polish
- [SV-C01-20260106-003] — Sigma Slice Analysis Tool

---

## SV-C01-20260103-001 — Log initialized

**Type:** Docs  
**Context:** Establish master log + indexing standard  
**Change summary:** Created initial Master_Log.md scaffold and PDF styling/build scripts  
**Rationale / tradeoffs:** Markdown source enables consistent PDF rendering + easy diffing  
**Files touched:** `docs/master_log/*`, `scripts/build_master_log.*`  
**Commands run:** N/A  
**Verification:** N/A  
**Notes:** Install Node + md-to-pdf (or choose another renderer) to build PDF  
**Concepts:** @concept:master-log @concept:indexing-standard

## SV-C01-20260106-001 — Watchlist sigma metrics + portfolio analytics

**Type:** Feature  
**Context:** Improve usability + demo polish for portfolio/social sharing  
**Change summary:** Added watchlist snapshot tables (compact/detailed) with 52-week range and sigma-distance metrics; added portfolio analytics (equity curve vs SPY, drawdown, allocation, basic risk stats); improved handling of missing quotes so holdings don’t show misleading $0 pricing.  
**Rationale / tradeoffs:** Kept changes lightweight and resilient by reusing existing cached provider functions (Yahoo/Stooq) and keeping calculations in small helpers. Equity curve is an approximation using daily Close data and end-of-day positions, which is “demo-grade” but credible for showcasing data/UX patterns.  
**Files touched:** `app.py`, `README.md`, `docs/master_log/Master_Log.md`, `docs/master_log/Master_Log.pdf`  
**Commands run:** `python -m compileall .` ; `powershell -ExecutionPolicy Bypass -File scripts/build_master_log.ps1`  
**Verification:** Navigated Dashboard/Markets/Portfolio; verified watchlist metrics render with partial symbol failures; verified portfolio analytics render with at least one holding and compares vs SPY when data available.  
**Notes:** Sigma distance uses \(σ_{usd,252} = Last × stdev(daily pct returns, 252 sessions)\); daily Close-based analytics may differ from real broker marks/fills.  
**Concepts:** @concept:watchlist-metrics @concept:portfolio-analytics @concept:market-data-cache

## SV-C01-20260106-002 — Rebrand to Tradeview + UI polish

**Type:** Feature / Refactor  
**Context:** Preparing app for social media portfolio showcase; user requested rebrand, responsive improvements, and reduced chart flicker  
**Change summary:**  
- Renamed app from "Cashbook Lite" to "Tradeview" (page title, sidebar, hero, README)
- Added Volume and Avg Vol (20D) columns to watchlist snapshot
- Improved watchlist table responsive scaling (CSS width rules)
- Reduced chart flicker: increased refresh interval to 3s, pre-allocated chart container height, added skeleton placeholder CSS
- Added color-coded returns (🟢/🔴 emoji indicators) and P&L formatting
- Added CSS media queries for tablet/mobile breakpoints
- Added fade-in animations for hero, metrics cards, symbol banner, and chart block  
**Rationale / tradeoffs:** Used emoji indicators for color-coding since st.dataframe doesn't support HTML in cells; 3s refresh interval balances "live feel" with reduced layout shift; animations are subtle (0.4-0.5s) to avoid feeling sluggish  
**Files touched:** `app.py`, `README.md`, `docs/master_log/Master_Log.md`, `docs/master_log/Master_Log.pdf`  
**Commands run:** `streamlit run app.py`  
**Verification:** App boots; branding shows "Tradeview"; watchlist includes Volume; chart container doesn't collapse during refresh; animations play on page load  
**Notes:** True incremental chart updates (WebSocket-style) not possible in vanilla Streamlit; mitigations reduce perceived flicker significantly  
**Concepts:** @concept:ui-polish @concept:responsive-design @concept:animations

## SV-C01-20260106-003 — Sigma Slice Analysis Tool

**Type:** Feature  
**Context:** User requested flexible sigma analysis tool that allows arbitrary time range selection instead of fixed 52-week window  
**Change summary:**  
- Added intraday data support (1m, 5m, 15m, 1h intervals) with appropriate caching (10s TTL vs 20s for daily)
- Implemented `compute_slice_sigma_metrics()` for arbitrary time range sigma calculations
- Added dual-handle range slider on Markets page for selecting analysis window
- Added stats panel showing slice mean, std dev, high/low, and current price's sigma distance
- Added visual shading on chart (Plotly vrect) for selected slice region
- Added collapsible "Key Levels" panel showing day/week/52-week highs, lows, and volume
- Added edge case handling: empty slice warnings, intraday data limit warnings, >3σ alerts  
**Rationale / tradeoffs:**  
- Used Streamlit's native `st.slider` with 2 values for range selection (simpler than custom Plotly drag-lines)
- Slider operates on bar indices (not timestamps) for simplicity across all intervals
- Intraday data has Yahoo limits (1m: ~7d, 5m/15m: ~60d, 1h: ~730d) - UI warns users
- Stats panel placed alongside chart for easy comparison  
**Files touched:** `app.py`, `README.md`, `docs/master_log/Master_Log.md`, `docs/master_log/Master_Log.pdf`  
**Commands run:** `streamlit run app.py`  
**Verification:**  
- App boots without errors
- Range slider appears below chart on Markets page
- Selecting a range shades that region on the chart
- Stats panel updates with sigma metrics for selected range
- Intraday intervals (1m, 5m, 15m, 1h) fetch correctly
- Key Levels panel shows day/week/52w highs and lows
- Edge cases handled (empty slice, insufficient data)  
**Notes:** Sigma calculations use price std dev (not returns std dev) for the slice, making it directly comparable to price distances. For returns-based volatility, see the 52-week metrics in the watchlist.  
**Concepts:** @concept:sigma-slice @concept:intraday-data @concept:volatility-analysis
