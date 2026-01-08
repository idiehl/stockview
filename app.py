import sqlite3
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Tradeview",
    page_icon="📈",
    layout="wide",
)

APP_NAME = "Tradeview"
APP_TAGLINE = "Market monitor • Paper trading • Portfolio analytics"
DB_PATH = "portfolio.db"

_EXECUTOR = ThreadPoolExecutor(max_workers=6)


# =========================================================
# SAFE EXECUTION
# =========================================================
def run_with_timeout(fn, timeout_sec: float):
    fut = _EXECUTOR.submit(fn)
    try:
        return fut.result(timeout=timeout_sec)
    except FuturesTimeoutError:
        return None
    except Exception:
        return None


# =========================================================
# THEME / STYLES
# =========================================================
def inject_css(theme_name: str) -> None:
    if theme_name == "Neon (Dark)":
        bg = "#070A12"
        panel = "rgba(255,255,255,0.06)"
        card = "rgba(255,255,255,0.08)"
        text = "#E6EAF2"
        muted = "#9AA4B2"
        accent = "#00E5FF"
        accent2 = "#A855F7"
        border = "rgba(0,229,255,0.28)"
        plotly_template = "plotly_dark"
    elif theme_name == "Dark":
        bg = "#0B1220"
        panel = "rgba(255,255,255,0.05)"
        card = "rgba(255,255,255,0.07)"
        text = "#E5E7EB"
        muted = "#9CA3AF"
        accent = "#60A5FA"
        accent2 = "#34D399"
        border = "rgba(96,165,250,0.22)"
        plotly_template = "plotly_dark"
    else:
        bg = "#F6F8FC"
        panel = "rgba(17,24,39,0.03)"
        card = "rgba(17,24,39,0.04)"
        text = "#0F172A"
        muted = "#475569"
        accent = "#2563EB"
        accent2 = "#7C3AED"
        border = "rgba(37,99,235,0.18)"
        plotly_template = "plotly_white"

    st.session_state["plotly_template"] = plotly_template

    st.markdown(
        f"""
        <style>
        div[data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(1200px 600px at 15% 0%, {accent}22, transparent 60%),
                radial-gradient(900px 500px at 85% 10%, {accent2}22, transparent 55%),
                {bg};
        }}

        section[data-testid="stSidebar"] > div {{
            background: {panel};
            border-right: 1px solid {border};
        }}

        /* ==========================
           Entry animations
           ========================== */
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(12px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .hero {{
            background: linear-gradient(90deg, {accent}22, {accent2}22);
            border: 1px solid {border};
            border-radius: 18px;
            padding: 16px 16px;
            margin: 0.10rem 0 0.85rem 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
            animation: fadeInUp 0.5s ease-out;
        }}
        .hero h1 {{
            margin: 0;
            font-size: 1.75rem;
            letter-spacing: 0.2px;
            color: {text};
        }}
        .hero .tagline {{
            margin-top: 0.35rem;
            color: {muted};
            font-size: 0.98rem;
        }}

        /* Cards */
        div[data-testid="stMetric"] {{
            background: {card};
            border: 1px solid {border};
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.18);
            animation: fadeInUp 0.4s ease-out;
            animation-fill-mode: both;
        }}
        div[data-testid="stMetric"]:nth-child(1) {{ animation-delay: 0.05s; }}
        div[data-testid="stMetric"]:nth-child(2) {{ animation-delay: 0.1s; }}
        div[data-testid="stMetric"]:nth-child(3) {{ animation-delay: 0.15s; }}
        div[data-testid="stMetric"]:nth-child(4) {{ animation-delay: 0.2s; }}
        div[data-testid="stDataFrame"] {{
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid {border};
            width: 100% !important;
            max-width: 100% !important;
        }}
        div[data-testid="stDataFrame"] > div {{
            width: 100% !important;
        }}
        div[data-testid="stDataFrame"] iframe {{
            width: 100% !important;
        }}

        /* Default buttons */
        .stButton>button {{
            background: linear-gradient(90deg, {accent}, {accent2});
            color: white;
            border: 0;
            border-radius: 12px;
            padding: 10px 16px;
            font-weight: 700;
        }}

        .small-muted {{
            color: {muted};
            font-size: 12px;
        }}

        /* ==========================
           Primary symbol emphasis
           ========================== */
        .symbol-banner {{
            border-radius: 18px;
            border: 1px solid {border};
            background: linear-gradient(90deg, {accent}1f, {accent2}1f);
            padding: 14px 16px;
            box-shadow: 0 10px 26px rgba(0,0,0,0.16);
            margin: 0.25rem 0 0.55rem 0;
            animation: fadeInUp 0.45s ease-out 0.1s both;
        }}
        .symbol-banner .label {{
            font-size: 0.85rem;
            opacity: 0.9;
            color: {muted};
            margin-bottom: 2px;
        }}
        .symbol-banner .value {{
            font-size: 2.05rem;
            font-weight: 900;
            letter-spacing: 0.6px;
            color: {text};
            line-height: 1.05;
        }}
        .symbol-banner .sub {{
            margin-top: 6px;
            font-size: 0.92rem;
            color: {text};
            opacity: 0.92;
        }}

        /* ==========================
           Chart block + HUD (bottom-right overlay)
           ========================== */
        .chart-block {{
            position: relative;
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid {border};
            background: {panel};
            padding: 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
            animation: fadeIn 0.5s ease-out 0.15s both;
        }}
        .chart-block div[data-testid="stPlotlyChart"] {{
            margin: 0 !important;
            padding: 8px 8px 8px 8px;
        }}

        /* ==========================
           Toolbar below chart
           ========================== */
        .toolbar {{
            margin-top: 0.55rem;
            padding: 10px 12px;
            border-radius: 16px;
            border: 1px solid {border};
            background: {panel};
        }}

        /* ==========================
           Responsive tweaks
           ========================== */
        @media (max-width: 1200px) {{
            .hero h1 {{
                font-size: 1.5rem;
            }}
            .symbol-banner .value {{
                font-size: 1.6rem;
            }}
        }}

        @media (max-width: 768px) {{
            .hero {{
                padding: 12px;
                margin: 0.1rem 0 0.5rem 0;
            }}
            .hero h1 {{
                font-size: 1.25rem;
            }}
            .hero .tagline {{
                font-size: 0.85rem;
            }}
            .symbol-banner {{
                padding: 10px 12px;
            }}
            .symbol-banner .value {{
                font-size: 1.4rem;
            }}
            .symbol-banner .sub {{
                font-size: 0.8rem;
            }}
            .chart-block {{
                border-radius: 12px;
            }}
            .toolbar {{
                padding: 8px 10px;
            }}
            div[data-testid="stMetric"] {{
                padding: 10px;
                border-radius: 12px;
            }}
        }}

        @media (max-width: 480px) {{
            .hero h1 {{
                font-size: 1.1rem;
            }}
            .symbol-banner .value {{
                font-size: 1.2rem;
            }}
        }}

        footer {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DATABASE HELPERS
# =========================================================
def _connect_db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    conn = _connect_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
                qty REAL NOT NULL CHECK(qty > 0),
                price REAL NOT NULL CHECK(price >= 0),
                note TEXT
            )
            """
        )
        cur.execute("SELECT value FROM meta WHERE key='initial_cash'")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO meta(key,value) VALUES('initial_cash','100000')")
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    conn = _connect_db()
    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS trades")
        cur.execute("DROP TABLE IF EXISTS meta")
        conn.commit()
    finally:
        conn.close()
    init_db()


def get_initial_cash() -> float:
    conn = _connect_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='initial_cash'")
        row = cur.fetchone()
        return float(row[0]) if row else 100000.0
    finally:
        conn.close()


def set_initial_cash(value: float) -> None:
    conn = _connect_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('initial_cash', ?)", (str(float(value)),))
        conn.commit()
    finally:
        conn.close()


def write_trade(ticker: str, side: str, qty: float, price: float, note: Optional[str] = None) -> None:
    conn = _connect_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO trades(ts_utc,ticker,side,qty,price,note) VALUES (?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ticker.upper().strip(),
                side,
                float(qty),
                float(price),
                note,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def read_trades() -> pd.DataFrame:
    conn = _connect_db()
    try:
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY ts_utc ASC, id ASC", conn)
        if df.empty:
            return df
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True, errors="coerce")
        df["ticker"] = df["ticker"].astype(str).str.upper()
        df["side"] = df["side"].astype(str).str.upper()
        df["cash_flow"] = df.apply(
            lambda r: (-float(r["qty"]) * float(r["price"])) if r["side"] == "BUY" else (float(r["qty"]) * float(r["price"])),
            axis=1,
        )
        return df
    finally:
        conn.close()


# =========================================================
# HELPERS
# =========================================================
def safe_ticker(s: str) -> str:
    return str(s).strip().upper().replace(" ", "")


def period_to_days(period: str) -> int:
    return {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "max": 3650,
    }.get(period, 365)


