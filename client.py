"""
Zerodha Kite API client for portfolio and order data.
"""

import csv
import io
from datetime import datetime
from pathlib import Path

import requests
from auth import get_enctoken

URLS = {
    "orders":    "https://kite.zerodha.com/oms/orders",
    "positions": "https://kite.zerodha.com/oms/portfolio/positions",
    "holdings":  "https://kite.zerodha.com/oms/portfolio/holdings",
    "margins":   "https://kite.zerodha.com/oms/user/margins",
}

# Cache for instruments data
_instruments_cache = {}
INSTRUMENTS_CACHE_FILE = Path(__file__).parent / "instruments_cache.csv"


def _headers():
    return {"authorization": get_enctoken()}


def get_orders():
    return requests.get(URLS["orders"], headers=_headers()).json()["data"]


def get_positions():
    data = requests.get(URLS["positions"], headers=_headers()).json()["data"]
    return {"day": data["day"], "net": data["net"]}


def get_holdings():
    return requests.get(URLS["holdings"], headers=_headers()).json()["data"]


def get_funds():
    data = requests.get(URLS["margins"], headers=_headers()).json()["data"]["equity"]
    return {
        "net":          data["net"],
        "live_balance": data["available"]["live_balance"],
    }


def _load_instruments(exchange: str) -> dict:
    """
    Load instruments for an exchange. Downloads from public API if not cached.
    Returns dict mapping (exchange, symbol) -> instrument_token
    """
    global _instruments_cache

    if exchange in _instruments_cache:
        return _instruments_cache[exchange]

    url = f"https://api.kite.trade/instruments/{exchange}"
    r = requests.get(url)
    r.raise_for_status()

    reader = csv.DictReader(io.StringIO(r.text))
    instruments = {}
    for row in reader:
        key = (row["exchange"], row["tradingsymbol"])
        instruments[key] = int(row["instrument_token"])

    _instruments_cache[exchange] = instruments
    return instruments


def _get_instrument_token(symbol: str, exchange: str) -> int:
    """Get instrument token for a symbol."""
    instruments = _load_instruments(exchange)
    key = (exchange, symbol)
    if key not in instruments:
        raise Exception(f"Instrument not found: {exchange}:{symbol}")
    return instruments[key]


def get_ohlc(symbol: str, exchange: str = "NSE") -> dict:
    """
    Returns OHLC + LTP of an instrument using historical candle data.
    LTP is derived from the last 1-minute candle's close price.

    Examples:
        get_ohlc("NIFTY 50", "NSE")
        get_ohlc("NIFTY26APRFUT", "NFO")
        get_ohlc("RELIANCE", "NSE")

    Returns dict:
        {
            "open":       float,   # today's open
            "high":       float,   # today's high
            "low":        float,   # today's low
            "close":      float,   # previous day close (from last candle)
            "last_price": float,   # current LTP (last candle close)
        }
    """
    token = _get_instrument_token(symbol, exchange)

    # Get today's minute candles
    today = datetime.now().strftime("%Y-%m-%d")
    from_dt = f"{today}+09:15:00"
    to_dt = f"{today}+15:30:00"

    url = f"https://kite.zerodha.com/oms/instruments/historical/{token}/minute?from={from_dt}&to={to_dt}"
    r = requests.get(url, headers=_headers()).json()

    if r["status"] != "success":
        raise Exception(r.get("message", "Failed to fetch historical data"))

    candles = r["data"]["candles"]
    if not candles:
        raise Exception(f"No candle data available for {exchange}:{symbol}")

    # Candle format: [timestamp, open, high, low, close, volume]
    # Calculate day's OHLC from all candles
    day_open = candles[0][1]
    day_high = max(c[2] for c in candles)
    day_low = min(c[3] for c in candles)
    last_close = candles[-1][4]  # LTP = last candle's close

    return {
        "open":       day_open,
        "high":       day_high,
        "low":        day_low,
        "close":      last_close,  # This is actually the current price
        "last_price": last_close,
    }


def get_ltp(symbol: str, exchange: str = "NSE") -> float:
    """
    Returns the last traded price of an instrument.
    Uses the last 1-minute candle's close price.

    Examples:
        get_ltp("NIFTY 50", "NSE")
        get_ltp("NIFTY26APRFUT", "NFO")
        get_ltp("RELIANCE", "NSE")
    """
    ohlc = get_ohlc(symbol, exchange)
    return ohlc["last_price"]


if __name__ == "__main__":
    print("=== Orders ===")
    print(get_orders())

    print("\n=== Positions ===")
    print(get_positions())

    print("\n=== Holdings ===")
    print(get_holdings())

    print("\n=== Funds ===")
    print(get_funds())
