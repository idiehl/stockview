# Tradeview 📈  
A sleek, Streamlit-based market dashboard + paper trading sandbox with live refresh, watchlists, portfolio analytics, and a lightweight SQLite-backed trade ledger.

> **Disclaimer:** Tradeview is a demo / portfolio project. Quotes are indicative and may be delayed. **Paper trading only. Not investment advice.**

License: MIT

---

## Table of Contents
- [What this is](#what-this-is)
- [Key features](#key-features)
- [Tech stack](#tech-stack)
- [How it works](#how-it-works)
- [Local setup](#local-setup)
- [Run the app](#run-the-app)
- [Deploy on Streamlit Community Cloud](#deploy-on-streamlit-community-cloud)
- [App tour](#app-tour)
- [Data providers + rate limits](#data-providers--rate-limits)
- [Database + trade ledger](#database--trade-ledger)
- [Troubleshooting](#troubleshooting)
- [Recommended next improvements](#recommended-next-improvements)
- [License](#license)

---

## What this is
**Tradeview** is a compact "trading terminal"-style dashboard meant to showcase:
- clean UI layout patterns in Streamlit
- real market charting (Plotly)
- a paper trading workflow
- persistent-ish storage via SQLite
- live refresh controls and caching strategies

It’s designed to be:
- **fast** (cached requests)
- **reliable** (fallback data provider)
- **presentable** (polished, commercial UI language)

---

## Key features

### 🧭 Navigation / Pages
- **🏠 Dashboard**
  - Primary Symbol “hero” banner
  - Live chart with bottom-right HUD (LIVE + Play/Pause)
  - Toolbar below chart: Window / Granularity / Chart + data source label
- **📊 Markets**
  - Same layout as Dashboard but with indicators support (SMA / Volume)
- **🧾 Order Entry**
  - Paper Buy/Sell (Market or Limit)
  - Quote preview panel
- **💼 Portfolio**
  - Aggregated holdings, market value, and unrealized P&L
- **🧱 Activity**
  - Full trade log + CSV export
- **⚙️ User Settings**
  - Theme picker
  - Market data provider picker (Auto / Yahoo / Stooq)
  - Diagnostics toggle
  - Live refresh toggle (1s)
  - Starting cash + full reset

### 📌 Watchlist sidebar
- Comma-separated tickers
- Quick “Use {SYMBOL}” buttons to set the Primary Symbol
- Optional “Refresh quotes” to populate watchlist prices

### 🔄 Live chart refresh
- Live refresh is **ON by default**
- HUD in the chart block allows **Play/Pause** without cluttering the sidebar
- Uses `streamlit_autorefresh` to rerun every 1 second when live

---

## Tech stack
- **Python**
- **Streamlit** (UI + layout)
- **Plotly** (interactive charts)
- **pandas** (data manipulation)
- **yfinance** (Yahoo market data)
- **streamlit-autorefresh** (live mode)
- **SQLite** (paper trades + metadata)

---

## How it works

### 1) Market data flow
Tradeview attempts to fetch OHLCV data in this order:
1. **Yahoo Finance (via `yfinance`)**  
2. If Yahoo fails or returns empty data, fallback to **Stooq** (daily bars)

This makes Streamlit Cloud deployments much more stable, since Yahoo can rate-limit or block cloud IP ranges.

### 2) Caching strategy
Market calls are cached so the app stays fast:
- **History** cached (TTL ~ 20s)
- **Quote** cached (TTL ~ 2s)
- **Stooq daily** cached longer (TTL ~ 300s)

There is also a **“Clear cache”** button in the sidebar to wipe cached responses.

### 3) Live mode
When live mode is enabled:
- the app triggers a rerun every ~1 second
- the LIVE timestamp updates
- history/quote data refreshes according to cache TTLs

The Play/Pause control toggles `st.session_state["live_playing"]`.

### 4) Paper trading ledger
Orders write rows into a SQLite database (`portfolio.db`).  
Portfolio and P&L are derived from that trade history.

---

## Local setup

### Prerequisites
- Python **3.10+** recommended (works in newer versions too)
- Git

### Install dependencies
From the project directory:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

---

## Run the app

From the project directory (with your venv activated):

```bash
streamlit run app.py
```

---

## App tour (what to show in a demo)

### 🏠 Dashboard
- Primary symbol banner + live chart with Play/Pause HUD
- **Watchlist snapshot table** (compact): short-term returns, 52-week context, and sparklines

### 📊 Markets
- Chart + indicators (SMA 20/50, optional volume)
- **Sigma Slice Analysis Tool** (new!)
  - Dual-handle range slider to select any time window
  - Computes mean, std dev, high/low for the selected slice
  - Shows current price's sigma distance from the sample
  - Visual shading on chart for selected region
  - Supports intraday data (1m, 5m, 15m, 1h) for short-term analysis
- **Key Levels panel**: Day/Week/52-week highs and lows, volume stats
- **Watchlist snapshot table** (compact/detailed view)
  - 1D/1W/1M returns
  - 52-week high/low + range position
  - volatility + "sigma distance" to 52-week high/low

### 💼 Portfolio
- Holdings table (market value + unrealized P&L)
- **Analytics**
  - Equity curve built from the SQLite trade ledger + daily closes
  - Benchmark overlay (SPY buy-and-hold)
  - Drawdown chart + quick risk stats
  - Allocation donut chart

---

## Metric notes (new columns)

### 52-week sigma distance
In the watchlist table:

- **σ To High**: \((Last - 52WHigh) / σ_{usd,252}\)
- **σ To Low**: \((Last - 52WLow) / σ_{usd,252}\)
- **\(σ_{usd,252}\)** is approximated as: \(Last × stdev(daily pct returns, 252 sessions)\)

This makes the distance "unitless" (in sigmas) while still tying volatility to the current price level.

### Sigma Slice Analysis
The Sigma Slice tool on the Markets page lets you:

1. **Select any time range**: Use the dual-handle slider to pick start and end points
2. **Analyze historical volatility**: See mean, std dev, high/low for that specific window
3. **Measure current price distance**: How many sigmas is the current price from the sample mean/high/low?

This is useful for:
- Comparing current price to a specific historical period (e.g., "How does today's price compare to last month's range?")
- Identifying when price has moved significantly from a baseline
- Analyzing volatility across different timeframes (intraday to yearly)

**Intraday data limits** (Yahoo Finance):
- 1m: ~7 days
- 5m/15m: ~60 days
- 1h: ~730 days

---

## Demo script (30–60 seconds)
- Open **Dashboard** → toggle Live mode → show chart HUD and source label
- Show **Watchlist snapshot** → point out 52-week context + sparklines
- Go to **Markets** → demo the **Sigma Slice** tool:
  - Select a short intraday interval (e.g., 5m)
  - Drag the slider handles to select a historical window
  - Show the shaded region on the chart and sigma stats panel
- Go to **Order Entry** → place a small paper BUY
- Go to **Portfolio** → show holdings update and equity curve vs SPY
- Go to **Activity** → export CSV
---

## Recommended next improvements
- Add a “details drawer” for a selected row in the watchlist table (news, fundamentals, key ratios)
- Add position sizing helpers (risk-based sizing, max % of portfolio)
- Add import/export of `portfolio.db` or a “sample trades” seed
- Add per-symbol caching diagnostics (last fetch time, cache hits)
- Add test coverage for the analytics helpers (pure functions)
