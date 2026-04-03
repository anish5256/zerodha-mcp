# Zerodha MCP Server

Query your Zerodha trading account via MCP (Model Context Protocol). Works with Claude Code, Claude Desktop, Cursor, and other MCP-compatible AI tools.

## Tools Available

| Tool | Description |
|------|-------------|
| `get_account_funds` | Available balance and margins |
| `get_portfolio_holdings` | Long-term demat holdings |
| `get_open_positions` | Intraday/F&O positions with P&L |
| `get_todays_orders` | Today's order history |
| `get_current_pnl` | Combined P&L summary |
| `get_instrument_ltp` | Last traded price of any instrument |
| `get_instrument_ohlc` | OHLC data of any instrument |

## Installation

```bash
git clone https://github.com/anish5256/zerodha-mcp.git
cd zerodha-mcp
pip install -e .
```

## Configuration

### Environment Variables

The server requires these environment variables for authentication:

| Variable | Description |
|----------|-------------|
| `ZERODHA_USER_ID` | Your Zerodha client ID (e.g., `AB1234`) |
| `ZERODHA_PASSWORD` | Your Zerodha login password |
| `ZERODHA_TOTP_KEY` | Your TOTP secret key (32-character base32 string) |

### Getting Your TOTP Key

Your TOTP secret key is the 32-character code you used when setting up 2FA in Google Authenticator/Authy. It looks like: `ABCD1234EFGH5678IJKL9012MNOP3456`

If you don't have it saved, reset 2FA in [Zerodha Console](https://console.zerodha.com) to get a new one.

---

## Setup by Platform

### Claude Code (CLI)

Add to `~/.mcp.json`:

```json
{
  "mcpServers": {
    "zerodha": {
      "command": "python",
      "args": ["/path/to/zerodha-mcp/server.py"],
      "env": {
        "ZERODHA_USER_ID": "YOUR_USER_ID",
        "ZERODHA_PASSWORD": "YOUR_PASSWORD",
        "ZERODHA_TOTP_KEY": "YOUR_TOTP_SECRET"
      }
    }
  }
}
```

Then restart Claude Code.

---

### Claude Desktop (macOS)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zerodha": {
      "command": "python",
      "args": ["/path/to/zerodha-mcp/server.py"],
      "env": {
        "ZERODHA_USER_ID": "YOUR_USER_ID",
        "ZERODHA_PASSWORD": "YOUR_PASSWORD",
        "ZERODHA_TOTP_KEY": "YOUR_TOTP_SECRET"
      }
    }
  }
}
```

Then restart Claude Desktop.

---

### Claude Desktop (Windows)

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zerodha": {
      "command": "python",
      "args": ["C:\\path\\to\\zerodha-mcp\\server.py"],
      "env": {
        "ZERODHA_USER_ID": "YOUR_USER_ID",
        "ZERODHA_PASSWORD": "YOUR_PASSWORD",
        "ZERODHA_TOTP_KEY": "YOUR_TOTP_SECRET"
      }
    }
  }
}
```

Then restart Claude Desktop.

---

### Cursor

Add to Cursor's MCP settings (Settings > MCP):

```json
{
  "zerodha": {
    "command": "python",
    "args": ["/path/to/zerodha-mcp/server.py"],
    "env": {
      "ZERODHA_USER_ID": "YOUR_USER_ID",
      "ZERODHA_PASSWORD": "YOUR_PASSWORD",
      "ZERODHA_TOTP_KEY": "YOUR_TOTP_SECRET"
    }
  }
}
```

---

### Other MCP Clients

For any MCP-compatible client, configure:

- **Command:** `python`
- **Args:** `["/path/to/zerodha-mcp/server.py"]`
- **Environment Variables:**
  - `ZERODHA_USER_ID` = Your client ID
  - `ZERODHA_PASSWORD` = Your password
  - `ZERODHA_TOTP_KEY` = Your TOTP secret

---

## Usage Examples

Once configured, ask your AI assistant:

- "What's my current portfolio value?"
- "Show me my open positions"
- "What's my P&L for today?"
- "How much funds do I have available?"
- "What's the LTP of RELIANCE?"
- "Get OHLC for NIFTY 50"

## Security Notes

- Your credentials are stored locally in your MCP config file
- Credentials are never sent to the AI model, only used server-side
- The enctoken is cached locally in `zerodha_enctoken.txt` (gitignored)
- Each user must configure their own credentials on their own machine

## License

MIT
