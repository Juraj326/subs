from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

_CENT = Decimal("0.01")


def format_eur(value: Decimal | Fraction) -> str:
    if isinstance(value, Fraction):
        # Round the exact rate half away from zero, without an intermediate decimal.
        cents, remainder = divmod(abs(value.numerator) * 100, value.denominator)
        cents += 2 * remainder >= value.denominator
        sign = "-" if value < 0 else ""
        return f"{sign}{cents // 100:,}.{cents % 100:02d}€"
    rounded = value.quantize(_CENT, rounding=ROUND_HALF_UP)
    return f"{rounded:,.2f}€"
