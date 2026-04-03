#!/usr/bin/env python3
"""
Zerodha MCP Server - Query account data via Model Context Protocol
"""

import json
from mcp.server.fastmcp import FastMCP
from client import (
    get_orders, get_positions, get_holdings, get_funds, get_ltp, get_ohlc,
    get_pnl_summary as _get_pnl_summary, get_pnl_heatmap as _get_pnl_heatmap
)

mcp = FastMCP("zerodha")


@mcp.tool()
def get_account_funds() -> dict:
    """
    Get available funds and margins in your Zerodha account.
    Returns net balance and live available balance for equity segment.
    """
    return get_funds()


@mcp.tool()
def get_portfolio_holdings() -> list:
    """
    Get all long-term holdings in your Zerodha demat account.
    Returns list of stocks with quantity, average price, current value, and P&L.
    """
    return get_holdings()


@mcp.tool()
def get_open_positions() -> dict:
    """
    Get all open positions (intraday and F&O).
    Returns day positions and net positions with unrealized P&L.
    """
    return get_positions()


@mcp.tool()
def get_todays_orders() -> list:
    """
    Get all orders placed today.
    Returns list of orders with status, quantity, price, and execution details.
    """
    return get_orders()


@mcp.tool()
def get_current_pnl() -> dict:
    """
    Get combined P&L summary from positions and holdings.
    Returns total realized P&L, unrealized P&L, and day P&L.
    """
    positions = get_positions()
    holdings = get_holdings()

    # Calculate positions P&L
    day_pnl = sum(p.get("pnl", 0) or 0 for p in positions.get("day", []))
    net_pnl = sum(p.get("pnl", 0) or 0 for p in positions.get("net", []))

    # Calculate holdings P&L
    holdings_pnl = sum(h.get("pnl", 0) or 0 for h in holdings)
    holdings_day_change = sum(h.get("day_change", 0) or 0 for h in holdings)

    return {
        "positions_day_pnl": round(day_pnl, 2),
        "positions_net_pnl": round(net_pnl, 2),
        "holdings_total_pnl": round(holdings_pnl, 2),
        "holdings_day_change": round(holdings_day_change, 2),
        "total_day_pnl": round(day_pnl + holdings_day_change, 2),
        "total_unrealized_pnl": round(net_pnl + holdings_pnl, 2),
    }


@mcp.tool()
def get_instrument_ltp(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get the last traded price (LTP) of any instrument.

    Args:
        symbol: Trading symbol (e.g., "RELIANCE", "NIFTY 50", "NIFTY24DECFUT")
        exchange: Exchange code - NSE, BSE, NFO, CDS, BCD, MCX (default: NSE)

    Examples:
        get_instrument_ltp("RELIANCE", "NSE")
        get_instrument_ltp("NIFTY 50", "NSE")
        get_instrument_ltp("NIFTY24DECFUT", "NFO")
    """
    ltp = get_ltp(symbol, exchange)
    return {
        "symbol": symbol,
        "exchange": exchange,
        "last_price": ltp,
    }


@mcp.tool()
def get_instrument_ohlc(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get OHLC (Open, High, Low, Close) and LTP of any instrument.

    Args:
        symbol: Trading symbol (e.g., "RELIANCE", "NIFTY 50", "NIFTY24DECFUT")
        exchange: Exchange code - NSE, BSE, NFO, CDS, BCD, MCX (default: NSE)

    Returns:
        open: Today's open price
        high: Today's high price
        low: Today's low price
        close: Previous day's close price
        last_price: Current LTP

    Examples:
        get_instrument_ohlc("RELIANCE", "NSE")
        get_instrument_ohlc("NIFTY 50", "NSE")
    """
    ohlc = get_ohlc(symbol, exchange)
    return {
        "symbol": symbol,
        "exchange": exchange,
        **ohlc,
    }


@mcp.tool()
def get_pnl_summary(from_date: str, to_date: str, segment: str = "FO") -> dict:
    """
    Get realized PnL summary for a date range from Zerodha Console.

    Args:
        from_date: Start date in "YYYY-MM-DD" format
        to_date: End date in "YYYY-MM-DD" format
        segment: Market segment - "FO" for F&O, "EQ" for Equity (default: FO)

    Returns:
        realized_profit: Total realized profit/loss
        unrealized_profit: Unrealized profit/loss (open positions)
        total_charges: Total taxes and charges
        net_pnl: Net P&L after charges (realized - charges)
        raw: Full API response for detailed breakdown

    Note:
        Maximum date range is 3 months. For longer periods, make multiple requests.

    Examples:
        get_pnl_summary("2026-04-01", "2026-04-03", "FO")  # F&O this month
        get_pnl_summary("2026-01-01", "2026-03-31", "EQ")  # Equity Q1
    """
    return _get_pnl_summary(from_date, to_date, segment)


@mcp.tool()
def get_pnl_heatmap(from_date: str, to_date: str, segment: str = "FO") -> dict:
    """
    Get daily PnL heatmap for a date range from Zerodha Console.
    Shows day-by-day breakdown of realized profit/loss.

    Args:
        from_date: Start date in "YYYY-MM-DD" format
        to_date: End date in "YYYY-MM-DD" format
        segment: Market segment - "FO" for F&O, "EQ" for Equity (default: FO)

    Returns:
        Daily PnL data organized by date, useful for identifying
        profitable/losing days and patterns.

    Note:
        Maximum date range is 3 months. For longer periods, make multiple requests.

    Examples:
        get_pnl_heatmap("2026-04-01", "2026-04-03", "FO")
        get_pnl_heatmap("2026-03-01", "2026-03-31", "EQ")
    """
    return _get_pnl_heatmap(from_date, to_date, segment)


if __name__ == "__main__":
    mcp.run()
