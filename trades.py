"""Persistencia y CRUD — trades de futuros y entradas spot."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

DATA_FILE = Path("data/trades.json")


def _load() -> dict:
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text('{"trades": [], "spot": []}')
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


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


def load_trades() -> list[dict]:
    return sorted(_load()["trades"], key=lambda t: t["creation_date"])


def add_trade(fields: dict) -> dict:
    data = _load()
    trade = {
        "id":           fields.get("id") or str(uuid.uuid4())[:8],
        "direction":    fields["direction"],
        "status":       fields["status"],
        "pnl":          int(fields.get("pnl", 0)),
        "quantity":     int(fields.get("quantity", 0)),
        "trade_margin": int(fields.get("trade_margin", 0)),
        "margin":       int(fields.get("margin", 0)),
        "leverage":     float(fields.get("leverage", 1.0)),
        "price":        float(fields.get("price", 0)),
        "liquidation":  float(fields.get("liquidation", 0)),
        "stoploss":     float(fields.get("stoploss", 0)),
        "takeprofit":   float(fields.get("takeprofit", 0)),
        "trading_fees": int(fields.get("trading_fees", 0)),
        "funding_cost": int(fields.get("funding_cost", 0)),
        "creation_date": fields["creation_date"],
        "filled_date":  fields.get("filled_date") or "",
        "notes":        fields.get("notes", ""),
    }
    data["trades"].append(trade)
    data["trades"].sort(key=lambda t: t["creation_date"])
    _save(data)
    return trade


def delete_trade(trade_id: str) -> None:
    data = _load()
    data["trades"] = [t for t in data["trades"] if t["id"] != trade_id]
    _save(data)


# ---------------------------------------------------------------------------
# Spot
# ---------------------------------------------------------------------------


def load_spot() -> list[dict]:
    return sorted(_load()["spot"], key=lambda e: e["date"])


def add_spot_entry(date: str, sats: int, notes: str = "") -> dict:
    data = _load()
    entry = {
        "id":    str(uuid.uuid4())[:8],
        "date":  date,
        "sats":  int(sats),
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
