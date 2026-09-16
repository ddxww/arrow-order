"""Pygame-drawn first-checkpoint screens; no gameplay is implemented here.

Everything is drawn at twice the logical resolution, then downsampled for
smooth edges. The same logical coordinates can be reused by the game UI.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import pygame

ROOT = Path(__file__).resolve().parents[1]
SIZE = (960, 800)
SCENES = ("home", "levels", "game", "hint", "collision", "win", "fail", "complete")
SCENE_NAMES = ("开始界面", "关卡选择", "游戏界面", "提示效果", "碰撞反馈", "单关通关", "挑战失败", "全部通关")
BG = "#000000"
PANEL = "#17161B"
INK = "#F5F4F7"
MUTED = "#B7B3C2"
ACCENT = "#A99AE8"
CYAN = "#65D6D0"
GOLD = "#F3C969"
PINK = "#EF719D"
PALE = "#24202E"
LINE = "#403A49"
WHITE = "#FFFFFF"
ORANGE = "#F0B45A"
RED = "#F26A83"
# Direction colors: left red, down yellow, right blue, and up green.
DIRECTION_COLORS = {"L": "#D94B5B", "D": "#E0A62B", "R": "#3F78C5", "U": "#4AA36B"}
DEMO_BOARD = (".U.RD", "U.L.D", ".RD.L", "D.U.L", "L.R.R")


@dataclass
class Button:
    name: str
    rect: pygame.Rect
    target: str


class Painter:
    def __init__(self):
        if not pygame.font.get_init():
            pygame.font.init()
        self.canvas = pygame.Surface((1920, 1600), pygame.SRCALPHA)
        self.font_path = ROOT / "assets" / "fonts" / "ArrowOrder-Regular.ttf"
        self.bold_path = ROOT / "assets" / "fonts" / "ArrowOrder-Semibold.ttf"
        if not self.font_path.exists():
            raise FileNotFoundError("缺少随项目分发的字体，请检查 assets/fonts 目录")
        self.fonts = {}
        self.buttons = []
        self.text_bounds = []

    @staticmethod
    def rect_scaled(rect):
        return pygame.Rect(*(round(v * 2) for v in rect))

    def box(self, rect, fill, radius=16, border=None, width=1):
        r = self.rect_scaled(rect)
        pygame.draw.rect(self.canvas, fill, r, border_radius=radius * 2)
        if border:
            pygame.draw.rect(self.canvas, border, r, width * 2, border_radius=radius * 2)

    def glow(self, rect, color=ACCENT, radius=16, alpha=24, spread=8):
        """Add a quiet halo behind an important panel without changing its hitbox."""
        x, y, w, h = rect
        layer = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
        glow_color = pygame.Color(color)
        glow_color.a = alpha
        pygame.draw.rect(layer, glow_color, self.rect_scaled((x-spread, y-spread, w+spread*2, h+spread*2)), border_radius=(radius+spread)*2)
        self.canvas.blit(layer, (0, 0))

    def background(self):
        """Subtle HUD grid keeps the black theme dimensional and calm."""
        for x in range(40, 921, 48):
            self.line((x, 76), (x, 726), "#0D1117")
        for y in range(92, 727, 48):
            self.line((40, y), (920, y), "#0D1117")
        for x, y, dx, dy in ((40, 76, 18, 0), (40, 76, 0, 18), (920, 726, -18, 0), (920, 726, 0, -18)):
            self.line((x, y), (x + dx, y + dy), CYAN, 1)

    def progress_bar(self, rect, value, color=CYAN, track=PALE):
        x, y, w, h = rect
        self.box(rect, track, radius=h // 2)
        if value > 0:
            self.box((x, y, max(h, w * max(0.0, min(1.0, value))), h), color, radius=h // 2)

    def stat_chip(self, label, value, rect, color=ACCENT):
        self.box(rect, PANEL, 12, LINE)
        self.text(label.upper(), rect[0] + 12, rect[1] + 9, 9, MUTED)
        self.text(value, rect[0] + 12, rect[1] + 24, 17, color)

    def line(self, a, b, color=LINE, width=1):
        pygame.draw.line(self.canvas, color, (a[0] * 2, a[1] * 2), (b[0] * 2, b[1] * 2), width * 2)

    def circle(self, center, radius, color, width=0):
        pygame.draw.circle(self.canvas, color, (round(center[0] * 2), round(center[1] * 2)), round(radius * 2), width * 2)

    def github_icon(self, center, size=18, color=ACCENT):
        """Small monochrome GitHub mark drawn without an external asset."""
        cx, cy = center
        self.circle((cx, cy), size, color)
        # Cat ears and head in the familiar GitHub mark silhouette.
        points = [(cx-size*.64, cy-size*.25), (cx-size*.54, cy-size*.78),
                  (cx-size*.12, cy-size*.55), (cx+size*.12, cy-size*.55),
                  (cx+size*.54, cy-size*.78), (cx+size*.64, cy-size*.25),
                  (cx+size*.52, cy+size*.50), (cx+size*.33, cy+size*.72),
                  (cx-size*.33, cy+size*.72), (cx-size*.52, cy+size*.50)]
        pygame.draw.polygon(self.canvas, WHITE, [(round(x*2), round(y*2)) for x,y in points])
        self.circle((cx-size*.2, cy-size*.06), size*.1, color)
        self.circle((cx+size*.2, cy-size*.06), size*.1, color)
        pygame.draw.line(self.canvas, color, (round(cx*2), round((cy+size*.04)*2)), (round(cx*2), round((cy+size*.28)*2)), 2)

    def text(self, value, x, y, size=18, color=INK, center=False):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(str(self.bold_path if size >= 22 else self.font_path), size * 2)
        glyph = self.fonts[size].render(str(value), True, color)
        bounds = glyph.get_bounding_rect()
        # Ignore the font's large invisible ascender/descender margins.
        if not bounds.width:
            return
        glyph = glyph.subsurface(bounds)
        px = round(x * 2 - glyph.get_width() / 2) if center else round(x * 2)
        self.canvas.blit(glyph, (px, round(y * 2)))
        self.text_bounds.append((str(value), pygame.Rect(px // 2, int(y), math.ceil(glyph.get_width() / 2), math.ceil(glyph.get_height() / 2))))

    def arrow(self, center, direction="R", size=24, color=None, width=4):
        if color is None:
            color = DIRECTION_COLORS[direction]
        dr, dc = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}[direction]
        x, y = center
        length = size / 2
        tail = (x - dc * length, y - dr * length)
        head = (x + dc * length, y + dr * length)
        wing1 = (head[0] - dc * size * .36 + dr * size * .36, head[1] - dr * size * .36 - dc * size * .36)
        wing2 = (head[0] - dc * size * .36 - dr * size * .36, head[1] - dr * size * .36 + dc * size * .36)
        for a, b in ((tail, head), (wing1, head), (wing2, head)):
            self.line(a, b, color, width)
            self.circle(a, width / 2, color)
            self.circle(b, width / 2, color)

    def pill(self, label, rect, bg=PALE, fg=ACCENT, size=13):
        self.box(rect, bg, radius=rect[3] // 2)
        self.text(label, rect[0] + rect[2] / 2, rect[1] + (rect[3] - size) / 2, size, fg, center=True)

    def button(self, label, rect, target, primary=False, enabled=True):
        fill = ACCENT if primary else PANEL
        fg = WHITE if primary else ACCENT
        if not enabled:
            fill, fg = PALE, MUTED
        self.box(rect, fill, 14, None if primary else LINE)
        self.text(label, rect[0] + rect[2] / 2, rect[1] + (rect[3] - 17) / 2, 17, fg, center=True)
        if enabled:
            self.buttons.append(Button(label, pygame.Rect(rect), target))

    def header(self):
        self.glow((40, 28, 34, 34), ACCENT, 11, 35, 5)
        self.box((40, 28, 34, 34), ACCENT, 11)
        self.arrow((57, 45), "R", 18, WHITE, 2)
        self.text("箭序", 86, 31, 24)
        self.line((148, 36), (148, 56))
        self.text("一箭又一箭", 164, 39, 14, MUTED)
        self.pill("●  本地 · 离线", (600, 29, 116, 32), PALE, CYAN)
        self.button("音效 开", (831, 27, 89, 36), "mute")

    def footer(self):
        self.line((40, 742), (920, 742))
        self.text("慢慢观察，每一箭都有出路。", 40, 763, 12, MUTED)
        self.text("ARROW ORDER  /  2026", 727, 764, 11, MUTED)

    def board(self, x, y, cell, rows=DEMO_BOARD, highlight=None, collision=False):
        n = len(rows)
        pad = 18
        extent = cell * n
        self.glow((x - pad, y - pad, extent + pad * 2, extent + pad * 2), CYAN, 24, 16, 7)
        self.box((x - pad + 2, y - pad + 7, extent + pad * 2, extent + pad * 2), "#0B0A0D", 24)
        self.box((x - pad, y - pad, extent + pad * 2, extent + pad * 2), PANEL, 24, LINE)
        for row, values in enumerate(rows):
            for col, direction in enumerate(values):
                tx, ty = x + col * cell, y + row * cell
                selected = (row, col) == highlight
                is_blocker = collision and (row, col) == (0, 4)
                fill = "#3B2D18" if selected and not collision else "#3D202A" if selected or is_blocker else PALE
                self.box((tx + 4, ty + 4, cell - 8, cell - 8), fill, 12)
                if selected or is_blocker:
                    self.box((tx + 4, ty + 4, cell - 8, cell - 8), fill, 12, RED if collision else ORANGE, 2)
                if direction != ".":
                    color = RED if selected and collision else ORANGE if selected else DIRECTION_COLORS[direction]
                    shift = 5 if selected and collision else 0
                    self.arrow((tx + cell / 2 + shift, ty + cell / 2), direction, cell * .39, color, 4 if cell > 50 else 3)
                else:
                    self.circle((tx + cell / 2, ty + cell / 2), 2, "#5A5367")

    def home(self):
        self.pill("PUZZLE SYSTEM  /  READY", (76, 112, 184, 27), "#101A1D", CYAN, 11)
        self.text("A LITTLE ORDER. A LITTLE JOY.", 76, 153, 12, ACCENT)
        self.text("一箭又一箭", 72, 195, 57)
        self.text("让每一箭，找到自己的出口。", 77, 290, 22, ACCENT)
        self.text("沿着方向，解开阻挡。", 78, 343, 17, MUTED)
        self.text("六段小小挑战，留一点时间给思考。", 78, 375, 17, MUTED)
        self.glow((76, 431, 208, 54), ACCENT, 14, 28, 5)
        self.button("开始游戏   →", (76, 431, 208, 54), "game", True)
        self.button("选择关卡", (299, 431, 136, 54), "levels")
        self.pill("6 个关卡", (78, 509, 91, 28), size=12)
        self.pill("3 次机会", (181, 509, 91, 28), size=12)
        self.pill("一点提示", (284, 509, 91, 28), size=12)
        self.board(552, 192, 59, highlight=(0, 1))
        self.text("LIVE BOARD", 552, 173, 10, CYAN)
        self.text("5 × 5  /  15 ARROWS", 689, 173, 10, MUTED)
        self.pill("从一支畅通的箭头开始", (581, 520, 231, 34), "#382B18", ORANGE)
        cards = (("01", "观察方向", "箭头只能沿自身方向飞出。"), ("02", "解除阻挡", "先送走挡在前面的箭头。"), ("03", "清空棋盘", "用三次机会，找到通关顺序。"))
        for i, (num, title, body) in enumerate(cards):
            x = 64 + i * 283
            self.box((x, 602, 266, 103), PANEL, 16, LINE)
            self.text(num, x + 19, 622, 14, ORANGE)
            self.text(title, x + 55, 622, 18)
            self.text(body, x + 19, 663, 13, MUTED)

    def game(self, variant="game"):
        completed = variant in ("win", "complete")
        board_size = 7 if variant == "complete" else 5
        rows = tuple("." * board_size for _ in range(board_size)) if completed else DEMO_BOARD
        mistakes = 0 if variant == "fail" else 2 if variant == "collision" else 3
        self.text("关卡 06 / 06     ·     挑战" if variant == "complete" else "关卡 01 / 06     ·     入门", 64, 108, 13, ACCENT)
        self.text("最后之序" if variant == "complete" else "初识箭序", 63, 143, 33)
        self.text("看清方向，先从畅通的箭头开始。", 65, 194, 15, MUTED)
        self.box((562, 110, 149, 83), PANEL, 16, LINE)
        self.text("BOARD LOAD", 580, 120, 9, CYAN)
        self.text(str(sum(ch != "." for row in rows for ch in row)), 580, 150, 26)
        self.text("支", 623, 161, 12, MUTED)
        self.box((726, 110, 170, 83), PANEL, 16, LINE)
        self.text("RUN STATUS", 744, 120, 9, CYAN)
        self.text("剩余机会", 744, 137, 12, MUTED)
        for i in range(3):
            self.circle((754 + i * 26, 166), 8, "#45414A" if i >= mistakes else "#A99AE8")
        self.text(f"{mistakes} / 3", 833, 159, 13, MUTED)
        highlight = (0, 3) if variant == "collision" else (0, 1) if variant == "hint" else None
        self.board(300, 257, 360 / len(rows), rows=rows, highlight=highlight, collision=variant == "collision")
        self.text("BOARD  /  ACTIVE GRID", 300, 225, 10, CYAN)
        self.text("先看边缘", 65, 333, 18, ACCENT)
        self.line((65, 369), (176, 369))
        self.text("朝向棋盘外的箭头，", 65, 390, 13, MUTED)
        self.text("往往是很好的起点。", 65, 416, 13, MUTED)
        self.circle((799, 409), 24, PALE)
        self.arrow((799, 409), "U", 23)
        self.text("不着急", 773, 454, 15, ACCENT)
        self.text("每一步都算数", 759, 483, 12, MUTED)
        message = "点击一支箭头，试着让它飞出去。"
        color = MUTED
        if variant == "hint":
            message, color = "试试金色箭头：它的前方没有阻挡。", ORANGE
        elif variant == "collision":
            message, color = "前方有箭头挡住了，先解除阻挡吧。", RED
        self.text(message, 480, 659, 14, color, center=True)
        self.button("提示  2 / 3" if variant in ("hint", "win", "fail", "complete") else "提示  3 / 3", (264, 693, 146, 38), "hint")
        self.button("重新开始", (421, 693, 146, 38), "game")
        self.button("返回选关", (578, 693, 118, 38), "levels")

    def levels(self):
        self.pill("MISSION SELECT", (64, 94, 142, 27), "#101A1D", CYAN, 11)
        self.text("一点点，解开所有方向。", 64, 127, 34)
        self.text("六个关卡 · 循序渐进 · 已通关的关卡可以随时重玩", 65, 186, 15, MUTED)
        names = ("初识箭序", "留意空隙", "交错之间", "逐一解锁", "四向交织", "最后之序")
        for i, name in enumerate(names):
            x, y = 64 + i % 3 * 283, 241 + i // 3 * 212
            unlocked = i < 2
            self.box((x, y, 266, 187), PANEL if unlocked else "#111014", 20, ACCENT if i == 1 else LINE)
            self.text(f"0{i + 1}", x + 23, y + 23, 33, ACCENT if unlocked else "#77717F")
            self.pill("已完成" if i == 0 else "可挑战" if i == 1 else "待解锁", (x + 164, y + 24, 80, 28), PALE, ACCENT if unlocked else MUTED, 12)
            self.text(name, x + 23, y + 80, 22, INK if unlocked else MUTED)
            self.text(f"{('入门', '进阶', '挑战')[i // 2]}   ·   {5 + i // 2} × {5 + i // 2}", x + 24, y + 118, 13, MUTED)
            difficulty = min(5, 2 + i // 2)
            for dot in range(5):
                self.circle((x + 25 + dot * 13, y + 145), 3, GOLD if dot < difficulty else "#343139")
            self.text("最佳：0 失误 · 1 提示" if i == 0 else "准备好了吗？" if i == 1 else f"完成第 {i} 关后解锁", x + 24, y + 151, 12, ACCENT if unlocked else MUTED)
            if unlocked:
                self.buttons.append(Button(name, pygame.Rect(x, y, 266, 187), "game"))
        self.button("返回首页", (64, 669, 140, 44), "home")
        self.text("进度会自动保存在这台电脑上。", 630, 686, 13, MUTED)

    def result(self, kind):
        self.game(kind)
        # Remove the game buttons: results must never click through to a board.
        self.buttons.clear()
        overlay = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((53, 45, 75, 83))
        self.canvas.blit(overlay, (0, 0))
        self.box((240, 197, 480, 424), "#0B0A0D", 26)
        self.box((240, 189, 480, 424), PANEL, 26, LINE)
        failed = kind == "fail"
        self.circle((480, 260), 31, "#3D202A" if failed else PALE)
        if failed:
            self.text("!", 480, 242, 36, RED, center=True)
        else:
            self.line((467, 260), (477, 270), ACCENT, 4)
            self.line((477, 270), (494, 249), ACCENT, 4)
        title = "这一次，差一点点" if failed else "六关完成，箭箭有序" if kind == "complete" else "第一关，顺利解开！"
        self.text(title, 480, 317, 29, INK, center=True)
        subtitle = "三次机会已用完。换个顺序，再试一次。" if failed else "谢谢你，把每一支箭头送往了出口。" if kind == "complete" else "每解除一个阻挡，就离出口更近一步。"
        self.text(subtitle, 480, 370, 15, MUTED, center=True)
        self.box((287, 410, 386, 62), PALE, 13)
        self.text("失误   3 / 3" if failed else "失误   0 / 3", 322, 434, 16, RED if failed else ACCENT)
        self.line((480, 425), (480, 458))
        self.text("提示   1 / 3", 520, 434, 16, ACCENT)
        label = "再试一次" if failed else "从第一关重玩" if kind == "complete" else "下一关   →"
        self.button(label, (287, 494, 386, 49), "game", True)
        self.button("返回选关", (487, 557, 186, 34), "levels")
        self.button("返回首页" if failed or kind == "complete" else "重玩本关", (287, 557, 186, 34), "home" if failed or kind == "complete" else "game")

    def render(self, scene):
        if scene not in SCENES:
            raise ValueError(f"Unknown scene: {scene}")
        self.canvas.fill(BG)
        self.background()
        self.buttons.clear()
        self.text_bounds.clear()
        self.header()
        self.footer()
        if scene == "home":
            self.home()
        elif scene == "levels":
            self.levels()
        elif scene in ("game", "hint", "collision"):
            self.game(scene)
        else:
            self.result(scene)
        return pygame.transform.smoothscale(self.canvas, SIZE)
