from collections import defaultdict
from .constants import SIZE_CHOICES

TRAYS_PER_CRATE = 12
EGGS_PER_TRAY = 30


def to_trays(crates: int, trays: int) -> int:
    return (crates or 0) * TRAYS_PER_CRATE + (trays or 0)


def from_trays(total_trays: int) -> tuple[int, int]:
    total_trays = max(total_trays or 0, 0)
    return total_trays // TRAYS_PER_CRATE, total_trays % TRAYS_PER_CRATE


def trays_to_eggs(total_trays: int) -> int:
    return (total_trays or 0) * EGGS_PER_TRAY


def empty_stock_dict():
    return {code: 0 for code, _ in SIZE_CHOICES}
