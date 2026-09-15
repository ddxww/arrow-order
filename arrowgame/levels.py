"""Six handcrafted, immutable and solver-verified Arrow Order levels."""
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from .rules import solve_order, validate_board

@dataclass(frozen=True)
class Level:
    number: int
    name: str
    difficulty: str
    rows: tuple[str, ...]
    tip: str
    @property
    def size(self) -> int: return len(self.rows)
    @property
    def layout(self) -> tuple[tuple[str, ...], ...]: return tuple(tuple(row) for row in self.rows)
    @property
    def arrows(self) -> int: return sum(cell != "." for row in self.rows for cell in row)
    @property
    def solution(self) -> tuple[tuple[int, int], ...]:
        order = solve_order(self.layout)
        if order is None: raise ValueError(f"level {self.number} is unsolvable")
        return order
    @property
    def hint(self) -> str: return self.tip
    def fresh_board(self) -> list[list[str]]: return [list(row) for row in self.rows]

_RAW_LEVELS = (
    ("初识箭序", "入门", ("U.U.U", ".....", "L.U.R", ".....", "D.D.D"), "先处理四个边缘箭头，再观察中间的纵向箭头。"),
    ("留意空隙", "入门", ("..D.D", "RD..D", "L.RU.", ".RD..", ".L..L"), "箭头之间隔着空格也会形成阻挡，沿整条路径仔细检查。"),
    ("交错之间", "进阶", ("DLDLLL", "....DD", "D.L...", "...RDD", ".UR.D.", "L.D..R"), "横向与纵向依赖交错，优先寻找当前没有阻挡的箭头。"),
    ("逐一解锁", "进阶", ("D.DRDD", ".D.LLD", "DLL.L.", "..DUD.", "L.D.LL", "L...LR"), "一条路线清空后，另一条路线才会逐步打开。"),
    ("四向交织", "挑战", ("R.DD...", "R.D.D..", "UDD..DD", "U.DDDLD", "..DL.LL", "..DL.LD", ".DDLLLD"), "四个方向的长路径互相交错，先拆掉外圈再进入中心。"),
    ("最后之序", "挑战", ("D.LLL.D", "..UL..L", ".RUURDD", "D..LLLL", "..UU.LL", ".RUURDD", "LRDRRDR"), "最终关综合考验远距离阻挡与四向判断，保持耐心逐步清理。"),
)

def _build_levels() -> tuple[Level, ...]:
    result = []
    for number, (name, difficulty, rows, tip) in enumerate(_RAW_LEVELS, 1):
        layout = tuple(tuple(row) for row in rows)
        validate_board(layout, require_all_directions=True)
        result.append(Level(number, name, difficulty, tuple(rows), tip))
    return tuple(result)

LEVELS = _build_levels()
LEVELS_BY_NUMBER = MappingProxyType({level.number: level for level in LEVELS})

def get_level(number: int) -> Level:
    try: return LEVELS_BY_NUMBER[number]
    except KeyError as exc: raise ValueError(f"unknown level: {number}") from exc

__all__ = ["Level", "LEVELS", "LEVELS_BY_NUMBER", "get_level"]