def stooq_symbol(ticker: str) -> str:
    t = ticker.lower()
    if "." not in t:
        t = f"{t}.us"
    return t


def normalize_ohlcv(df: pd.DataFrame, *, prefer_adj_close: bool = True) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        lvl0 = out.columns.get_level_values(0)
        lvl1 = out.columns.get_level_values(1)
        ohlc_fields = {"open", "high", "low", "close", "adj close", "volume"}

        if any(str(x).strip().lower() in ohlc_fields for x in lvl0):
            out.columns = [str(x) for x in lvl0]
        elif any(str(x).strip().lower() in ohlc_fields for x in lvl1):
            out.columns = [str(x) for x in lvl1]
        else:
            out.columns = [" | ".join([str(a), str(b)]) for a, b in out.columns]

    rename_map = {}
    for c in out.columns:
        raw = str(c).strip()
        key = " ".join(raw.lower().replace("_", " ").replace("-", " ").split())
        if key == "open":
            rename_map[c] = "Open"
        elif key == "high":
            rename_map[c] = "High"
        elif key == "low":
            rename_map[c] = "Low"
        elif key == "close":
            rename_map[c] = "Close"
        elif key in ("adj close", "adjusted close", "adjclose"):
            rename_map[c] = "Adj Close"
        elif key == "volume":
            rename_map[c] = "Volume"

    out = out.rename(columns=rename_map)

    if "Close" not in out.columns:
        if prefer_adj_close and "Adj Close" in out.columns:
            out["Close"] = out["Adj Close"]
        else:
            close_like = [c for c in out.columns if "close" in str(c).lower()]
            if close_like:
                out["Close"] = out[close_like[0]]

    if "Close" in out.columns:
        out = out.dropna(subset=["Close"])

    return out


# =========================================================
# MARKET METRICS (pure helpers)
# =========================================================
def pct_change_from(series: pd.Series, periods: int) -> Optional[float]:
    """
    Returns percent change over N rows: (last / value_{-periods-1}) - 1.
    Uses trading bars count (not calendar days). Returns None if insufficient data.
    """
    try:
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) < periods + 1:
            return None
        base = float(s.iloc[-(periods + 1)])
        last = float(s.iloc[-1])
        if abs(base) < 1e-12:
            return None
        return (last / base) - 1.0
    except Exception:
        return None


def compute_52w_sigma_metrics(close: pd.Series, last_price: Optional[float]) -> Dict[str, Optional[float]]:
    """
    Computes 52-week (approx 252 sessions) highs/lows plus sigma-distance metrics.

    Sigma definition used here:
      - sigma_pct_252: std dev of daily pct returns over last ~252 sessions
      - sigma_usd_252: last_price * sigma_pct_252 (approx one-sigma $ move)
    """
    close_s = pd.to_numeric(close, errors="coerce").dropna()
    if close_s.empty:
        return {
            "high_52w": None,
            "low_52w": None,
            "range_pos_52w": None,
            "sigma_pct_252": None,
            "sigma_usd_252": None,
            "pct_from_52w_high": None,
            "pct_from_52w_low": None,
            "sigma_to_52w_high": None,
            "sigma_to_52w_low": None,
        }

    w = close_s.tail(min(252, len(close_s)))
    high_52w = float(w.max())
    low_52w = float(w.min())

    last = float(last_price) if isinstance(last_price, (int, float)) else float(close_s.iloc[-1])

    # Percent distances (as decimals)
    pct_from_high = None if abs(high_52w) < 1e-12 else (last / high_52w) - 1.0
    pct_from_low = None if abs(low_52w) < 1e-12 else (last / low_52w) - 1.0

    # Range position (0..1)
    denom = high_52w - low_52w
    range_pos = None
    if abs(denom) > 1e-12:
        range_pos = (last - low_52w) / denom
        range_pos = float(max(0.0, min(1.0, range_pos)))

    # Volatility (pct) and $-sigma
    rets = w.pct_change().dropna()
    sigma_pct_252 = float(rets.std(ddof=0)) if len(rets) >= 2 else None
    sigma_usd_252 = (last * sigma_pct_252) if isinstance(sigma_pct_252, float) and sigma_pct_252 > 0 else None

    sigma_to_high = ((last - high_52w) / sigma_usd_252) if isinstance(sigma_usd_252, float) and sigma_usd_252 > 0 else None
    sigma_to_low = ((last - low_52w) / sigma_usd_252) if isinstance(sigma_usd_252, float) and sigma_usd_252 > 0 else None

    return {
        "high_52w": high_52w,
        "low_52w": low_52w,
        "range_pos_52w": range_pos,
        "sigma_pct_252": sigma_pct_252,
        "sigma_usd_252": sigma_usd_252,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "sigma_to_52w_high": sigma_to_high,
        "sigma_to_52w_low": sigma_to_low,
    }


def compute_slice_sigma_metrics(
    close: pd.Series,
    start_idx: int,
    end_idx: int,
    current_price: Optional[float] = None,
) -> Dict[str, Optional[float]]:
    """
    Computes sigma metrics for an arbitrary slice of price data.
    
    Args:
        close: Full Close price series (with datetime index ideally)
        start_idx: Start index (inclusive) of the slice
        end_idx: End index (inclusive) of the slice
        current_price: Current/latest price to measure distance from (defaults to last in series)
    
    Returns:
        Dict with: slice_mean, slice_std, slice_high, slice_low, slice_bars,
                   sigma_from_mean, sigma_from_high, sigma_from_low,
                   pct_from_mean, pct_from_high, pct_from_low
    """
    empty_result = {
        "slice_mean": None,
        "slice_std": None,
        "slice_std_pct": None,
        "slice_high": None,
        "slice_low": None,
        "slice_bars": 0,
        "slice_start_date": None,
        "slice_end_date": None,
        "current_price": None,
        "sigma_from_mean": None,
        "sigma_from_high": None,
        "sigma_from_low": None,
        "pct_from_mean": None,
        "pct_from_high": None,
        "pct_from_low": None,
    }
    
    close_s = pd.to_numeric(close, errors="coerce").dropna()
    if close_s.empty:
        return empty_result
    
    # Clamp indices to valid range
    n = len(close_s)
    start_idx = max(0, min(start_idx, n - 1))
    end_idx = max(0, min(end_idx, n - 1))
    
    # Ensure start <= end
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
    
    # Extract slice (inclusive on both ends)
    slice_data = close_s.iloc[start_idx : end_idx + 1]
    
    if len(slice_data) < 2:
        return empty_result
    
    # Basic stats for the slice
    slice_mean = float(slice_data.mean())
    slice_std = float(slice_data.std(ddof=0))
    slice_high = float(slice_data.max())
    slice_low = float(slice_data.min())
    slice_bars = len(slice_data)
    
    # Get dates if index is datetime
    slice_start_date = None
    slice_end_date = None
    try:
        if hasattr(slice_data.index, 'to_pydatetime'):
            slice_start_date = slice_data.index[0]
            slice_end_date = slice_data.index[-1]
    except Exception:
        pass
    
    # Current price (default to last in full series)
    if current_price is None:
        current_price = float(close_s.iloc[-1])
    else:
        current_price = float(current_price)
    
    # Sigma-based distances (using $ std dev)
    sigma_from_mean = None
    sigma_from_high = None
    sigma_from_low = None
    
    if slice_std > 1e-12:
        sigma_from_mean = (current_price - slice_mean) / slice_std
        sigma_from_high = (current_price - slice_high) / slice_std
        sigma_from_low = (current_price - slice_low) / slice_std
    
    # Percentage distances
    pct_from_mean = ((current_price / slice_mean) - 1.0) if abs(slice_mean) > 1e-12 else None
    pct_from_high = ((current_price / slice_high) - 1.0) if abs(slice_high) > 1e-12 else None
    pct_from_low = ((current_price / slice_low) - 1.0) if abs(slice_low) > 1e-12 else None
    
    # Std dev as percentage of mean (volatility proxy)
    slice_std_pct = (slice_std / slice_mean) if abs(slice_mean) > 1e-12 else None
    
    return {
        "slice_mean": slice_mean,
        "slice_std": slice_std,
        "slice_std_pct": slice_std_pct,
        "slice_high": slice_high,
        "slice_low": slice_low,
        "slice_bars": slice_bars,
        "slice_start_date": slice_start_date,
        "slice_end_date": slice_end_date,
        "current_price": current_price,
        "sigma_from_mean": sigma_from_mean,
        "sigma_from_high": sigma_from_high,
        "sigma_from_low": sigma_from_low,
        "pct_from_mean": pct_from_mean,
        "pct_from_high": pct_from_high,
        "pct_from_low": pct_from_low,
    }


