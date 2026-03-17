# btc-tui

A keyboard-driven terminal UI for tracking Bitcoin futures trades and spot balance. Built with [Textual](https://github.com/Textualize/textual) and [plotext](https://github.com/piccolomo/plotext).

![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Track futures positions (Long/Short) with P&L, fees, leverage, and margin in satoshis
- Manual spot entries to record deposits and withdrawals
- Live BTC price via CoinGecko API — converts sats balance to USD
- P&L timeline chart and cumulative balance chart
- All keyboard-driven — no mouse required

## Keybindings

| Key | Action |
|-----|--------|
| `1` / `2` / `3` | Switch tabs (Trades / Spot / Charts) |
| `A` | Add trade |
| `S` | Add spot entry |
| `D` | Delete selected row |
| `R` | Refresh BTC price |
| `?` | Help |
| `Q` | Quit |
| `Ctrl+S` | Save (inside modal forms) |
| `Escape` | Cancel (inside modal forms) |

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/btc-tui.git
cd btc-tui

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Usage

```bash
source venv/bin/activate
python main.py
# or
./run.sh
```

On first run, `data/trades.json` is created automatically. You can use `data/trades.json.example` as a reference for the data structure.

## Data model

Data is stored locally in `data/trades.json` (not synced, not tracked by git).

**Trades** — futures positions (values in satoshis, except price fields which are USD):

| Field | Description |
|-------|-------------|
| `direction` | `Long` or `Short` |
| `status` | `Filled`, `Open`, or `Canceled` |
| `pnl` | Gross P&L in sats |
| `margin` | Margin used in sats |
| `leverage` | Leverage multiplier |
| `price` | Entry price in USD |
| `trading_fees` | Exchange fees in sats |
| `funding_cost` | Funding rate cost in sats (can be negative) |
| `close_event` | `none`, `stoploss`, or `takeprofit` |

**Spot entries** — manual sats movements (positive = deposit, negative = withdrawal).

**Net P&L** = `pnl - (trading_fees + funding_cost)`

## Requirements

- Python 3.10+
- Linux or macOS (Windows untested)

## License

MIT
