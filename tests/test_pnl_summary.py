import pytest
from stats import calc_spot_total, calc_net_pnl, calc_grand_total, validate_funding_sign


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def spot_entries():
    return [
        {"id": "e5c0361c", "date": "2026-03-16", "sats":  611_276, "notes": "Init"},
        {"id": "cfe275f2", "date": "2026-03-16", "sats": 3_134_473, "notes": "Init"},
        {"id": "deae94cf", "date": "2026-03-16", "sats": 2_867_610, "notes": "Init"},
        {"id": "86676ef0", "date": "2026-03-16", "sats":   115_786, "notes": "Isolated"},
        {"id": "3f4a5e35", "date": "2026-03-17", "sats":   -10_305, "notes": "Breakfast"},
    ]

@pytest.fixture
def filled_trades():
    return [
        {
            "id": "29312b0b", "direction": "Short", "status": "Filled",
            "pnl": -68_479, "trading_fees": 10_763, "funding_cost": 0,
        },
        {
            "id": "15ac11bc", "direction": "Short", "status": "Filled",
            "pnl": 49_911, "trading_fees": 10_714, "funding_cost": 0,
        },
        {
            "id": "a794678f", "direction": "Short", "status": "Filled",
            "pnl": 79_247, "trading_fees": 10_690, "funding_cost": 0,
        },
        {
            "id": "db78ac40", "direction": "Short", "status": "Filled",
            "pnl": 151_922, "trading_fees": 21_568, "funding_cost": -538,
        },
    ]

@pytest.fixture
def open_trade():
    return [
        {
            "id": "open001", "direction": "Short", "status": "Open",
            "pnl": -52_726, "trading_fees": 5_000, "funding_cost": -135,
        }
    ]


# ── calc_spot_total ───────────────────────────────────────────────────────────

def test_spot_total_sums_all_entries(spot_entries):
    # Arrange
    expected = 611_276 + 3_134_473 + 2_867_610 + 115_786 - 10_305

    # Act
    result = calc_spot_total(spot_entries)

    # Assert
    assert result == expected == 6_718_840

def test_spot_total_empty_list():
    # Arrange
    spot = []

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 0

def test_spot_total_includes_negative_entries():
    # Arrange
    spot = [{"sats": 100_000}, {"sats": -5_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 95_000

def test_spot_total_single_entry():
    # Arrange
    spot = [{"sats": 500_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 500_000

def test_spot_total_all_negative():
    # Arrange — net negative balance (more expenses than income)
    spot = [{"sats": -10_000}, {"sats": -5_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == -15_000


# ── calc_net_pnl ──────────────────────────────────────────────────────────────

def test_net_pnl_deducts_fees_and_funding(filled_trades):
    # Arrange
    gross   = -68_479 + 49_911 + 79_247 + 151_922   # 212_601
    fees    = 10_763 + 10_714 + 10_690 + 21_568       # 53_735
    funding = -538                                     # negative = received
    expected = gross - fees - funding                  # 159_404

    # Act
    result = calc_net_pnl(filled_trades)

    # Assert
    assert result == expected == 159_404

def test_net_pnl_ignores_non_filled_trades(filled_trades, open_trade):
    # Arrange
    all_trades = filled_trades + open_trade

    # Act
    result_all    = calc_net_pnl(all_trades)
    result_filled = calc_net_pnl(filled_trades)

    # Assert
    assert result_all == result_filled

def test_net_pnl_negative_funding_adds_to_pnl():
    # Arrange — negative funding on short = income (received payment)
    trades = [{"status": "Filled", "pnl": 10_000, "trading_fees": 500, "funding_cost": -200}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 10_000 - 500 - (-200) == 9_700

def test_net_pnl_empty_list():
    # Arrange
    trades = []

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 0

def test_net_pnl_only_losses():
    # Arrange
    trades = [
        {"status": "Filled", "pnl": -50_000, "trading_fees": 5_000, "funding_cost": 0},
        {"status": "Filled", "pnl": -30_000, "trading_fees": 3_000, "funding_cost": 0},
    ]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -88_000

def test_net_pnl_fees_exceed_gross():
    # Arrange — gross P&L is positive but fees push net negative
    trades = [{"status": "Filled", "pnl": 1_000, "trading_fees": 5_000, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -4_000

def test_net_pnl_breakeven():
    # Arrange — trade with exactly zero P&L
    trades = [{"status": "Filled", "pnl": 0, "trading_fees": 500, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -500

@pytest.mark.parametrize("status", ["Open", "Cancelled", "Liquidated", "Pending"])
def test_net_pnl_ignores_non_filled_status(status):
    # Arrange
    trades = [{"status": status, "pnl": 100_000, "trading_fees": 1_000, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 0


# ── calc_grand_total ──────────────────────────────────────────────────────────

def test_grand_total_is_spot_plus_net_pnl(spot_entries, filled_trades):
    # Arrange
    expected_spot  = 6_718_840
    expected_net   = 159_404
    expected_total = expected_spot + expected_net  # 6_878_244

    # Act
    result = calc_grand_total(spot_entries, filled_trades)

    # Assert
    assert result == expected_total == 6_878_244

def test_grand_total_no_trades(spot_entries):
    # Arrange
    trades = []

    # Act
    result = calc_grand_total(spot_entries, trades)

    # Assert
    assert result == calc_spot_total(spot_entries)

def test_grand_total_negative_when_losses_exceed_spot():
    # Arrange — trade losses greater than spot balance
    spot   = [{"sats": 10_000}]
    trades = [{"status": "Filled", "pnl": -50_000, "trading_fees": 0, "funding_cost": 0}]

    # Act
    result = calc_grand_total(spot, trades)

    # Assert
    assert result == -40_000


# ── validate_funding_sign ─────────────────────────────────────────────────────

@pytest.mark.parametrize("direction,funding_rate,funding_cost,expected", [
    # Positive rate → Short receives (negative cost) ✅
    ("Short", +0.01,  -538, True),
    # Positive rate → Short pays (positive cost) ❌ — inconsistent data
    ("Short", +0.01,  +538, False),
    # Positive rate → Long pays (positive cost) ✅
    ("Long",  +0.01,  +538, True),
    # Positive rate → Long receives (negative cost) ❌ — inconsistent data
    ("Long",  +0.01,  -538, False),
    # Negative rate → Short pays (positive cost) ✅
    ("Short", -0.01,  +135, True),
    # Negative rate → Short receives (negative cost) ❌ — inconsistent data
    ("Short", -0.01,  -135, False),
    # Negative rate → Long receives (negative cost) ✅
    ("Long",  -0.01,  -135, True),
    # Negative rate → Long pays (positive cost) ❌ — inconsistent data
    ("Long",  -0.01,  +135, False),
    # Zero funding cost → always valid regardless of rate
    ("Short", +0.01,     0, True),
    ("Long",  -0.01,     0, True),
    # Zero rate with non-zero cost → inconsistent (no rate should produce no cost)
    ("Short",  0.00,  +100, False),
    ("Long",   0.00,  -100, False),
])
def test_validate_funding_sign(direction, funding_rate, funding_cost, expected):
    # Arrange — combination of direction, rate and cost comes from parameter

    # Act
    result = validate_funding_sign(direction, funding_rate, funding_cost)

    # Assert
    assert result == expected
