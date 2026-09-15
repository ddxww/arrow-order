"""Pure rules for the Arrow Order puzzle.

The module deliberately has no pygame dependency, so the same functions can
be used by the game loop, level validator and unit tests.  A board is any
rectangular sequence of rows; a non-empty cell contains one of ``up``,
``down``, ``left`` or ``right`` (the arrow glyphs ``^v<>`` are accepted too).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

DIRECTIONS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
    "^": (-1, 0),
    "v": (1, 0),
    "<": (0, -1),
    ">": (0, 1),
}
_ALIASES = {"U": "up", "D": "down", "L": "left", "R": "right",
            "u": "up", "d": "down", "l": "left", "r": "right"}
EMPTY = (None, "", ".", 0, False)


def _direction(value: str) -> tuple[int, int]:
    try:
        return DIRECTIONS[_ALIASES.get(value, value).lower()]
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"unknown arrow direction: {value!r}") from exc


def _shape(board: Sequence[Sequence[object]]) -> tuple[int, int]:
    rows = len(board)
    cols = len(board[0]) if rows else 0
    if any(len(row) != cols for row in board):
        raise ValueError("board must be rectangular")
    return rows, cols


def path_cells(board: Sequence[Sequence[object]], row: int, col: int) -> tuple[tuple[int, int], ...]:
    """Return cells strictly in front of an arrow, up to the board edge."""
    rows, cols = _shape(board)
    if not (0 <= row < rows and 0 <= col < cols):
        raise IndexError((row, col))
    value = board[row][col]
    if value in EMPTY:
        raise ValueError("selected cell is empty")
    dr, dc = _direction(value)
    result: list[tuple[int, int]] = []
    r, c = row + dr, col + dc
    while 0 <= r < rows and 0 <= c < cols:
        result.append((r, c))
        r, c = r + dr, c + dc
    return tuple(result)


def first_blocker(board: Sequence[Sequence[object]], row: int, col: int) -> tuple[int, int] | None:
    """Return the nearest occupied cell on an arrow's path, if any."""
    for cell in path_cells(board, row, col):
        if board[cell[0]][cell[1]] not in EMPTY:
            return cell
    return None


def can_exit(board: Sequence[Sequence[object]], row: int, col: int) -> bool:
    """Whether the selected arrow can fly out without hitting another arrow."""
    rows, cols = _shape(board)
    if not (0 <= row < rows and 0 <= col < cols) or board[row][col] in EMPTY:
        return False
    return first_blocker(board, row, col) is None


def count_arrows(board: Sequence[Sequence[object]]) -> int:
    """Count occupied cells in a board."""
    _shape(board)
    return sum(cell not in EMPTY for row in board for cell in row)


def available_arrows(board: Sequence[Sequence[object]]) -> tuple[tuple[int, int], ...]:
    """Return all currently removable arrows in row-major order."""
    _shape(board)
    return tuple(
        (r, c)
        for r, row in enumerate(board)
        for c, value in enumerate(row)
        if value not in EMPTY and can_exit(board, r, c)
    )


def remove_arrow(board: Sequence[Sequence[object]], row: int, col: int) -> tuple[tuple[object, ...], ...]:
    """Return a copied board with one arrow removed."""
    rows, cols = _shape(board)
    if not (0 <= row < rows and 0 <= col < cols):
        raise IndexError((row, col))
    if board[row][col] in EMPTY:
        raise ValueError("selected cell is empty")
    copied = [list(r) for r in board]
    copied[row][col] = "."
    return tuple(tuple(r) for r in copied)


def solve_order(board: Sequence[Sequence[object]]) -> tuple[tuple[int, int], ...] | None:
    """Find a complete legal removal order, or ``None`` when unsolvable.

    A memoised depth-first search keeps this validator useful for small course
    levels while correctly handling cases where a greedy choice gets stuck.
    """
    rows, cols = _shape(board)
    initial = tuple(tuple(row) for row in board)

    @lru_cache(maxsize=None)
    def search(state: tuple[tuple[object, ...], ...]):
        if count_arrows(state) == 0:
            return ()
        for r, c in available_arrows(state):
            rest = search(remove_arrow(state, r, c))
            if rest is not None:
                return ((r, c),) + rest
        return None

    return search(initial)


def is_solvable(board: Sequence[Sequence[object]]) -> bool:
    """Return ``True`` when every arrow can be removed legally."""
    return solve_order(board) is not None


def validate_board(board: Sequence[Sequence[object]], require_all_directions: bool = False) -> None:
    """Raise ``ValueError`` when a board is malformed or cannot be solved."""
    rows, cols = _shape(board)
    if rows == 0 or cols == 0:
        raise ValueError("board cannot be empty")
    values = [cell for row in board for cell in row if cell not in EMPTY]
    for value in values:
        _direction(value)
    if require_all_directions and {_direction(v) for v in values} != {(-1, 0), (1, 0), (0, -1), (0, 1)}:
        raise ValueError("board must contain up, down, left and right arrows")
    if values and solve_order(board) is None:
        raise ValueError("board has no complete removal order")


__all__ = ["DIRECTIONS", "path_cells", "first_blocker", "can_exit", "count_arrows", "available_arrows", "remove_arrow", "solve_order", "is_solvable", "validate_board"]
