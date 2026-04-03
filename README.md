# Zerodha MCP Server

Query your Zerodha account via Claude Code.

## Tools Available

| Tool | Description |
|------|-------------|
| `get_account_funds` | Available balance and margins |
| `get_portfolio_holdings` | Long-term demat holdings |
| `get_open_positions` | Intraday/F&O positions with P&L |
| `get_todays_orders` | Today's order history |
| `get_current_pnl` | Combined P&L summary |

## Setup

1. Install dependencies:
```bash
cd "/Users/anish/Documents/anish projects/zerodha-mcp"
pip install -e .
```

2. Add to `~/.mcp.json`:
```json
{
  "mcpServers": {
    "zerodha": {
      "command": "python",
      "args": ["/Users/anish/Documents/anish projects/zerodha-mcp/server.py"]
    }
  }
}
```

3. Restart Claude Code

## Usage

Ask Claude things like:
- "What's my current portfolio value?"
- "Show me my open positions"
- "What's my P&L for today?"
- "How much funds do I have available?"
- "List my holdings"
