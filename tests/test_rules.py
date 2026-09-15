"""Unit tests for the pure arrow puzzle rules (assignment T01-T07)."""
from arrowgame.levels import LEVELS, get_level
from arrowgame.rules import (
    available_arrows, can_exit, count_arrows, first_blocker,
    path_cells, remove_arrow, solve_order, validate_board,
)


def test_t01_clear_path_and_edge_exit():
    board = ("U..", "...", "..R")
    assert can_exit(board, 0, 0)
    assert can_exit(board, 2, 2)
    assert path_cells(board, 2, 2) == ()


def test_t02_long_distance_blocking_is_direction_agnostic():
    # The blocker is any occupied cell on the complete row, even after gaps.
    board = ("R...", ".D..", "....", "....")
    assert can_exit(board, 0, 0)  # the down arrow is on another path
    blocked = ("R..L", "....", "....", "....")
    assert not can_exit(blocked, 0, 0)
    assert first_blocker(blocked, 0, 0) == (0, 3)


def test_t03_remove_does_not_mutate_original():
    board = (("R", "."), (".", "U"))
    updated = remove_arrow(board, 0, 0)
    assert board == (("R", "."), (".", "U"))
    assert updated == ((".", "."), (".", "U"))
    assert count_arrows(updated) == 1


def test_t04_invalid_clicks_are_safe_and_do_not_exit():
    board = ((".", "R"),)
    assert not can_exit(board, 0, 0)
    assert not can_exit(board, -1, 0)
    assert not can_exit(board, 9, 9)


def test_t05_solve_order_clears_every_arrow():
    for level in LEVELS:
        order = solve_order(level.layout)
        assert order is not None
        assert len(order) == level.arrows
        state = level.layout
        for row, col in order:
            assert can_exit(state, row, col)
            state = remove_arrow(state, row, col)
        assert count_arrows(state) == 0


def test_t06_all_six_levels_are_valid_and_have_four_directions():
    assert len(LEVELS) == 6
    for level in LEVELS:
        validate_board(level.layout, require_all_directions=True)
        assert len(level.rows) == level.size
        assert all(len(row) == level.size for row in level.rows)
        assert {cell for row in level.rows for cell in row if cell != "."} >= {"U", "D", "L", "R"}


def test_t07_restart_copy_and_level_lookup():
    level = get_level(1)
    board = level.fresh_board()
    original = tuple(level.rows)
    board[0][0] = "."
    assert tuple(level.rows) == original
    assert get_level(1) is level
    try:
        get_level(99)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown level should raise ValueError")
