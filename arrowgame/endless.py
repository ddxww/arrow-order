"""Random solvable puzzles constrained by the six campaign difficulty bands."""
import random
from .levels import LEVELS, Level
from .rules import available_arrows, can_exit


def dependency_depth(rows):
    board = [list(row) for row in rows]
    depth = 0
    while any(cell != '.' for row in board for cell in row):
        available = available_arrows(board)
        if not available:
            return None
        for r, c in available:
            board[r][c] = '.'
        depth += 1
    return depth


def generate_level(round_number, rng=None, tier=None):
    rng = rng if rng is not None else random.Random()
    tier = rng.randint(1, 6) if tier is None else tier
    if tier not in range(1, 7):
        raise ValueError('tier must be 1..6')
    reference = LEVELS[tier-1]
    # Match board size and population; constrain dependency depth to the
    # reference level. Reverse insertion guarantees an acyclic removal order.
    maximum_depth = dependency_depth(reference.rows)
    minimum_depth = max(2, (maximum_depth+2)//3)
    for _ in range(48):
        board = [['.'] * reference.size for _ in range(reference.size)]
        for _ in range(reference.arrows):
            choices = []
            for r in range(reference.size):
                for c in range(reference.size):
                    if board[r][c] != '.':
                        continue
                    for direction in 'UDLR':
                        board[r][c] = direction
                        if can_exit(board, r, c):
                            choices.append((r, c, direction))
                    board[r][c] = '.'
            if not choices:
                break
            r, c, direction = rng.choice(choices)
            board[r][c] = direction
        rows = tuple(''.join(row) for row in board)
        values = {cell for row in rows for cell in row if cell != '.'}
        depth = dependency_depth(rows)
        if (sum(cell != '.' for row in rows for cell in row) == reference.arrows
                and values == set('UDLR') and depth is not None
                and minimum_depth <= depth <= maximum_depth):
            return Level(round_number, f'无尽挑战 · 第 {round_number} 关', f'难度 {tier}/6', rows,
                         '随机棋盘，沿箭头方向观察阻挡。每关恢复三次机会。')
    # Bounded fallback: random symmetries preserve the reference's difficulty.
    rows = reference.rows
    for _ in range(rng.randrange(4)):
        rows = tuple(''.join(dict(U='R', R='D', D='L', L='U', **{'.': '.'})[rows[reference.size-1-c][r]]
                             for c in range(reference.size)) for r in range(reference.size))
    if rng.choice((False, True)):
        rows = tuple(row[::-1].translate(str.maketrans('LR', 'RL')) for row in rows)
    return Level(round_number, f'无尽挑战 · 第 {round_number} 关', f'难度 {tier}/6', rows,
                 '随机棋盘，沿箭头方向观察阻挡。每关恢复三次机会。')