def compute_key_levels(df: pd.DataFrame, current_price: Optional[float] = None) -> Dict[str, Optional[float]]:
    """
    Computes traditional key levels from OHLCV data.
    
    Returns: day_high, day_low, week_high, week_low, high_52w, low_52w, 
             volume_last, volume_avg_20
    """
    empty_result = {
        "day_high": None,
        "day_low": None,
        "week_high": None,
        "week_low": None,
        "high_52w": None,
        "low_52w": None,
        "volume_last": None,
        "volume_avg_20": None,
        "current_price": current_price,
    }
    
    if df is None or df.empty:
        return empty_result
    
    result = empty_result.copy()
    
    # Day high/low (most recent bar)
    if "High" in df.columns and "Low" in df.columns:
        try:
            result["day_high"] = float(df["High"].iloc[-1])
            result["day_low"] = float(df["Low"].iloc[-1])
        except Exception:
            pass
    
    # Week high/low (last 5 trading bars)
    if "High" in df.columns and "Low" in df.columns and len(df) >= 1:
        try:
            week_data = df.tail(min(5, len(df)))
            result["week_high"] = float(week_data["High"].max())
            result["week_low"] = float(week_data["Low"].min())
        except Exception:
            pass
    
    # 52-week high/low (last 252 bars or all available)
    if "High" in df.columns and "Low" in df.columns:
        try:
            year_data = df.tail(min(252, len(df)))
            result["high_52w"] = float(year_data["High"].max())
            result["low_52w"] = float(year_data["Low"].min())
        except Exception:
            pass
    
    # Volume
    if "Volume" in df.columns:
        try:
            vol_series = pd.to_numeric(df["Volume"], errors="coerce").dropna()
            if not vol_series.empty:
                result["volume_last"] = float(vol_series.iloc[-1])
                if len(vol_series) >= 20:
                    result["volume_avg_20"] = float(vol_series.tail(20).mean())
        except Exception:
            pass
    
    # Current price
    if current_price is not None:
        result["current_price"] = float(current_price)
    elif "Close" in df.columns:
        try:
            result["current_price"] = float(df["Close"].iloc[-1])
        except Exception:
            pass
    
    return result


def fmt_signed_pct(v: Optional[float]) -> str:
    """Format a percentage with arrow and color emoji indicator."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        x = float(v)
        if x > 0:
            return f"🟢 +{x:.2f}%"
        elif x < 0:
            return f"🔴 {x:.2f}%"
        else:
            return f"⚪ {x:.2f}%"
    except Exception:
        return "—"


def fmt_pnl_delta(v: Optional[float]) -> str:
    """Format P&L value with color indicator."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        x = float(v)
        if x > 0:
            return f"🟢 +${x:,.2f}"
        elif x < 0:
            return f"🔴 -${abs(x):,.2f}"
        return f"${x:,.2f}"
    except Exception:
        return "—"


def fmt_sigma(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):+.2f}σ"
    except Exception:
        return "—"


# =========================================================
# DATA PROVIDERS
# =========================================================

# Intraday data limits (Yahoo Finance):
# 1m: ~7 days, 2m: ~60 days, 5m: ~60 days, 15m: ~60 days, 30m: ~60 days, 1h: ~730 days
INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
INTRADAY_MAX_PERIODS = {
    "1m": "7d",
    "2m": "60d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "60m": "60d",
    "90m": "60d",
    "1h": "730d",
}


def _fetch_yahoo_history(ticker: str, period: str, interval: str, timeout: float = 12.0) -> pd.DataFrame:
    """Core Yahoo history fetch (no caching - called by cached wrappers)."""
    def _core():
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            threads=False,
            auto_adjust=False,
            group_by="column",
        )
        if df is None or len(df) == 0:
            return pd.DataFrame()
        return df

    result = run_with_timeout(_core, timeout_sec=timeout)
    if not isinstance(result, pd.DataFrame) or result.empty:
        return pd.DataFrame()
    return normalize_ohlcv(result)


@st.cache_data(ttl=20, show_spinner=False)
def yahoo_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Fetch daily/weekly history with 20s cache TTL."""
    return _fetch_yahoo_history(ticker, period, interval)


@st.cache_data(ttl=10, show_spinner=False)
def yahoo_history_intraday(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Fetch intraday history with shorter 10s cache TTL."""
    return _fetch_yahoo_history(ticker, period, interval)


@st.cache_data(ttl=2, show_spinner=False)
def yahoo_quote(ticker: str) -> Optional[float]:
    def _core():
        t = yf.Ticker(ticker)
        try:
            fi = getattr(t, "fast_info", None)
            if isinstance(fi, dict):
                v = fi.get("last_price") or fi.get("lastPrice") or fi.get("regular_market_price")
                if v is not None:
                    return float(v)
        except Exception:
            pass

        hist = t.history(period="1d", interval="5m")
        if hist is not None and not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[-1])
        return None

    v = run_with_timeout(_core, timeout_sec=8.0)
    return float(v) if isinstance(v, (float, int)) else None


@st.cache_data(ttl=300, show_spinner=False)
def stooq_history_daily(ticker: str) -> pd.DataFrame:
    def _core():
        sym = stooq_symbol(ticker)
        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        df = pd.read_csv(url)
        if df is None or df.empty:
            return pd.DataFrame()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
        return df

    result = run_with_timeout(_core, timeout_sec=10.0)
    if not isinstance(result, pd.DataFrame) or result.empty:
        return pd.DataFrame()
    return normalize_ohlcv(result)


def get_history(ticker: str, period: str, interval: str, provider_mode: str) -> Tuple[pd.DataFrame, str]:
    ticker = safe_ticker(ticker)
    provider_mode = provider_mode or "Auto"
    is_intraday = interval in INTRADAY_INTERVALS

    if provider_mode in ("Auto", "Yahoo"):
        # Use intraday-specific fetcher for shorter intervals
        if is_intraday:
            # Clamp period to max allowed for this interval
            max_period = INTRADAY_MAX_PERIODS.get(interval, "60d")
            effective_period = period if period_to_days(period) <= period_to_days(max_period) else max_period
            df = yahoo_history_intraday(ticker, period=effective_period, interval=interval)
        else:
            df = yahoo_history(ticker, period=period, interval=interval)
        
        if not df.empty and "Close" in df.columns:
            source = "Yahoo Finance (yfinance)"
            if is_intraday:
                source += f" [intraday {interval}]"
            return df, source

    # Fallback to Stooq (daily only)
    if is_intraday:
        return pd.DataFrame(), "No intraday data (Stooq fallback only supports daily bars)"
    
    df_s = stooq_history_daily(ticker)
    if df_s.empty or "Close" not in df_s.columns:
        return pd.DataFrame(), "No data (provider blocked or symbol invalid)"

    days = period_to_days(period)
    df_s = df_s.tail(max(days, 5))
    return df_s, "Stooq (daily fallback)"


def get_quote(ticker: str, provider_mode: str) -> Tuple[Optional[float], str]:
    ticker = safe_ticker(ticker)
    provider_mode = provider_mode or "Auto"

    if provider_mode in ("Auto", "Yahoo"):
        q = yahoo_quote(ticker)
        if q is not None:
            return q, "Yahoo Finance (yfinance)"

    df_s = stooq_history_daily(ticker)
    if not df_s.empty and "Close" in df_s.columns:
        return float(df_s["Close"].iloc[-1]), "Stooq (daily fallback)"

    return None, "No data"


