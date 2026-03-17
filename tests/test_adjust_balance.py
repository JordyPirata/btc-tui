import pytest
from screens import AdjustBalanceModal, calc_balance_delta, format_adjustment_notes


# ── calc_balance_delta ────────────────────────────────────────────────────────

def test_delta_positive_when_new_total_is_higher():
    # Arrange
    current, new = 6_878_244, 6_878_330

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == 86

def test_delta_negative_when_new_total_is_lower():
    # Arrange
    current, new = 6_878_244, 6_877_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == -1_244

def test_delta_zero_when_totals_are_equal():
    # Arrange
    current = 6_878_244

    # Act
    result = calc_balance_delta(current, current)

    # Assert
    assert result == 0

def test_delta_from_empty_balance():
    # Arrange — empty balance, first deposit
    current, new = 0, 500_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == 500_000

def test_delta_results_in_negative_total():
    # Arrange — more expenses than income
    current, new = 10_000, -5_000

    # Act
    result = calc_balance_delta(new, current)

    # Assert
    assert result == -15_000


# ── format_adjustment_notes ───────────────────────────────────────────────────

def test_notes_with_description():
    # Arrange
    label, notes = "Routing fee", "LN payment"

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "[Routing fee] LN payment"

def test_notes_without_description_returns_label_only():
    # Arrange
    label, notes = "Expense", ""

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "Expense"

def test_notes_preserves_exact_description():
    # Arrange
    label, notes = "Correction +", "86 sats difference adjustment"

    # Act
    result = format_adjustment_notes(label, notes)

    # Assert
    assert result == "[Correction +] 86 sats difference adjustment"


# ── AdjustBalanceModal.TYPES ──────────────────────────────────────────────────

def test_types_has_correct_structure():
    # Arrange / Act
    types = AdjustBalanceModal.TYPES

    # Assert — each type has (label, key, sign)
    for label, key, sign in types:
        assert isinstance(label, str) and label
        assert isinstance(key,   str) and key
        assert sign in (-1, +1)

def test_types_expenses_have_negative_sign():
    # Arrange
    expense_keys = {"routing_fee", "exchange_fee", "expense", "transfer_out", "correction_neg"}

    # Act / Assert
    for label, key, sign in AdjustBalanceModal.TYPES:
        if key in expense_keys:
            assert sign == -1, f"{key} should be negative"

def test_types_income_have_positive_sign():
    # Arrange
    income_keys = {"income", "transfer_in", "correction_pos"}

    # Act / Assert
    for label, key, sign in AdjustBalanceModal.TYPES:
        if key in income_keys:
            assert sign == +1, f"{key} should be positive"

def test_types_no_duplicate_keys():
    # Arrange / Act
    keys = [key for _, key, _ in AdjustBalanceModal.TYPES]

    # Assert
    assert len(keys) == len(set(keys))


# ── Full flow (without UI) ────────────────────────────────────────────────────

@pytest.mark.parametrize("current,new_total,expected_delta,expected_notes", [
    # Routing fee of 86 sats — real case from this session
    (6_878_244, 6_878_330, +86,     "[Routing fee] LN adjustment"),
    # Expense: coffee
    (6_878_330, 6_867_000, -11_330, "[Expense] Breakfast"),
    # Positive correction without notes
    (1_000_000, 1_000_100, +100,    "Correction +"),
])
def test_full_flow_delta_and_notes(current, new_total, expected_delta, expected_notes):
    # Arrange
    label = expected_notes.split("] ")[0].lstrip("[") if "] " in expected_notes else expected_notes
    notes = expected_notes.split("] ")[1] if "] " in expected_notes else ""

    # Act
    delta  = calc_balance_delta(new_total, current)
    result = format_adjustment_notes(label, notes)

    # Assert
    assert delta  == expected_delta
    assert result == expected_notes
