"""
Zerodha Kite API client for portfolio and order data.
"""

import csv
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pathlib import Path

import time
import requests
from auth import get_enctoken, get_console_tokens, HEADERS

# Zerodha Console PnL report limit: max 3 months per request
MAX_PNL_MONTHS = 3

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


def _console_headers():
    """Get headers for Zerodha Console API requests."""
    public_token, session = get_console_tokens()
    return {
        "user-agent": HEADERS["user-agent"],
        "cookie": f"public_token={public_token}; session={session};",
        "x-csrftoken": public_token,
    }


def _validate_pnl_date_range(from_date: str, to_date: str) -> None:
    """
    Validate that the date range doesn't exceed Zerodha's limit.
    Raises ValueError if the range exceeds MAX_PNL_MONTHS (3 months).
    """
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

    if from_dt > to_dt:
        raise ValueError(f"from_date ({from_date}) cannot be after to_date ({to_date})")

    # Calculate the difference in months
    max_allowed_date = from_dt + relativedelta(months=MAX_PNL_MONTHS)

    if to_dt > max_allowed_date:
        raise ValueError(
            f"Date range exceeds {MAX_PNL_MONTHS} months limit. "
            f"Maximum to_date for from_date={from_date} is {max_allowed_date.strftime('%Y-%m-%d')}. "
            f"Split your request into multiple {MAX_PNL_MONTHS}-month chunks."
        )


def get_pnl_summary(from_date: str, to_date: str, segment: str = "FO") -> dict:
    """
    Fetches realized PnL summary from Zerodha Console.

    Args:
        from_date: Start date in "YYYY-MM-DD" format
        to_date: End date in "YYYY-MM-DD" format
        segment: "FO" (F&O) or "EQ" (Equity)

    Note:
        Maximum date range is 3 months. For longer periods, make multiple requests.

    Returns:
        {
            "realized_profit": float,
            "total_charges": float,
            "net_pnl": float,
            "raw": dict,
        }
    """
    _validate_pnl_date_range(from_date, to_date)
    headers = _console_headers()
    url = (
        f"https://console.zerodha.com/api/reports/pnl/summary"
        f"?segment={segment}&from_date={from_date}&to_date={to_date}"
    )

    r = requests.get(url, headers=headers).json()

    # Retry if report is pending
    for _ in range(3):
        if r.get("status") == "success" and r["data"].get("state") == "PENDING":
            print("Report pending, retrying in 3s...")
            time.sleep(3)
            r = requests.get(url, headers=headers).json()
        else:
            break

    if r.get("status") != "success":
        raise Exception(f"API error: {r}")

    result = r["data"]["result"]
    realized_profit = result["pnl"]["realized_profit"] or 0
    unrealized_profit = result["pnl"].get("unrealized_profit") or 0

    total_charges = 0
    for charge in result.get("charges", []):
        try:
            total_charges += charge.get("tax_amount", 0) or 0
        except (KeyError, TypeError):
            pass
    # Include other_charges if present
    total_charges += result.get("other_charges", 0) or 0

    return {
        "realized_profit": realized_profit,
        "unrealized_profit": unrealized_profit,
        "total_charges": total_charges,
        "net_pnl": realized_profit - total_charges,
        "raw": result,
    }


def get_pnl_heatmap(from_date: str, to_date: str, segment: str = "FO") -> dict:
    """
    Fetches daily PnL heatmap from Zerodha Console.

    Args:
        from_date: Start date in "YYYY-MM-DD" format
        to_date: End date in "YYYY-MM-DD" format
        segment: "FO" or "EQ"

    Note:
        Maximum date range is 3 months. For longer periods, make multiple requests.

    Returns:
        raw heatmap data dict with daily PnL breakdown
    """
    _validate_pnl_date_range(from_date, to_date)
    headers = _console_headers()
    url = (
        f"https://console.zerodha.com/api/reports/pnl/heatmap"
        f"?segment={segment}&from_date={from_date}&to_date={to_date}"
    )

    r = requests.get(url, headers=headers).json()

    # Retry if report is pending
    for _ in range(3):
        if r.get("status") == "success" and r["data"].get("state") == "PENDING":
            print("Heatmap pending, retrying in 3s...")
            time.sleep(3)
            r = requests.get(url, headers=headers).json()
        else:
            break

    if r.get("status") != "success":
        raise Exception(f"API error: {r}")

    return r["data"]


if __name__ == "__main__":
    print("=== Orders ===")
    print(get_orders())

    print("\n=== Positions ===")
    print(get_positions())

    print("\n=== Holdings ===")
    print(get_holdings())

    print("\n=== Funds ===")
    print(get_funds())

    print("\n=== PnL Summary (F&O, this month) ===")
    from datetime import date
    first_of_month = date.today().replace(day=1).strftime("%Y-%m-%d")
    today = date.today().strftime("%Y-%m-%d")
    try:
        pnl = get_pnl_summary(first_of_month, today, "FO")
        print(f"Realized: {pnl['realized_profit']}, Charges: {pnl['total_charges']}, Net: {pnl['net_pnl']}")
    except Exception as e:
        print(f"Error: {e}")