@st.cache_data(ttl=120, show_spinner=False)
def build_watchlist_metrics(symbols: Tuple[str, ...], provider_mode: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Builds a compact watchlist table with per-symbol fault isolation.
    Returns (df, errors) where errors are human-readable strings.
    """
    rows: List[Dict[str, object]] = []
    errors: List[str] = []

    for sym_raw in symbols:
        sym = safe_ticker(sym_raw)
        if not sym:
            continue

        # Prefer live quote if available (fallback to last close from daily history).
        last_px, last_src = get_quote(sym, provider_mode=provider_mode)

        df_d, hist_src = get_history(sym, period="1y", interval="1d", provider_mode=provider_mode)
        df_d = df_d.copy() if isinstance(df_d, pd.DataFrame) else pd.DataFrame()

        if df_d.empty or "Close" not in df_d.columns:
            errors.append(f"{sym}: no daily Close history returned ({hist_src}).")
            rows.append(
                {
                    "Symbol": sym,
                    "Last": last_px,
                    "1D%": None,
                    "1W%": None,
                    "1M%": None,
                    "Volume": None,
                    "Avg Vol (20D)": None,
                    "52W High": None,
                    "52W Low": None,
                    "% From High": None,
                    "% From Low": None,
                    "σ To High": None,
                    "σ To Low": None,
                    "52W Range Pos": None,
                    "Vol (252D) %": None,
                    "Spark (60D)": [],
                    "Quote Src": last_src,
                    "Hist Src": hist_src,
                }
            )
            continue

        close = pd.to_numeric(df_d["Close"], errors="coerce").dropna()
        if close.empty:
            errors.append(f"{sym}: daily history returned but Close is empty after cleaning ({hist_src}).")
            continue

        # If quote missing, fall back to last daily close
        last_val = float(last_px) if isinstance(last_px, (int, float)) else float(close.iloc[-1])

        # Volume metrics
        volume_col = None
        avg_vol_20 = None
        if "Volume" in df_d.columns:
            vol_series = pd.to_numeric(df_d["Volume"], errors="coerce").dropna()
            if not vol_series.empty:
                volume_col = float(vol_series.iloc[-1])
                if len(vol_series) >= 20:
                    avg_vol_20 = float(vol_series.tail(20).mean())

        m = compute_52w_sigma_metrics(close, last_price=last_val)

        rows.append(
            {
                "Symbol": sym,
                "Last": last_val,
                "1D%": (pct_change_from(close, 1) * 100.0) if pct_change_from(close, 1) is not None else None,
                "1W%": (pct_change_from(close, 5) * 100.0) if pct_change_from(close, 5) is not None else None,
                "1M%": (pct_change_from(close, 21) * 100.0) if pct_change_from(close, 21) is not None else None,
                "Volume": volume_col,
                "Avg Vol (20D)": avg_vol_20,
                "52W High": m["high_52w"],
                "52W Low": m["low_52w"],
                "% From High": (m["pct_from_52w_high"] * 100.0) if m["pct_from_52w_high"] is not None else None,
                "% From Low": (m["pct_from_52w_low"] * 100.0) if m["pct_from_52w_low"] is not None else None,
                "σ To High": m["sigma_to_52w_high"],
                "σ To Low": m["sigma_to_52w_low"],
                "52W Range Pos": m["range_pos_52w"],
                "Vol (252D) %": (m["sigma_pct_252"] * 100.0) if m["sigma_pct_252"] is not None else None,
                "Spark (60D)": [float(x) for x in close.tail(60).tolist()],
                "Quote Src": last_src,
                "Hist Src": hist_src,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df, errors

    # Stable ordering: watchlist order
    order = {safe_ticker(s): i for i, s in enumerate(symbols)}
    df["_ord"] = df["Symbol"].map(lambda s: order.get(str(s), 10_000))
    df = df.sort_values(["_ord", "Symbol"]).drop(columns=["_ord"]).reset_index(drop=True)
    return df, errors


# =========================================================
# PORTFOLIO MATH
# =========================================================
def compute_positions(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["ticker", "qty", "avg_cost"])

    positions = []
    for ticker, g in trades.groupby("ticker"):
        qty = 0.0
        cost = 0.0
        for _, r in g.iterrows():
            q = float(r["qty"])
            p = float(r["price"])
            if r["side"] == "BUY":
                qty += q
                cost += q * p
            else:
                sell_qty = q
                if qty <= 0:
                    qty -= sell_qty
                else:
                    avg = cost / qty if qty else 0.0
                    qty -= sell_qty
                    cost -= sell_qty * avg

        avg_cost = (cost / qty) if abs(qty) > 1e-12 else 0.0
        positions.append({"ticker": ticker, "qty": qty, "avg_cost": avg_cost})

    return pd.DataFrame(positions).sort_values("ticker").reset_index(drop=True)


def cash_from_trades(trades: pd.DataFrame, initial_cash: float) -> float:
    if trades.empty:
        return float(initial_cash)
    return float(initial_cash + trades["cash_flow"].sum())


# =========================================================
# PORTFOLIO ANALYTICS (cached)
# =========================================================
def days_to_period(days: int) -> str:
    if days <= 5:
        return "5d"
    if days <= 30:
        return "1mo"
    if days <= 180:
        return "6mo"
    if days <= 365:
        return "1y"
    if days <= 730:
        return "2y"
    if days <= 1825:
        return "5y"
    return "10y"


@st.cache_data(ttl=120, show_spinner=False)
def build_portfolio_analytics_timeseries(
    trades_key: Tuple[Tuple[str, str, str, str, str], ...],
    initial_cash: float,
    provider_mode: str,
    benchmark_symbol: str = "SPY",
) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Reconstructs an approximate daily equity curve from trades + daily closes.
    - Uses end-of-day positions (cumulative qty by trade date).
    - Prices are daily Close, forward-filled across the union of trading days.
    Returns (df, errors, source_label).
    """
    errors: List[str] = []

    if not trades_key:
        return pd.DataFrame(), errors, "No trades"

    trades = pd.DataFrame(list(trades_key), columns=["ts_utc", "ticker", "side", "qty", "price"])
    trades["ts_utc"] = pd.to_datetime(trades["ts_utc"], utc=True, errors="coerce")
    trades["ticker"] = trades["ticker"].astype(str).str.upper()
    trades["side"] = trades["side"].astype(str).str.upper()
    trades["qty"] = pd.to_numeric(trades["qty"], errors="coerce")
    trades["price"] = pd.to_numeric(trades["price"], errors="coerce")
    trades = trades.dropna(subset=["ts_utc", "ticker", "side", "qty", "price"])
    if trades.empty:
        return pd.DataFrame(), errors, "No usable trades"

    trades["date"] = trades["ts_utc"].dt.date
    trades["signed_qty"] = trades.apply(lambda r: float(r["qty"]) if r["side"] == "BUY" else -float(r["qty"]), axis=1)
    trades["cash_flow"] = trades.apply(
        lambda r: (-float(r["qty"]) * float(r["price"])) if r["side"] == "BUY" else (float(r["qty"]) * float(r["price"])),
        axis=1,
    )

    start_date = pd.to_datetime(min(trades["date"])).tz_localize(None)
    now_date = pd.Timestamp.utcnow().tz_localize(None).normalize()
    days = int(max(5, (now_date - start_date).days + 1))
    period = days_to_period(days)

    symbols = sorted(set(trades["ticker"].astype(str).tolist()))
    bench = safe_ticker(benchmark_symbol) or "SPY"
    if bench not in symbols:
        symbols_plus = symbols + [bench]
    else:
        symbols_plus = symbols

    # Pull daily close history per symbol (fault isolated)
    price_series: Dict[str, pd.Series] = {}
    used_sources: List[str] = []
    for sym in symbols_plus:
        df_h, src = get_history(sym, period=period, interval="1d", provider_mode=provider_mode)
        used_sources.append(src)
        if df_h.empty or "Close" not in df_h.columns:
            errors.append(f"{sym}: missing daily Close history ({src}).")
            continue
        s = pd.to_numeric(df_h["Close"], errors="coerce").dropna()
        if s.empty:
            errors.append(f"{sym}: Close is empty after cleaning ({src}).")
            continue
        s.index = pd.to_datetime(s.index).tz_localize(None)
        price_series[sym] = s

    if not price_series:
        return pd.DataFrame(), errors, "No price history"

    # Align to union of trading days and forward-fill
    idx = sorted(set().union(*[set(s.index) for s in price_series.values()]))
    idx = pd.DatetimeIndex(idx).sort_values()
    prices = pd.DataFrame({sym: s.reindex(idx).ffill() for sym, s in price_series.items()}, index=idx)

    # Build daily quantities (end-of-day) per symbol
    qty = pd.DataFrame(index=idx)
    for sym in symbols:
        g = trades[trades["ticker"] == sym].groupby("date")["signed_qty"].sum()
        q = pd.Series(g, dtype="float64")
        q.index = pd.to_datetime(q.index)
        qty[sym] = q.reindex(idx).fillna(0.0).cumsum()

    # Daily cash
    cf = trades.groupby("date")["cash_flow"].sum()
    cash = pd.Series(cf, dtype="float64")
    cash.index = pd.to_datetime(cash.index)
    cash = cash.reindex(idx).fillna(0.0).cumsum() + float(initial_cash)

    holdings_value = (qty * prices.reindex(columns=qty.columns, fill_value=pd.NA)).sum(axis=1).fillna(0.0)
    equity = cash + holdings_value

    out = pd.DataFrame(
        {
            "Cash": cash,
            "Holdings": holdings_value,
            "Equity": equity,
        },
        index=idx,
    ).dropna(subset=["Equity"])

    # Benchmark (buy-and-hold from first available day)
    if bench in prices.columns and not prices[bench].dropna().empty:
        b = prices[bench].dropna()
        b0 = float(b.iloc[0])
        out["Benchmark"] = (b / b0) * float(initial_cash) if abs(b0) > 1e-12 else pd.NA
    else:
        out["Benchmark"] = pd.NA

    out["Drawdown"] = (out["Equity"] / out["Equity"].cummax()) - 1.0

    # Choose a short source label for display
    src_label = " / ".join(sorted(set(used_sources))) if used_sources else "Unknown"
    return out, errors, src_label


# =========================================================
# LIVE / HUD
# =========================================================
def ensure_live_defaults():
    if "live_playing" not in st.session_state:
        st.session_state["live_playing"] = False  # Default to paused for stability
    if "live_interval_ms" not in st.session_state:
        st.session_state["live_interval_ms"] = 3000  # 3s reduces flicker perception


def render_chart_block(fig: Optional[go.Figure], key_prefix: str):
    """
    Renders a Plotly chart inside a styled block.
    Live refresh is controlled from User Settings page.
    """
    ensure_live_defaults()
    playing = bool(st.session_state["live_playing"])

    if playing:
        st_autorefresh(interval=st.session_state["live_interval_ms"], key=f"{key_prefix}_autorefresh")

    # Block open
    st.markdown('<div class="chart-block">', unsafe_allow_html=True)

    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)  # chart-block


