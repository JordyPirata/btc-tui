"""Pure computations on trades and spot — no I/O."""
from __future__ import annotations

SATS = 100_000_000


# ── Utility functions ─────────────────────────────────────────────────────────

def calc_spot_total(spot: list[dict]) -> int:
    return sum(e["sats"] for e in spot)


def calc_net_pnl(trades: list[dict]) -> int:
    filled        = [t for t in trades if t["status"] == "Filled"]
    gross_pnl     = sum(t["pnl"]          for t in filled)
    total_fees    = sum(t["trading_fees"] for t in filled)
    total_funding = sum(t["funding_cost"] for t in filled)
    return gross_pnl - total_fees - total_funding


def calc_grand_total(spot: list[dict], trades: list[dict]) -> int:
    return calc_spot_total(spot) + calc_net_pnl(trades)


def validate_funding_sign(direction: str, funding_rate: float, funding_cost: int) -> bool:
    """
    Validates that funding_cost sign is consistent with direction and funding_rate.

    | Rate      | Long         | Short        |
    |-----------|--------------|--------------|
    | Positive  | pays (+cost) | receives (−) |
    | Negative  | receives (−) | pays (+cost) |
    """
    if funding_cost == 0:
        return True
    if funding_rate == 0:
        return False  # zero rate should produce no funding cost
    short_receives = direction == "Short" and funding_rate > 0
    long_receives  = direction == "Long"  and funding_rate < 0
    if short_receives or long_receives:
        return funding_cost < 0   # negative cost = received
    return funding_cost > 0       # positive cost = paid


# ── Aggregated stats ──────────────────────────────────────────────────────────

def compute_stats(trades: list[dict], spot: list[dict], btc_price_usd: float) -> dict:
    filled  = [t for t in trades if t["status"] == "Filled"]
    winners = [t for t in filled if t["pnl"] > 0]
    losers  = [t for t in filled if t["pnl"] <= 0]

    total_pnl       = sum(t["pnl"] for t in filled)
    total_fees      = sum(t["trading_fees"] + t["funding_cost"] for t in filled)
    net_pnl         = calc_net_pnl(trades)
    win_rate        = len(winners) / len(filled) * 100 if filled else 0.0

    spot_manual     = calc_spot_total(spot)
    total_spot_sats = calc_grand_total(spot, trades)
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
    """Cumulative net P&L data points for charts (Filled trades only)."""
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
