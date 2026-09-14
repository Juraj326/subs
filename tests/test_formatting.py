from decimal import Decimal

import pytest

from subs.formatting import format_eur


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0.005"), "0.01€"),
        (Decimal("-0.005"), "-0.01€"),
        (Decimal(0), "0.00€"),
        (Decimal("1234.565"), "1,234.57€"),
    ],
)
def test_euro_formatting_rounds_half_up_at_the_display_boundary(value: Decimal, expected: str) -> None:
    assert format_eur(value) == expected
