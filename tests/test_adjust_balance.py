import pytest
from screens import AdjustBalanceModal, calc_balance_delta, format_adjustment_notes


# ── calc_balance_delta ────────────────────────────────────────────────────────

def test_delta_positivo_cuando_nuevo_total_es_mayor():
    # Arrange
    current, new = 6_878_244, 6_878_330

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == 86

def test_delta_negativo_cuando_nuevo_total_es_menor():
    # Arrange
    current, new = 6_878_244, 6_877_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == -1_244

def test_delta_cero_cuando_totales_son_iguales():
    # Arrange
    current = 6_878_244

    # Act
    result = calc_balance_delta(current, current)

    # Assert
    assert result == 0

def test_delta_desde_cero():
    # Arrange — balance vacío, primer depósito
    current, new = 0, 500_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == 500_000

def test_delta_resultado_negativo_total():
    # Arrange — más gastos que ingresos
    current, new = 10_000, -5_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == -15_000


# ── format_adjustment_notes ───────────────────────────────────────────────────

def test_notes_con_descripcion():
    # Arrange
    label, notes = "Routing fee", "pago LN"

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "[Routing fee] pago LN"

def test_notes_sin_descripcion_devuelve_solo_label():
    # Arrange
    label, notes = "Expense", ""

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "Expense"

def test_notes_preserva_descripcion_exacta():
    # Arrange
    label, notes = "Correction +", "ajuste por diferencia de 86 sats"

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "[Correction +] ajuste por diferencia de 86 sats"


# ── AdjustBalanceModal.TYPES ──────────────────────────────────────────────────

def test_types_tiene_estructura_correcta():
    # Arrange / Act
    types = AdjustBalanceModal.TYPES

    # Assert — cada tipo tiene (label, key, sign)
    for label, key, sign in types:
        assert isinstance(label, str) and label
        assert isinstance(key,   str) and key
        assert sign in (-1, +1)

def test_types_expenses_tienen_signo_negativo():
    # Arrange
    expense_keys = {"routing_fee", "exchange_fee", "expense", "transfer_out", "correction_neg"}

    # Act / Assert
    for label, key, sign in AdjustBalanceModal.TYPES:
        if key in expense_keys:
            assert sign == -1, f"{key} debería ser negativo"

def test_types_ingresos_tienen_signo_positivo():
    # Arrange
    income_keys = {"income", "transfer_in", "correction_pos"}

    # Act / Assert
    for label, key, sign in AdjustBalanceModal.TYPES:
        if key in income_keys:
            assert sign == +1, f"{key} debería ser positivo"

def test_types_no_tiene_keys_duplicados():
    # Arrange / Act
    keys = [key for _, key, _ in AdjustBalanceModal.TYPES]

    # Assert
    assert len(keys) == len(set(keys))


# ── Flujo completo (sin UI) ───────────────────────────────────────────────────

@pytest.mark.parametrize("current,new_total,expected_delta,expected_notes", [
    # Routing fee de 86 sats — caso real de la sesión
    (6_878_244, 6_878_330, +86,   "[Routing fee] ajuste LN"),
    # Gasto: café
    (6_878_330, 6_867_000, -11_330, "[Expense] Desayuno"),
    # Corrección positiva sin nota
    (1_000_000, 1_000_100, +100,  "Correction +"),
])
def test_flujo_delta_y_notas(current, new_total, expected_delta, expected_notes):
    # Arrange
    label = expected_notes.split("] ")[0].lstrip("[") if "] " in expected_notes else expected_notes
    notes = expected_notes.split("] ")[1] if "] " in expected_notes else ""

    # Act
    delta  = calc_balance_delta(new_total, current)
    result = format_adjustment_notes(label, notes)

    # Assert
    assert delta  == expected_delta
    assert result == expected_notes
