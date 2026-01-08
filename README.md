# Tradeview 📈

A polished **Streamlit market dashboard + paper trading sandbox** with watchlists, indicators, portfolio analytics, and a lightweight **SQLite trade ledger**.

> **Disclaimer:** Tradeview is a demo / portfolio project. Quotes are indicative and may be delayed. **Paper trading only. Not investment advice.**

---

## Table of Contents
- [What this is](#what-this-is)
- [Demo video](#demo-video)
- [Key features](#key-features)
- [Tech stack](#tech-stack)
- [How it works](#how-it-works)
- [Local setup](#local-setup)
- [Run the app](#run-the-app)
- [Deploy on Streamlit Community Cloud](#deploy-on-streamlit-community-cloud)
- [App tour (demo flow)](#app-tour-demo-flow)
- [Metric notes](#metric-notes)
- [Database + trade ledger](#database--trade-ledger)
- [Master Log (version history)](#master-log-version-history)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Demo video

[![Tradeview demo video](docs/media/thumbnail.png)](https://youtu.be/_ikvd5eztsE)

Watch on YouTube: `https://youtu.be/_ikvd5eztsE`

---

## What this is
**Tradeview** is a compact “trading terminal”-style dashboard meant to showcase:
- clean UI/layout patterns in Streamlit
- interactive charting (Plotly)
- a paper trading workflow (orders → ledger → portfolio)
- credible portfolio analytics (equity curve, drawdown, allocation)
- resilient market data fetching (timeouts, caching, provider fallback)

Design goals:
- **fast** reruns via caching
- **resilient** to partial provider failures (fault-isolated watchlist rows)
- **presentable** for a portfolio / social demo

---

## Key features

### 🧭 Pages
- **🏠 Dashboard**
  - Primary symbol “hero” banner + chart
  - Watchlist snapshot (high-signal columns + sparklines)
  - **Sigma window statistics** (volatility context for the visible chart window)
- **📊 Markets**
  - Chart + indicators (SMA 20/50, optional volume)
  - Key Levels panel (day/week/52w high/low + volume)
  - Sigma window statistics (same as Dashboard)
- **🧾 Order Entry**
  - Paper Buy/Sell (market/limit) with basic validation
- **💼 Portfolio**
  - Holdings + unrealized P&L
  - Analytics: equity curve vs benchmark (SPY), drawdown, allocation
- **🧱 Activity**
  - Trade log + CSV export
- **⚙️ User Settings**
  - Theme, data provider mode, diagnostics
  - Live refresh toggle + interval
  - Starting cash + full reset

### 📌 Sidebar watchlist
- Comma-separated tickers with quick “Use {SYMBOL}” buttons
- Manual “Refresh quotes” and “Clear cache” controls

---

## Tech stack
- **Python**
- **Streamlit** (UI)
- **Plotly** (charts)
- **pandas** (data manipulation)
- **yfinance** (Yahoo Finance market data)
- **SQLite** (trade ledger: local-only by default)
- Optional: **streamlit-autorefresh** (live refresh when enabled)

---

## How it works

### 1) Market data providers (resilient)
Tradeview attempts to fetch OHLCV data in this order:
1. **Yahoo Finance** (via `yfinance`)
2. If Yahoo fails or returns empty data, fallback to **Stooq** (daily bars)

This fallback helps Streamlit Cloud deployments stay stable when Yahoo rate-limits cloud IP ranges.

### 2) Caching strategy (fast reruns)
Remote calls are cached to keep the app snappy:
- **History**: cached (short TTL)
- **Quotes**: cached (very short TTL)
- **Fallback daily** (Stooq): cached longer

There’s also a **“Clear cache”** button in the sidebar.

### 3) Live refresh (opt-in)
Live refresh is **disabled by default** to avoid layout shifting while you interact with the chart.
Enable it in **User Settings** if you want periodic reruns.

### 4) Paper trading ledger
Orders are recorded into a local SQLite DB (`portfolio.db`). Portfolio and P&L are derived from trade history.

---

## Local setup

### Prerequisites
- Python **3.10+** recommended
- Git

### Install dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Run the app

```bash
streamlit run app.py
```

---

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. In Streamlit Community Cloud, click **New app** and choose:
   - **Repository**: your GitHub repo
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. Click **Deploy**.

Notes:
- Streamlit Cloud installs from `requirements.txt`.
- Streamlit Cloud has an **ephemeral filesystem**. Local files like `portfolio.db` are not durable between restarts/redeploys.
  - For a portfolio demo, that’s usually fine (it behaves like a “fresh paper account”).
  - If you want persistence later, you’ll need an external DB or an upload/download mechanism.

---

## App tour (demo flow)

### 30–60 second demo script
- Open **Dashboard** → show clean hero + watchlist snapshot
- Switch **Window/Granularity** → point out **Sigma window statistics** update with the visible data
- Go to **Markets** → toggle indicators (SMA/volume) + show Key Levels
- Go to **Order Entry** → place a small paper BUY
- Go to **Portfolio** → show holdings + equity curve vs SPY + drawdown
- Go to **Activity** → export CSV

---

## Metric notes

### 52-week sigma distance (watchlist)
In the watchlist table:
- **σ To High**: \((Last - 52WHigh) / σ_{usd,252}\)
- **σ To Low**: \((Last - 52WLow) / σ_{usd,252}\)
- \(σ_{usd,252}\) is approximated as: \(Last × stdev(daily pct returns, 252 sessions)\)

### Sigma window statistics (Dashboard/Markets)
Tradeview also displays “window statistics” for the *currently visible chart window* (based on your selected Window + Granularity):
- mean price, standard deviation, high/low, and where the current price sits relative to that distribution

---

## Database + trade ledger
- Local ledger file: `portfolio.db` (created automatically if missing)
- Reset behavior: use **User Settings → Reset** to clear trades / restore starting cash

Streamlit Cloud note: the local DB is not durable across restarts. For hosted persistence, use an external DB.

---

## Master Log (version history)
This repo keeps a running version history:
- Source: `docs/master_log/Master_Log.md`
- Rendered: `docs/master_log/Master_Log.pdf`

Build the PDF:
- Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_master_log.ps1
```

- Linux/macOS (bash):

```bash
bash scripts/build_master_log.sh
```

---

## Troubleshooting
- **Yahoo returns empty / rate-limited**: try Provider Mode **Auto** or **Stooq** (daily only).
- **Chart seems stale**: use **Refresh quotes** or **Clear cache** in the sidebar.
- **Weird local state**: restart Streamlit; then Clear cache.

---

## License
MIT
