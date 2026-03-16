"""Data layer: load, save, and compute BTC trade statistics."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_FILE = Path("data/trades.json")


def load_trades() -> list[dict]:
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text('{"trades": []}')
        return []
    try:
        data = json.loads(DATA_FILE.read_text())
        return sorted(data.get("trades", []), key=lambda t: t["date"])
    except Exception:
        return []


def save_trades(trades: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps({"trades": trades}, indent=2))


def add_trade(
    trade_type: str,
    date: str,
    btc_amount: float,
    price_usd: float,
    notes: str = "",
) -> dict:
    trades = load_trades()
    trade = {
        "id": str(uuid.uuid4())[:8],
        "type": trade_type,  # "buy" | "sell"
        "date": date,
        "btc_amount": float(btc_amount),
        "price_usd": float(price_usd),
        "total_usd": float(btc_amount) * float(price_usd),
        "notes": notes,
    }
    trades.append(trade)
    trades.sort(key=lambda t: t["date"])
    save_trades(trades)
    return trade


def delete_trade(trade_id: str) -> None:
    trades = load_trades()
    trades = [t for t in trades if t["id"] != trade_id]
    save_trades(trades)


def compute_stats(trades: list[dict], current_price: float) -> dict:
    btc = 0.0
    invested = 0.0
    received = 0.0
    for t in trades:
        if t["type"] == "buy":
            btc += t["btc_amount"]
            invested += t["total_usd"]
        else:
            btc -= t["btc_amount"]
            received += t["total_usd"]

    net_cost = invested - received
    current_val = btc * current_price
    pnl = current_val - net_cost
    roi = (pnl / invested * 100) if invested > 0 else 0.0
    avg_price = (invested / btc) if btc > 0 else 0.0

    return {
        "btc": btc,
        "invested": invested,
        "received": received,
        "net_cost": net_cost,
        "current_val": current_val,
        "pnl": pnl,
        "roi": roi,
        "avg_price": avg_price,
        "current_price": current_price,
    }


def get_timeline(trades: list[dict]) -> list[dict]:
    """Cumulative data points for charting (sorted by date)."""
    points = []
    btc = 0.0
    net_invested = 0.0
    for t in trades:
        if t["type"] == "buy":
            btc += t["btc_amount"]
            net_invested += t["total_usd"]
        else:
            btc -= t["btc_amount"]
            net_invested -= t["total_usd"]
        points.append(
            {
                "date": t["date"],
                "btc": max(0.0, btc),
                "invested": max(0.0, net_invested),
            }
        )
    return points