# =========================================================
# APP START
# =========================================================
init_db()

if "theme" not in st.session_state:
    st.session_state["theme"] = "Neon (Dark)"
if "provider_mode" not in st.session_state:
    st.session_state["provider_mode"] = "Auto"
if "show_diagnostics" not in st.session_state:
    st.session_state["show_diagnostics"] = False

ensure_live_defaults()
inject_css(st.session_state["theme"])

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]
if "selected_symbol" not in st.session_state:
    st.session_state["selected_symbol"] = "AAPL"
if "watch_quotes" not in st.session_state:
    st.session_state["watch_quotes"] = {}

# Sidebar
with st.sidebar:
    st.header("Tradeview")

    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📊 Markets", "🧾 Order Entry", "💼 Portfolio", "🧱 Activity", "⚙️ User Settings"],
        index=0,
    )

    st.divider()
    st.caption(f"Theme: {st.session_state['theme']}  •  Data: {st.session_state['provider_mode']}")

    st.divider()
    st.subheader("Watchlist")
    wl_text = st.text_input("Symbols (comma-separated)", value=", ".join(st.session_state["watchlist"]))
    st.session_state["watchlist"] = [safe_ticker(x) for x in wl_text.split(",") if safe_ticker(x)][:15] or ["AAPL"]

    c1, c2 = st.columns(2)
    with c1:
        refresh_quotes = st.button("Refresh quotes")
    with c2:
        clear_cache = st.button("Clear cache")

    if clear_cache:
        st.cache_data.clear()
        st.session_state["watch_quotes"] = {}

    if refresh_quotes:
        quotes: Dict[str, Optional[float]] = {}
        for sym in st.session_state["watchlist"][:8]:
            q, _src = get_quote(sym, provider_mode=st.session_state["provider_mode"])
            quotes[sym] = q
        st.session_state["watch_quotes"] = quotes

    for sym in st.session_state["watchlist"][:8]:
        px = st.session_state["watch_quotes"].get(sym)
        st.caption(f"{sym}: {'—' if px is None else f'${px:,.2f}'}")
        if st.button(f"Use {sym}", key=f"use_{sym}"):
            st.session_state["selected_symbol"] = sym
            st.rerun()

# Header (clean: removed build pill)
st.markdown(
    f"""
    <div class="hero">
        <h1>📈 {APP_NAME}</h1>
        <div class="tagline">{APP_TAGLINE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="small-muted">Quotes are indicative and may be delayed. Paper trading only. Not investment advice.</div>',
    unsafe_allow_html=True,
)

plotly_template = st.session_state.get("plotly_template", "plotly_dark")
provider_mode = st.session_state["provider_mode"]
show_diagnostics = st.session_state["show_diagnostics"]

# KPIs
trades_df = read_trades()
initial_cash = get_initial_cash()
cash = cash_from_trades(trades_df, initial_cash)
positions_df = compute_positions(trades_df)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Cash", f"${cash:,.2f}")
k2.metric("Open Positions", f"{positions_df.shape[0]}")
k3.metric("Trades Logged", f"{len(trades_df)}")
k4.metric("Data Provider", provider_mode)


# =========================================================
# PAGES
# =========================================================
def build_price_figure(df: pd.DataFrame, *, chart_type: str, template: str, height: int) -> go.Figure:
    fig = go.Figure()
    if chart_type == "Candles" and all(x in df.columns for x in ["Open", "High", "Low", "Close"]):
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Price",
            )
        )
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Price"))

    # Cleanups: kill "undefined" + kill range slider + kill title band
    # Use empty string "" instead of None to prevent "undefined" text rendering
    fig.update_layout(
        template=template,
        height=height,
        title="",
        showlegend=False,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_xaxes(rangeslider_visible=False, title_text="")
    fig.update_yaxes(title_text="")
    fig.update_layout(xaxis_rangeslider_visible=False)
    
    return fig


if page == "🏠 Dashboard":
    st.subheader("Overview")

    sym_input = st.text_input("Primary Symbol", value=st.session_state.get("selected_symbol", "AAPL"), key="dash_symbol")
    sym = safe_ticker(sym_input) or "AAPL"
    st.session_state["selected_symbol"] = sym

    q_now, _q_src = get_quote(sym, provider_mode=provider_mode)
    q_txt = "—" if q_now is None else f"${q_now:,.2f}"
    st.markdown(
        f"""
        <div class="symbol-banner">
            <div class="label">Primary Symbol</div>
            <div class="value">{sym}</div>
            <div class="sub">Indicative quote: <b>{q_txt}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_slot = st.empty()
    toolbar_slot = st.empty()

    with toolbar_slot.container():
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.0, 1.8])
        with c1:
            period = st.selectbox("🗓️ Window", ["5d", "1mo", "6mo", "1y", "5y"], index=1, key="dash_period")
        with c2:
            interval = st.selectbox("⏱️ Granularity", ["1d", "1h", "15m", "5m"], index=0, key="dash_interval")
        with c3:
            chart_type = st.selectbox("📈 Chart", ["Line", "Candles"], index=0, key="dash_chart_type")
        with c4:
            source_ph = st.empty()

        diag_ph = st.empty()
        st.markdown("</div>", unsafe_allow_html=True)

    df, src = get_history(sym, period=period, interval=interval, provider_mode=provider_mode)
    source_ph.caption(f"Source: {src}")

    if df.empty or "Close" not in df.columns:
        with chart_slot.container():
            st.error("No usable price data returned (missing Close or empty).")
        if show_diagnostics and not df.empty:
            diag_ph.write("Columns received:")
            diag_ph.write(list(df.columns))
            diag_ph.dataframe(df.tail(5), use_container_width=True)
        slice_metrics = None
        key_levels = None
    else:
        df = df.copy()
        fig = build_price_figure(df, chart_type=chart_type, template=plotly_template, height=520)
        with chart_slot.container():
            render_chart_block(fig, "dashboard")
        
        # Compute metrics for the ENTIRE visible window (no slider needed)
        close_series = df["Close"]
        slice_metrics = compute_slice_sigma_metrics(close_series, 0, len(df) - 1, current_price=q_now)
        key_levels = compute_key_levels(df, current_price=q_now)

    # =============================================
    # WINDOW STATISTICS (tied to visible chart period)
    # =============================================
    st.divider()
    
    if not df.empty and "Close" in df.columns and slice_metrics:
        # Get date range for display
        start_date_str = ""
        end_date_str = ""
        try:
            if hasattr(df.index[0], 'strftime'):
                start_date_str = df.index[0].strftime('%Y-%m-%d')
                end_date_str = df.index[-1].strftime('%Y-%m-%d')
        except Exception:
            pass
        
        period_label = f"{period.upper()}" if period else "Selected"
        st.markdown(f"### 📐 {period_label} Window Statistics")
        if start_date_str and end_date_str:
            st.caption(f"Analysis period: {start_date_str} → {end_date_str} ({len(df)} bars)")
        else:
            st.caption(f"Analysis period: {len(df)} bars")
        
        # Compact 4-column layout for stats
        stat_cols = st.columns(4)
        
        with stat_cols[0]:
            mean_val = slice_metrics.get("slice_mean")
            if mean_val is not None:
                st.metric("Mean Price", f"${mean_val:,.2f}")
        
        with stat_cols[1]:
            std_val = slice_metrics.get("slice_std")
            std_pct = slice_metrics.get("slice_std_pct")
            if std_val is not None:
                delta_str = f"{std_pct*100:.1f}% of mean" if std_pct else None
                st.metric("Std Dev (σ)", f"${std_val:,.2f}", delta=delta_str)
        
        with stat_cols[2]:
            high_val = slice_metrics.get("slice_high")
            low_val = slice_metrics.get("slice_low")
            if high_val is not None and low_val is not None:
                st.metric("Range", f"${low_val:,.2f} — ${high_val:,.2f}")
        
        with stat_cols[3]:
            sig_mean = slice_metrics.get("sigma_from_mean")
            if sig_mean is not None:
                color = "🟢" if sig_mean > 0 else ("🔴" if sig_mean < 0 else "⚪")
                st.metric("Current vs Mean", f"{color} {sig_mean:+.2f}σ")
        
        # Additional sigma info in a subtle row
        sig_high = slice_metrics.get("sigma_from_high")
        sig_low = slice_metrics.get("sigma_from_low")
        if sig_high is not None and sig_low is not None:
            st.caption(f"σ from period high: {sig_high:+.2f}σ  •  σ from period low: {sig_low:+.2f}σ")

    # Key Levels (collapsible)
    with st.expander("📊 Key Levels", expanded=False):
        if not df.empty and key_levels:
            kl_cols = st.columns(4)
            with kl_cols[0]:
                st.markdown("**Day**")
                dh = key_levels.get("day_high")
                dl = key_levels.get("day_low")
                if dh is not None:
                    st.caption(f"High: ${dh:,.2f}")
                if dl is not None:
                    st.caption(f"Low: ${dl:,.2f}")
            with kl_cols[1]:
                st.markdown("**Week (5 bars)**")
                wh = key_levels.get("week_high")
                wl_val = key_levels.get("week_low")
                if wh is not None:
                    st.caption(f"High: ${wh:,.2f}")
                if wl_val is not None:
                    st.caption(f"Low: ${wl_val:,.2f}")
            with kl_cols[2]:
                st.markdown("**52-Week**")
                h52 = key_levels.get("high_52w")
                l52 = key_levels.get("low_52w")
                if h52 is not None:
                    st.caption(f"High: ${h52:,.2f}")
                if l52 is not None:
                    st.caption(f"Low: ${l52:,.2f}")
            with kl_cols[3]:
                st.markdown("**Volume**")
                vol_last = key_levels.get("volume_last")
                vol_avg = key_levels.get("volume_avg_20")
                if vol_last is not None:
                    st.caption(f"Last: {vol_last:,.0f}")
                if vol_avg is not None:
                    st.caption(f"Avg (20): {vol_avg:,.0f}")
        else:
            st.info("No data available for key levels.")

    st.divider()
    st.markdown("### Watchlist snapshot")
    wl = [safe_ticker(x) for x in st.session_state.get("watchlist", []) if safe_ticker(x)]
    if not wl:
        st.info("Your watchlist is empty. Add symbols in the sidebar.")
    else:
        dfw, errs = build_watchlist_metrics(tuple(wl[:8]), provider_mode=provider_mode)
        if dfw.empty:
            st.warning("No watchlist metrics available right now.")
        else:
            view = dfw.copy()
            view["1D"] = view["1D%"].apply(fmt_signed_pct)
            view["1W"] = view["1W%"].apply(fmt_signed_pct)
            view["1M"] = view["1M%"].apply(fmt_signed_pct)
            view["σ→High"] = view["σ To High"].apply(fmt_sigma)
            view["σ→Low"] = view["σ To Low"].apply(fmt_sigma)
            view = view[
                ["Symbol", "Last", "1D", "1W", "1M", "% From High", "% From Low", "σ→High", "σ→Low", "52W Range Pos", "Spark (60D)"]
            ].copy()

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Last": st.column_config.NumberColumn(format="$%.2f"),
                    "% From High": st.column_config.NumberColumn(format="%.2f%%"),
                    "% From Low": st.column_config.NumberColumn(format="%.2f%%"),
                    "52W Range Pos": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0),
                    "Spark (60D)": st.column_config.LineChartColumn(),
                },
            )

        if errs and show_diagnostics:
            with st.expander(f"Watchlist diagnostics ({len(errs)})", expanded=False):
                for e in errs[:50]:
                    st.write(f"- {e}")
                if len(errs) > 50:
                    st.caption(f"(Showing 50 of {len(errs)}.)")


