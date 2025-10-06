"""Utility helpers used across the backend."""

import string


_BASE36_ALPHABET = string.digits + string.ascii_uppercase


def to_base36(number: int) -> str:
    """Convert an integer to Base36."""
    if not isinstance(number, int) or number < 0:
        raise ValueError("The number must be a non-negative integer.")
    if number == 0:
        return _BASE36_ALPHABET[0]

    digits = []
    base = len(_BASE36_ALPHABET)
    while number:
        number, remainder = divmod(number, base)
        digits.append(_BASE36_ALPHABET[remainder])
    return "".join(reversed(digits))


def from_base36(value: str) -> int:
    """Convert a Base36 string back to an integer."""
    if not value:
        raise ValueError("The value cannot be empty.")
    value = value.strip().upper()
    allowed = set(_BASE36_ALPHABET)
    if any(char not in allowed for char in value):
        raise ValueError("The value contains invalid Base36 characters.")
    base = len(_BASE36_ALPHABET)
    result = 0
    for char in value:
        result = result * base + _BASE36_ALPHABET.index(char)
    return result
