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
        {"id": "3f4a5e35", "date": "2026-03-17", "sats":   -10_305, "notes": "Desayuno Café Adentro"},
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

def test_spot_total_suma_todas_las_entradas(spot_entries):
    # Arrange
    expected = 611_276 + 3_134_473 + 2_867_610 + 115_786 - 10_305

    # Act
    result = calc_spot_total(spot_entries)

    # Assert
    assert result == expected == 6_718_840

def test_spot_total_con_lista_vacia():
    # Arrange
    spot = []

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 0

def test_spot_total_incluye_entradas_negativas():
    # Arrange
    spot = [{"sats": 100_000}, {"sats": -5_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 95_000

def test_spot_total_entrada_unica():
    # Arrange
    spot = [{"sats": 500_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == 500_000

def test_spot_total_todas_negativas():
    # Arrange — balance neto negativo (más gastos que ingresos)
    spot = [{"sats": -10_000}, {"sats": -5_000}]

    # Act
    result = calc_spot_total(spot)

    # Assert
    assert result == -15_000


# ── calc_net_pnl ──────────────────────────────────────────────────────────────

def test_net_pnl_descuenta_fees_y_funding(filled_trades):
    # Arrange
    gross   = -68_479 + 49_911 + 79_247 + 151_922   # 212_601
    fees    = 10_763 + 10_714 + 10_690 + 21_568       # 53_735
    funding = -538                                     # negativo = recibido
    expected = gross - fees - funding                  # 159_404

    # Act
    result = calc_net_pnl(filled_trades)

    # Assert
    assert result == expected == 159_404

def test_net_pnl_ignora_trades_no_filled(filled_trades, open_trade):
    # Arrange
    all_trades = filled_trades + open_trade

    # Act
    result_all    = calc_net_pnl(all_trades)
    result_filled = calc_net_pnl(filled_trades)

    # Assert
    assert result_all == result_filled

def test_net_pnl_funding_negativo_suma_al_pnl():
    # Arrange — funding negativo en short = ingreso (te pagan)
    trades = [{"status": "Filled", "pnl": 10_000, "trading_fees": 500, "funding_cost": -200}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 10_000 - 500 - (-200) == 9_700

def test_net_pnl_lista_vacia():
    # Arrange
    trades = []

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 0

def test_net_pnl_solo_perdidas():
    # Arrange
    trades = [
        {"status": "Filled", "pnl": -50_000, "trading_fees": 5_000, "funding_cost": 0},
        {"status": "Filled", "pnl": -30_000, "trading_fees": 3_000, "funding_cost": 0},
    ]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -88_000

def test_net_pnl_fees_mayores_que_gross():
    # Arrange — ganas en P&L bruto pero las fees te dejan en negativo
    trades = [{"status": "Filled", "pnl": 1_000, "trading_fees": 5_000, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -4_000

def test_net_pnl_breakeven():
    # Arrange — trade con P&L exactamente 0
    trades = [{"status": "Filled", "pnl": 0, "trading_fees": 500, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == -500

@pytest.mark.parametrize("status", ["Open", "Cancelled", "Liquidated", "Pending"])
def test_net_pnl_ignora_status_no_filled(status):
    # Arrange
    trades = [{"status": status, "pnl": 100_000, "trading_fees": 1_000, "funding_cost": 0}]

    # Act
    result = calc_net_pnl(trades)

    # Assert
    assert result == 0


# ── calc_grand_total ──────────────────────────────────────────────────────────

def test_grand_total_es_spot_mas_net_pnl(spot_entries, filled_trades):
    # Arrange
    expected_spot   = 6_718_840
    expected_net    = 159_404
    expected_total  = expected_spot + expected_net  # 6_878_244

    # Act
    result = calc_grand_total(spot_entries, filled_trades)

    # Assert
    assert result == expected_total == 6_878_244

# ── validate_funding_sign ─────────────────────────────────────────────────────

@pytest.mark.parametrize("direction,funding_rate,funding_cost,expected", [
    # Tasa positiva → Short recibe (cost negativo) ✅
    ("Short", +0.01,  -538, True),
    # Tasa positiva → Short paga (cost positivo) ❌ — dato inconsistente
    ("Short", +0.01,  +538, False),
    # Tasa positiva → Long paga (cost positivo) ✅
    ("Long",  +0.01,  +538, True),
    # Tasa positiva → Long recibe (cost negativo) ❌ — dato inconsistente
    ("Long",  +0.01,  -538, False),
    # Tasa negativa → Short paga (cost positivo) ✅
    ("Short", -0.01,  +135, True),
    # Tasa negativa → Short recibe (cost negativo) ❌ — dato inconsistente
    ("Short", -0.01,  -135, False),
    # Tasa negativa → Long recibe (cost negativo) ✅
    ("Long",  -0.01,  -135, True),
    # Tasa negativa → Long paga (cost positivo) ❌ — dato inconsistente
    ("Long",  -0.01,  +135, False),
    # Funding cero → siempre válido independiente de la tasa
    ("Short", +0.01,     0, True),
    ("Long",  -0.01,     0, True),
    # Tasa cero con funding no cero → inconsistente (sin tasa no debería haber costo)
    ("Short",  0.00,  +100, False),
    ("Long",   0.00,  -100, False),
])
def test_validate_funding_sign(direction, funding_rate, funding_cost, expected):
    # Arrange — combinación de dirección, tasa y costo viene del parámetro

    # Act
    result = validate_funding_sign(direction, funding_rate, funding_cost)

    # Assert
    assert result == expected


def test_grand_total_sin_trades(spot_entries):
    # Arrange
    trades = []

    # Act
    result = calc_grand_total(spot_entries, trades)

    # Assert
    assert result == calc_spot_total(spot_entries)

def test_grand_total_negativo_cuando_perdidas_superan_spot():
    # Arrange — pérdidas en trades mayores que el balance spot
    spot   = [{"sats": 10_000}]
    trades = [{"status": "Filled", "pnl": -50_000, "trading_fees": 0, "funding_cost": 0}]

    # Act
    result = calc_grand_total(spot, trades)

    # Assert
    assert result == -40_000