elif page == "📊 Markets":
    st.subheader("Markets")

    ticker_input = st.text_input("Symbol", value=st.session_state.get("selected_symbol", "AAPL"), key="mkt_symbol")
    ticker = safe_ticker(ticker_input) or "AAPL"
    st.session_state["selected_symbol"] = ticker

    q_now, _qsrc = get_quote(ticker, provider_mode=provider_mode)
    q_txt = "—" if q_now is None else f"${q_now:,.2f}"
    st.markdown(
        f"""
        <div class="symbol-banner">
            <div class="label">Active Symbol</div>
            <div class="value">{ticker}</div>
            <div class="sub">Indicative quote: <b>{q_txt}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_slot = st.empty()
    toolbar_slot = st.empty()

    with toolbar_slot.container():
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)

        r1c1, r1c2, r1c3, r1c4 = st.columns([1.1, 1.1, 1.0, 1.8])
        with r1c1:
            period = st.selectbox("🗓️ Window", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=2, key="mkt_period")
        with r1c2:
            interval = st.selectbox("⏱️ Granularity", ["1m", "5m", "15m", "1h", "1d"], index=3, key="mkt_interval")
        with r1c3:
            chart_type = st.selectbox("📈 Chart", ["Line", "Candles"], index=0, key="mkt_chart_type")
        with r1c4:
            source_ph = st.empty()

        with st.expander("Indicators", expanded=False):
            i1, i2, i3 = st.columns(3)
            with i1:
                show_sma_20 = st.checkbox("SMA 20", value=True, key="mkt_sma20")
            with i2:
                show_sma_50 = st.checkbox("SMA 50", value=True, key="mkt_sma50")
            with i3:
                show_volume = st.checkbox("Volume", value=False, key="mkt_vol")

        # Intraday data limit warning
        is_intraday = interval in INTRADAY_INTERVALS
        if is_intraday:
            max_period = INTRADAY_MAX_PERIODS.get(interval, "60d")
            st.caption(f"⚠️ Intraday data ({interval}) limited to ~{max_period} of history.")

        diag_ph = st.empty()
        st.markdown("</div>", unsafe_allow_html=True)

    df, src = get_history(ticker, period=period, interval=interval, provider_mode=provider_mode)
    source_ph.caption(f"Source: {src}")

    if df.empty or "Close" not in df.columns:
        with chart_slot.container():
            st.error("No usable price data returned (missing Close or empty).")
        if show_diagnostics and not df.empty:
            diag_ph.write("Columns received:")
            diag_ph.write(list(df.columns))
            diag_ph.dataframe(df.tail(5), use_container_width=True)
        # Initialize empty slice metrics for the UI below
        slice_metrics = None
        key_levels = None
    else:
        df = df.copy()
        if show_sma_20:
            df["SMA_20"] = df["Close"].rolling(window=20).mean()
        if show_sma_50:
            df["SMA_50"] = df["Close"].rolling(window=50).mean()

        fig = build_price_figure(df, chart_type=chart_type, template=plotly_template, height=640)

        if show_sma_20 and "SMA_20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], mode="lines", name="SMA 20", opacity=0.7))
        if show_sma_50 and "SMA_50" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], mode="lines", name="SMA 50", opacity=0.7))
        if show_volume and "Volume" in df.columns and chart_type != "Candles":
            fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", opacity=0.30))

        fig.update_layout(showlegend=False)
        fig.update_xaxes(rangeslider_visible=False)
        fig.update_layout(xaxis_rangeslider_visible=False)

        with chart_slot.container():
            render_chart_block(fig, "markets")
        
        # Compute metrics for the ENTIRE visible window
        close_series = df["Close"]
        slice_metrics = compute_slice_sigma_metrics(close_series, 0, len(df) - 1, current_price=q_now)
        key_levels = compute_key_levels(df, current_price=q_now)

    # =============================================
    # WINDOW STATISTICS (tied to visible chart period)
    # =============================================
    st.divider()
    
    if not df.empty and "Close" in df.columns and slice_metrics:
        # Get date range for display
        start_date_str = ""
        end_date_str = ""
        try:
            if hasattr(df.index[0], 'strftime'):
                start_date_str = df.index[0].strftime('%Y-%m-%d')
                end_date_str = df.index[-1].strftime('%Y-%m-%d')
        except Exception:
            pass
        
        period_label = f"{period.upper()}" if period else "Selected"
        st.markdown(f"### 📐 {period_label} Window Statistics")
        if start_date_str and end_date_str:
            st.caption(f"Analysis period: {start_date_str} → {end_date_str} ({len(df)} bars)")
        else:
            st.caption(f"Analysis period: {len(df)} bars")
        
        # Compact 4-column layout for stats
        stat_cols = st.columns(4)
        
        with stat_cols[0]:
            mean_val = slice_metrics.get("slice_mean")
            if mean_val is not None:
                st.metric("Mean Price", f"${mean_val:,.2f}")
        
        with stat_cols[1]:
            std_val = slice_metrics.get("slice_std")
            std_pct = slice_metrics.get("slice_std_pct")
            if std_val is not None:
                delta_str = f"{std_pct*100:.1f}% of mean" if std_pct else None
                st.metric("Std Dev (σ)", f"${std_val:,.2f}", delta=delta_str)
        
        with stat_cols[2]:
            high_val = slice_metrics.get("slice_high")
            low_val = slice_metrics.get("slice_low")
            if high_val is not None and low_val is not None:
                st.metric("Range", f"${low_val:,.2f} — ${high_val:,.2f}")
        
        with stat_cols[3]:
            sig_mean = slice_metrics.get("sigma_from_mean")
            if sig_mean is not None:
                color = "🟢" if sig_mean > 0 else ("🔴" if sig_mean < 0 else "⚪")
                st.metric("Current vs Mean", f"{color} {sig_mean:+.2f}σ")
        
        # Additional sigma info in a subtle row
        sig_high = slice_metrics.get("sigma_from_high")
        sig_low = slice_metrics.get("sigma_from_low")
        if sig_high is not None and sig_low is not None:
            st.caption(f"σ from period high: {sig_high:+.2f}σ  •  σ from period low: {sig_low:+.2f}σ")

    # =============================================
    # KEY LEVELS PANEL
    # =============================================
    with st.expander("📊 Key Levels", expanded=False):
        if not df.empty and key_levels:
            kl_cols = st.columns(4)
            
            with kl_cols[0]:
                st.markdown("**Day**")
                dh = key_levels.get("day_high")
                dl = key_levels.get("day_low")
                if dh is not None:
                    st.caption(f"High: ${dh:,.2f}")
                if dl is not None:
                    st.caption(f"Low: ${dl:,.2f}")
            
            with kl_cols[1]:
                st.markdown("**Week (5 bars)**")
                wh = key_levels.get("week_high")
                wl_val = key_levels.get("week_low")
                if wh is not None:
                    st.caption(f"High: ${wh:,.2f}")
                if wl_val is not None:
                    st.caption(f"Low: ${wl_val:,.2f}")
            
            with kl_cols[2]:
                st.markdown("**52-Week**")
                h52 = key_levels.get("high_52w")
                l52 = key_levels.get("low_52w")
                if h52 is not None:
                    st.caption(f"High: ${h52:,.2f}")
                if l52 is not None:
                    st.caption(f"Low: ${l52:,.2f}")
            
            with kl_cols[3]:
                st.markdown("**Volume**")
                vol_last = key_levels.get("volume_last")
                vol_avg = key_levels.get("volume_avg_20")
                if vol_last is not None:
                    st.caption(f"Last: {vol_last:,.0f}")
                if vol_avg is not None:
                    st.caption(f"Avg (20): {vol_avg:,.0f}")
        else:
            st.info("No data available for key levels.")

    st.divider()
    st.markdown("### Watchlist snapshot")
    st.caption("Includes 52-week range + volatility metrics (fault-isolated per symbol).")

    wl = [safe_ticker(x) for x in st.session_state.get("watchlist", []) if safe_ticker(x)]
    if not wl:
        st.info("Your watchlist is empty. Add symbols in the sidebar.")
    else:
        top_row = st.columns([1.0, 1.0, 1.2, 1.8, 1.2])
        with top_row[0]:
            max_rows = st.number_input("Max rows", min_value=1, max_value=15, value=min(10, len(wl)), step=1)
        with top_row[1]:
            view_mode = st.selectbox("View", ["Compact", "Detailed"], index=0)
        with top_row[2]:
            show_sources = st.checkbox("Show sources", value=False, help="Show quote/history provider per row.")
        with top_row[3]:
            quick_pick = st.selectbox("Quick pick", options=wl, index=wl.index(ticker) if ticker in wl else 0)
        with top_row[4]:
            st.write("")
            if st.button("Load symbol", use_container_width=True):
                st.session_state["selected_symbol"] = quick_pick
                st.rerun()

        wl_use = tuple(wl[: int(max_rows)])
        dfw, errs = build_watchlist_metrics(wl_use, provider_mode=provider_mode)

        if dfw.empty:
            st.warning("No watchlist metrics available right now (provider blocked or symbols invalid).")
        else:
            view = dfw.copy()
            view["1D"] = view["1D%"].apply(fmt_signed_pct)
            view["1W"] = view["1W%"].apply(fmt_signed_pct)
            view["1M"] = view["1M%"].apply(fmt_signed_pct)
            view["σ→High"] = view["σ To High"].apply(fmt_sigma)
            view["σ→Low"] = view["σ To Low"].apply(fmt_sigma)

            cols_default = (
                [
                    "Symbol",
                    "Last",
                    "1D",
                    "1W",
                    "1M",
                    "Volume",
                    "% From High",
                    "% From Low",
                    "52W Range Pos",
                    "Spark (60D)",
                ]
                if view_mode == "Compact"
                else [
                    "Symbol",
                    "Last",
                    "1D%",
                    "1W%",
                    "1M%",
                    "Volume",
                    "Avg Vol (20D)",
                    "52W High",
                    "52W Low",
                    "% From High",
                    "% From Low",
                    "σ To High",
                    "σ To Low",
                    "52W Range Pos",
                    "Vol (252D) %",
                    "Spark (60D)",
                ]
            )
            cols_sources = ["Quote Src", "Hist Src"]
            view_cols = cols_default + (cols_sources if show_sources or show_diagnostics else [])
            view_cols = [c for c in view_cols if c in view.columns]
            view = view[view_cols].copy()

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Last": st.column_config.NumberColumn(format="$%.2f"),
                    "1D%": st.column_config.NumberColumn(format="%.2f%%"),
                    "1W%": st.column_config.NumberColumn(format="%.2f%%"),
                    "1M%": st.column_config.NumberColumn(format="%.2f%%"),
                    "1D": st.column_config.TextColumn(),
                    "1W": st.column_config.TextColumn(),
                    "1M": st.column_config.TextColumn(),
                    "52W High": st.column_config.NumberColumn(format="$%.2f"),
                    "52W Low": st.column_config.NumberColumn(format="$%.2f"),
                    "% From High": st.column_config.NumberColumn(
                        format="%.2f%%",
                        help="(Last / 52W High) - 1",
                    ),
                    "% From Low": st.column_config.NumberColumn(
                        format="%.2f%%",
                        help="(Last / 52W Low) - 1",
                    ),
                    "σ→High": st.column_config.TextColumn(help="(Last - 52W High) / σ_usd_252"),
                    "σ→Low": st.column_config.TextColumn(help="(Last - 52W Low) / σ_usd_252"),
                    "σ To High": st.column_config.NumberColumn(
                        format="%.2f",
                        help="(Last - 52W High) / σ_usd_252; σ_usd_252 = Last * stdev(daily pct returns, 252D).",
                    ),
                    "σ To Low": st.column_config.NumberColumn(
                        format="%.2f",
                        help="(Last - 52W Low) / σ_usd_252; σ_usd_252 = Last * stdev(daily pct returns, 252D).",
                    ),
                    "52W Range Pos": st.column_config.ProgressColumn(
                        min_value=0.0,
                        max_value=1.0,
                        help="(Last - 52W Low) / (52W High - 52W Low), clipped to 0..1",
                    ),
                    "Volume": st.column_config.NumberColumn(
                        format="%,.0f",
                        help="Most recent daily trading volume.",
                    ),
                    "Avg Vol (20D)": st.column_config.NumberColumn(
                        format="%,.0f",
                        help="20-day average trading volume.",
                    ),
                    "Vol (252D) %": st.column_config.NumberColumn(
                        format="%.2f%%",
                        help="Std dev of daily pct returns over ~252 sessions.",
                    ),
                    "Spark (60D)": st.column_config.LineChartColumn(
                        help="Last ~60 daily closes (for quick trend context).",
                    ),
                },
            )

        if errs:
            with st.expander(f"Watchlist notes ({len(errs)})", expanded=False):
                for e in errs[:50]:
                    st.write(f"- {e}")
                if len(errs) > 50:
                    st.caption(f"(Showing 50 of {len(errs)}.)")

elif page == "🧾 Order Entry":
    st.subheader("Order Entry")

    left, right = st.columns([2, 1])
    with left:
        ticker = safe_ticker(st.text_input("Symbol", value=st.session_state.get("selected_symbol", "AAPL")))
        side = st.selectbox("Side", ["BUY", "SELL"])
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
        order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"], index=0)

        limit_price = None
        if order_type == "LIMIT":
            limit_price = st.number_input("Limit Price", min_value=0.0, value=0.0, step=0.01)

        note = st.text_input("Note (optional)", value="")
        place = st.button("Execute (Paper)")

    with right:
        st.subheader("Indicative Quote")
        px, qsrc = get_quote(ticker, provider_mode=provider_mode) if ticker else (None, "No data")
        if px is None:
            st.warning("Quote unavailable right now.")
        else:
            st.metric("Last", f"${px:,.2f}")
            if show_diagnostics:
                st.caption(f"Source: {qsrc}")

    if place:
        if not ticker:
            st.error("Enter a symbol.")
        elif qty <= 0:
            st.error("Quantity must be greater than zero.")
        else:
            px, _qsrc = get_quote(ticker, provider_mode=provider_mode)
            if px is None:
                st.error("Unable to retrieve a quote. Try switching Market Data to Stooq in User Settings.")
            else:
                filled = True
                fill_price = float(px)

                if order_type == "LIMIT":
                    if limit_price is None or float(limit_price) <= 0:
                        st.error("Enter a valid limit price.")
                        filled = False
                    else:
                        lp = float(limit_price)
                        if side == "BUY" and fill_price > lp:
                            filled = False
                        if side == "SELL" and fill_price < lp:
                            filled = False
                        fill_price = lp

                if not filled:
                    st.info("Limit order is not marketable at the current indicative quote.")
                else:
                    trades = read_trades()
                    cash_now = cash_from_trades(trades, initial_cash)
                    est_value = float(qty) * float(fill_price)

                    if side == "BUY" and est_value > cash_now + 1e-9:
                        st.error(f"Insufficient cash. Need ${est_value:,.2f}, have ${cash_now:,.2f}.")
                    else:
                        write_trade(ticker=ticker, side=side, qty=float(qty), price=float(fill_price), note=note.strip() or None)
                        st.success(f"Executed (Paper): {side} {qty:g} {ticker} @ ${fill_price:,.2f}")
                        st.cache_data.clear()
                        st.rerun()


elif page == "💼 Portfolio":
    st.subheader("Portfolio")

    trades = read_trades()
    positions = compute_positions(trades)

    if positions.empty:
        st.info("No holdings yet. Place a paper order to create positions.")
    else:
        rows = []
        holdings_value = 0.0
        # Quote pulls can be slow; keep per-symbol failures isolated and avoid misleading 0.0 prices.
        for _, r in positions.iterrows():
            sym = str(r["ticker"])
            q = float(r["qty"])
            avg = float(r["avg_cost"])
            last, _src = get_quote(sym, provider_mode=provider_mode)
            last_val = float(last) if last is not None else None
            mv = (q * last_val) if last_val is not None else None
            upnl = ((last_val - avg) * q) if last_val is not None else None
            holdings_value += float(mv) if mv is not None else 0.0

            rows.append(
                {
                    "Symbol": sym,
                    "Quantity": q,
                    "Avg Cost": avg,
                    "Last": last_val,
                    "Market Value": mv,
                    "Unrealized P&L": upnl,
                }
            )

        dfp = pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)
        total_value = float(cash + holdings_value)
        pnl = float(total_value - initial_cash)

        m1, m2, m3 = st.columns(3)
        m1.metric("Holdings (Indicative)", f"${holdings_value:,.2f}")
        m2.metric("Total Value", f"${total_value:,.2f}")
        pnl_delta = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
        m3.metric("P&L", f"${pnl:,.2f}", delta=pnl_delta)

        st.dataframe(
            dfp.style.format(
                {
                    "Quantity": "{:,.4g}",
                    "Avg Cost": "${:,.2f}",
                    "Last": lambda v: "—" if pd.isna(v) else f"${v:,.2f}",
                    "Market Value": lambda v: "—" if pd.isna(v) else f"${v:,.2f}",
                    "Unrealized P&L": lambda v: fmt_pnl_delta(v),
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.markdown("### Analytics")

        # Build a stable, hashable key for caching
        key_df = trades[["ts_utc", "ticker", "side", "qty", "price"]].copy()
        key_df["ts_utc"] = key_df["ts_utc"].astype(str)
        key_df["ticker"] = key_df["ticker"].astype(str)
        key_df["side"] = key_df["side"].astype(str)
        key_df["qty"] = key_df["qty"].astype(str)
        key_df["price"] = key_df["price"].astype(str)
        trades_key = tuple(map(tuple, key_df.values.tolist()))

        ts, ts_errs, ts_src = build_portfolio_analytics_timeseries(trades_key, float(initial_cash), provider_mode=provider_mode)
        if ts.empty:
            st.info("Not enough price history to build an equity curve yet.")
        else:
            c1, c2 = st.columns([2.2, 1.2])
            with c1:
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=ts.index, y=ts["Equity"], mode="lines", name="Equity"))
                if "Benchmark" in ts.columns and ts["Benchmark"].notna().any():
                    fig_eq.add_trace(go.Scatter(x=ts.index, y=ts["Benchmark"], mode="lines", name="Benchmark (SPY)", opacity=0.7))
                fig_eq.update_layout(
                    template=plotly_template,
                    height=420,
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=True,
                )
                st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})
                st.caption(f"Equity curve uses daily Close data. Source: {ts_src}")

            with c2:
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(x=ts.index, y=ts["Drawdown"] * 100.0, mode="lines", name="Drawdown %"))
                fig_dd.update_layout(
                    template=plotly_template,
                    height=420,
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                )
                fig_dd.update_yaxes(ticksuffix="%")
                st.plotly_chart(fig_dd, use_container_width=True, config={"displayModeBar": False})

            # Risk/return quick stats (demo-grade; RF=0)
            rets = ts["Equity"].pct_change().dropna()
            if not rets.empty and rets.std(ddof=0) > 0:
                vol_ann = float(rets.std(ddof=0) * (252**0.5))
                sharpe = float((rets.mean() * 252) / (rets.std(ddof=0) * (252**0.5)))
            else:
                vol_ann = None
                sharpe = None
            max_dd = float(ts["Drawdown"].min()) if "Drawdown" in ts.columns and ts["Drawdown"].notna().any() else None

            s1, s2, s3 = st.columns(3)
            s1.metric("Max Drawdown", "—" if max_dd is None else f"{max_dd*100:.2f}%")
            s2.metric("Vol (Ann.)", "—" if vol_ann is None else f"{vol_ann*100:.2f}%")
            s3.metric("Sharpe (RF=0)", "—" if sharpe is None else f"{sharpe:.2f}")

            # Allocation (current holdings)
            if "Market Value" in dfp.columns and dfp["Market Value"].abs().sum() > 0:
                fig_alloc = go.Figure(
                    data=[
                        go.Pie(
                            labels=dfp["Symbol"],
                            values=dfp["Market Value"].abs(),
                            hole=0.55,
                        )
                    ]
                )
                fig_alloc.update_layout(
                    template=plotly_template,
                    height=380,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=True,
                )
                st.plotly_chart(fig_alloc, use_container_width=True, config={"displayModeBar": False})

        if ts_errs and show_diagnostics:
            with st.expander(f"Analytics diagnostics ({len(ts_errs)})", expanded=False):
                for e in ts_errs[:50]:
                    st.write(f"- {e}")
                if len(ts_errs) > 50:
                    st.caption(f"(Showing 50 of {len(ts_errs)}.)")


elif page == "🧱 Activity":
    st.subheader("Activity Log")

    trades = read_trades()
    if trades.empty:
        st.info("No activity recorded yet.")
    else:
        view = trades.copy()
        view["Timestamp"] = view["ts_utc"].dt.tz_convert(None)
        view = view[["id", "Timestamp", "ticker", "side", "qty", "price", "note"]].rename(
            columns={"id": "ID", "ticker": "Symbol", "side": "Side", "qty": "Qty", "price": "Price", "note": "Note"}
        )
        st.dataframe(view, use_container_width=True, hide_index=True)

        csv = view.to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV", data=csv, file_name="activity_log.csv", mime="text/csv")


elif page == "⚙️ User Settings":
    st.subheader("User Settings")

    st.markdown("### Appearance")
    theme = st.selectbox(
        "Theme",
        ["Neon (Dark)", "Dark", "Light"],
        index=["Neon (Dark)", "Dark", "Light"].index(st.session_state["theme"]),
    )
    if theme != st.session_state["theme"]:
        st.session_state["theme"] = theme
        st.rerun()

    st.divider()
    st.markdown("### Market Data")
    provider = st.selectbox(
        "Market Data Provider",
        ["Auto", "Yahoo", "Stooq"],
        index=["Auto", "Yahoo", "Stooq"].index(st.session_state["provider_mode"]),
    )
    st.session_state["provider_mode"] = provider
    st.session_state["show_diagnostics"] = st.checkbox("Diagnostics", value=st.session_state["show_diagnostics"])
    st.caption("Tip: If Yahoo gets rate-limited on Streamlit Cloud, use Auto or Stooq (daily bars).")

    st.divider()
    st.markdown("### Live Refresh")
    ensure_live_defaults()
    st.session_state["live_playing"] = st.checkbox("Live mode (Play)", value=st.session_state["live_playing"])
    st.session_state["live_interval_ms"] = 3000
    st.caption("Live refresh is set to 3 seconds. Frequent refreshes may hit market data rate limits.")

    st.divider()
    st.markdown("### Account")
    current = get_initial_cash()
    new_cash = st.number_input("Starting Cash (USD)", min_value=0.0, value=float(current), step=1000.0)
    if st.button("Save Starting Cash"):
        set_initial_cash(float(new_cash))
        st.success("Saved.")
        st.rerun()

    st.divider()
    st.markdown("### Reset")
    st.warning("This will remove all trades and restore starting cash to $100,000.")
    if st.button("Full Reset"):
        reset_db()
        st.cache_data.clear()
        st.success("Reset complete.")
        st.rerun()
