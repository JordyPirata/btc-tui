"""Cálculos puros sobre trades y spot — sin I/O."""
from __future__ import annotations

SATS = 100_000_000


def compute_stats(trades: list[dict], spot: list[dict], btc_price_usd: float) -> dict:
    filled   = [t for t in trades if t["status"] == "Filled"]
    winners  = [t for t in filled if t["pnl"] > 0]
    losers   = [t for t in filled if t["pnl"] <= 0]

    total_pnl  = sum(t["pnl"] for t in filled)
    total_fees = sum(t["trading_fees"] + t["funding_cost"] for t in filled)
    net_pnl    = total_pnl - total_fees
    win_rate   = len(winners) / len(filled) * 100 if filled else 0.0

    spot_manual     = sum(e["sats"] for e in spot)
    total_spot_sats = net_pnl + spot_manual
    spot_usd        = total_spot_sats / SATS * btc_price_usd

    return {
        "total_trades":     len(trades),
        "filled":           len(filled),
        "canceled":         len(trades) - len(filled),
        "winners":          len(winners),
        "losers":           len(losers),
        "win_rate":         win_rate,
        "total_pnl":        total_pnl,
        "total_fees":       total_fees,
        "net_pnl":          net_pnl,
        "best":             max((t["pnl"] for t in filled), default=0),
        "worst":            min((t["pnl"] for t in filled), default=0),
        "spot_manual":      spot_manual,
        "total_spot_sats":  total_spot_sats,
        "spot_usd":         spot_usd,
    }


def pnl_timeline(trades: list[dict]) -> list[dict]:
    """Puntos acumulados de P&L neto para las gráficas (solo Filled)."""
    cumulative = 0
    points = []
    for t in (t for t in trades if t["status"] == "Filled"):
        net = t["pnl"] - t["trading_fees"] - t["funding_cost"]
        cumulative += net
        points.append({
            "date":       (t["filled_date"] or t["creation_date"])[:10],
            "pnl":        net,
            "cumulative": cumulative,
        })
    return points
