"""Data layer — trades de futuros BTC denominados en satoshis."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

DATA_FILE = Path("data/trades.json")
SATS = 100_000_000  # sats per BTC

_EMPTY = {"trades": [], "spot": []}


def _load() -> dict:
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(_EMPTY, indent=2))
        return {"trades": [], "spot": []}
    try:
        data = json.loads(DATA_FILE.read_text())
        data.setdefault("spot", [])
        return data
    except Exception:
        return {"trades": [], "spot": []}


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


def load_trades() -> list[dict]:
    return sorted(_load()["trades"], key=lambda t: t["creation_date"])


def load_spot() -> list[dict]:
    return sorted(_load()["spot"], key=lambda e: e["date"])


def save_trades(trades: list[dict]) -> None:
    data = _load()
    data["trades"] = trades
    _save(data)


def add_trade(fields: dict) -> dict:
    trades = load_trades()
    trade = {
        "id": fields.get("id") or str(uuid.uuid4())[:8],
        "direction": fields["direction"],         # "Long" | "Short"
        "status": fields["status"],               # "Filled" | "Canceled" | "Open"
        "pnl": int(fields.get("pnl", 0)),         # sats
        "quantity": int(fields.get("quantity", 0)),       # sats
        "trade_margin": int(fields.get("trade_margin", 0)),  # sats
        "margin": int(fields.get("margin", 0)),           # sats
        "leverage": float(fields.get("leverage", 1.0)),
        "price": float(fields.get("price", 0)),           # entry price USD
        "liquidation": float(fields.get("liquidation", 0)),
        "stoploss": float(fields.get("stoploss", 0)),
        "takeprofit": float(fields.get("takeprofit", 0)),
        "trading_fees": int(fields.get("trading_fees", 0)),  # sats
        "funding_cost": int(fields.get("funding_cost", 0)),  # sats
        "creation_date": fields["creation_date"],
        "filled_date": fields.get("filled_date") or "",
        "notes": fields.get("notes", ""),
    }
    trades.append(trade)
    trades.sort(key=lambda t: t["creation_date"])
    save_trades(trades)
    return trade


def delete_trade(trade_id: str) -> None:
    trades = load_trades()
    save_trades([t for t in trades if t["id"] != trade_id])


# ---------------------------------------------------------------------------
# Spot entries
# ---------------------------------------------------------------------------


def add_spot_entry(date: str, sats: int, notes: str = "") -> dict:
    data = _load()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": date,
        "sats": int(sats),   # positivo = ingreso, negativo = retiro
        "notes": notes,
    }
    data["spot"].append(entry)
    data["spot"].sort(key=lambda e: e["date"])
    _save(data)
    return entry


def delete_spot_entry(entry_id: str) -> None:
    data = _load()
    data["spot"] = [e for e in data["spot"] if e["id"] != entry_id]
    _save(data)


def compute_stats(trades: list[dict], spot: list[dict], btc_price_usd: float) -> dict:
    filled = [t for t in trades if t["status"] == "Filled"]

    total_pnl  = sum(t["pnl"] for t in filled)
    total_fees = sum(t["trading_fees"] + t["funding_cost"] for t in filled)
    net_pnl    = total_pnl - total_fees

    winners  = [t for t in filled if t["pnl"] > 0]
    losers   = [t for t in filled if t["pnl"] <= 0]
    win_rate = (len(winners) / len(filled) * 100) if filled else 0.0

    best  = max((t["pnl"] for t in filled), default=0)
    worst = min((t["pnl"] for t in filled), default=0)

    spot_manual = sum(e["sats"] for e in spot)
    total_spot_sats = net_pnl + spot_manual
    spot_usd = total_spot_sats / SATS * btc_price_usd

    return {
        "total_trades": len(trades),
        "filled":       len(filled),
        "canceled":     len(trades) - len(filled),
        "winners":      len(winners),
        "losers":       len(losers),
        "win_rate":     win_rate,
        "total_pnl":    total_pnl,
        "total_fees":   total_fees,
        "net_pnl":      net_pnl,
        "best":         best,
        "worst":        worst,
        "spot_manual":  spot_manual,
        "total_spot_sats": total_spot_sats,
        "spot_usd":     spot_usd,
        "btc_price":    btc_price_usd,
    }


def get_pnl_timeline(trades: list[dict]) -> list[dict]:
    """Puntos para graficar P&L acumulado (solo trades Filled)."""
    filled = [t for t in trades if t["status"] == "Filled"]
    points = []
    cumulative = 0
    for t in filled:
        net = t["pnl"] - t["trading_fees"] - t["funding_cost"]
        cumulative += net
        points.append({
            "date": (t["filled_date"] or t["creation_date"])[:10],
            "pnl": net,
            "cumulative": cumulative,
        })
    return points
