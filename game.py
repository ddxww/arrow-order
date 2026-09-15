"""Playable Arrow Order game.

Run with ``python game.py`` after installing pygame-ce. The earlier
``preview.py`` remains a static visual review tool.
"""
from __future__ import annotations

import array
import json
import math
import os
import sys
import time
from pathlib import Path

import pygame

from arrowgame.levels import LEVELS
from arrowgame.preview_ui import Painter, BG, INK, MUTED, ACCENT, PALE, LINE, WHITE, ORANGE, RED
from arrowgame.rules import can_exit, first_blocker

SIZE = (960, 800)
FPS = 60


def progress_path() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home())) / "ArrowOrder"
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root / "progress.json"
    except OSError:
        return Path.cwd() / ".arrow_order_progress.json"


class SoundKit:
    def __init__(self):
        self.enabled = True
        self.music_enabled = True
        self.sounds = {}
        self.music = None
        self.music_channel = None
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)
            for name, freq, duration in (("click", 540, .06), ("fly", 760, .13), ("hit", 170, .12), ("win", 880, .22)):
                samples = array.array("h")
                total = int(22050 * duration)
                for i in range(total):
                    envelope = min(1, i / 300, (total - i) / 1000)
                    samples.append(int(11000 * envelope * math.sin(2 * math.pi * freq * i / 22050)))
                self.sounds[name] = pygame.mixer.Sound(buffer=samples.tobytes())
            self.music = self._make_music()
        except pygame.error:
            self.enabled = False
            self.music_enabled = False

    @staticmethod
    def _make_music():
        """Build an original, gently looping background track in memory."""
        sample_rate, bpm, bars = 22050, 92, 8
        beat = 60 / bpm
        total = int(sample_rate * beat * 4 * bars)
        mix = [0.0] * total
        chords = ((261.63, 329.63, 392.00), (220.00, 261.63, 329.63),
                  (174.61, 220.00, 261.63), (196.00, 246.94, 293.66))
        melody = (659.25, 0, 523.25, 587.33, 659.25, 0, 783.99, 659.25,
                  523.25, 0, 440.00, 523.25, 587.33, 0, 523.25, 392.00)

        def add_note(frequency, start, duration, volume, fade=.12):
            first = int(start * sample_rate)
            count = min(int(duration * sample_rate), total - first)
            edge = max(1, int(fade * sample_rate))
            for i in range(count):
                envelope = min(1.0, i / edge, (count - i) / edge)
                mix[first + i] += volume * envelope * math.sin(2 * math.pi * frequency * i / sample_rate)

        for bar in range(bars):
            start = bar * 4 * beat
            for frequency in chords[bar % len(chords)]:
                add_note(frequency / 2, start, 4 * beat, .105, .35)
            add_note(chords[bar % len(chords)][0], start, 4 * beat, .035, .4)
        for step in range(bars * 2):
            frequency = melody[step % len(melody)]
            if frequency:
                add_note(frequency, step * 2 * beat, 1.55 * beat, .075, .08)

        samples = array.array("h", (int(max(-1, min(1, value)) * 32767) for value in mix))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        self.enabled = not self.enabled

    def start_music(self):
        if self.music_enabled and self.music and (not self.music_channel or not self.music_channel.get_busy()):
            self.music_channel = self.music.play(loops=-1, fade_ms=700)

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            self.start_music()
        elif self.music_channel:
            self.music_channel.fadeout(350)


class Game:
    def __init__(self, data_dir=None):
        pygame.init()
        pygame.display.set_caption("箭序 · 一箭又一箭")
        self.screen = pygame.display.set_mode(SIZE, pygame.RESIZABLE)
        self.painter = Painter()
        self.sound = SoundKit()
        self.scene = "home"
        self.level_index = 0
        self.board = []
        self.mistakes = 3
        self.hints = 3
        self.animation = None
        self.feedback = "选择一支箭头，让它沿方向飞出去。"
        self.feedback_color = MUTED
        self.hover = None
        self.highlight = None
        self.hint_active = False
        self.unlocked = 1
        self.best = {}
        self.regions = []
        self.progress_file = Path(data_dir) / "progress.json" if data_dir is not None else progress_path()
        self.storage_message = ""
        self.load_progress()
        self.sound.start_music()

    def load_progress(self):
        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            self.unlocked = max(1, min(len(LEVELS), int(data.get("unlocked", 1))))
            raw_best = data.get("best", {})
            self.best = {str(k): v for k, v in raw_best.items() if str(k).isdigit() and 0 <= int(k) < len(LEVELS) and isinstance(v, dict) and type(v.get("mistakes")) is int and 0 <= v["mistakes"] <= 2 and type(v.get("hints")) is int and 0 <= v["hints"] <= 3} if isinstance(raw_best, dict) else {}
            self.sound.enabled = bool(data.get("sound", True))
            self.sound.music_enabled = bool(data.get("music", True)) and self.sound.music is not None
        except FileNotFoundError:
            self.unlocked, self.best = 1, {}
        except (OSError, ValueError, TypeError, AttributeError):
            self.unlocked, self.best = 1, {}
            self.storage_message = "存档无法读取，已恢复默认进度。"

    def save_progress(self):
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.progress_file.with_suffix(".tmp")
            temporary.write_text(json.dumps({"unlocked": self.unlocked, "best": self.best, "sound": self.sound.enabled, "music": self.sound.music_enabled}, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.progress_file)
        except OSError:
            self.storage_message = "进度暂未保存，本次游戏仍可继续。"

    def reset_level(self, index=None):
        if index is not None:
            self.level_index = max(0, min(len(LEVELS) - 1, index))
        level = LEVELS[self.level_index]
        self.board = [list(row) for row in level.rows]
        self.mistakes, self.hints = 3, 3
        self.animation, self.highlight, self.hover = None, None, None
        self.hint_active = False
        self.feedback, self.feedback_color = "选择一支箭头，让它沿方向飞出去。", MUTED
        self.scene = "playing"

    def count_arrows(self):
        return sum(cell != "." for row in self.board for cell in row)

    def set_layout(self):
        sw, sh = self.screen.get_size()
        scale = min(sw / SIZE[0], sh / SIZE[1])
        return scale, ((sw - SIZE[0] * scale) / 2, (sh - SIZE[1] * scale) / 2)

    def logical_point(self, point):
        scale, offset = self.set_layout()
        return ((point[0] - offset[0]) / scale, (point[1] - offset[1]) / scale)

    def button(self, label, rect, action, primary=False, enabled=True):
        self.painter.button(label, rect, action, primary, enabled)
        if enabled:
            self.regions.append((pygame.Rect(rect), action))

    def draw_header_footer(self):
        self.painter.header()
        self.painter.footer()
        self.painter.box((731, 27, 89, 36), BG, 12)
        self.button("音乐 开" if self.sound.music_enabled else "音乐 关", (731, 27, 89, 36), "music")
        self.painter.box((831, 27, 89, 36), BG, 12)
        self.button("音效 开" if self.sound.enabled else "音效 关", (831, 27, 89, 36), "sound")

    def draw_home(self):
        p = self.painter
        p.text("A LITTLE ORDER. A LITTLE JOY.", 76, 153, 12, ACCENT)
        p.text("一箭又一箭", 72, 195, 57)
        p.text("让每一箭，找到自己的出口。", 77, 290, 22, ACCENT)
        p.text("沿着方向，解开阻挡。", 78, 343, 17, MUTED)
        p.text("六段小小挑战，留一点时间给思考。", 78, 375, 17, MUTED)
        self.button("开始游戏   →", (76, 431, 208, 54), "start", True)
        self.button("选择关卡", (299, 431, 136, 54), "levels")
        p.pill("6 个关卡", (78, 509, 91, 28), size=12)
        p.pill("3 次机会", (181, 509, 91, 28), size=12)
        p.pill("3 次提示", (284, 509, 91, 28), size=12)
        p.board(552, 192, 59, highlight=(0, 1))
        p.pill("从一支畅通的箭头开始", (581, 520, 231, 34), "#F5E9D8", ORANGE)
        cards = (("01", "观察方向", "箭头只能沿自身方向飞出。"), ("02", "解除阻挡", "先送走挡在前面的箭头。"), ("03", "清空棋盘", "用三次机会，找到通关顺序。"))
        for i, (num, title, body) in enumerate(cards):
            x = 64 + i * 283
            p.box((x, 602, 266, 103), WHITE, 16, LINE)
            p.text(num, x + 19, 622, 14, ORANGE)
            p.text(title, x + 55, 622, 18)
            p.text(body, x + 19, 663, 13, MUTED)
        if self.storage_message:
            p.text(self.storage_message, 480, 717, 12, RED, center=True)

    def draw_levels(self):
        p = self.painter
        p.text("一点点，解开所有方向。", 64, 127, 34)
        p.text("六个关卡 · 循序渐进 · 已通关的关卡可以随时重玩", 65, 186, 15, MUTED)
        for i, level in enumerate(LEVELS):
            x, y = 64 + i % 3 * 283, 241 + i // 3 * 212
            unlocked = i < self.unlocked
            completed = str(i) in self.best
            p.box((x, y, 266, 187), WHITE if unlocked else "#F0EDF3", 20, ACCENT if unlocked and i == self.level_index else LINE)
            p.text(f"0{i + 1}", x + 23, y + 23, 33, ACCENT if unlocked else "#AAA2BA")
            p.pill("已完成" if completed else "可挑战" if unlocked else "待解锁", (x + 164, y + 24, 80, 28), PALE, ACCENT if unlocked else MUTED, 12)
            p.text(level.name, x + 23, y + 80, 22, INK if unlocked else MUTED)
            p.text(f"{level.difficulty}   ·   {len(level.rows)} × {len(level.rows)}", x + 24, y + 118, 13, MUTED)
            record = self.best.get(str(i))
            p.text(f"最佳：{record['mistakes']} 失误 · {record['hints']} 提示" if record else "点击开始挑战" if unlocked else f"完成第 {i} 关后解锁", x + 24, y + 151, 12, ACCENT if unlocked else MUTED)
            if unlocked:
                self.regions.append((pygame.Rect(x, y, 266, 187), ("level", i)))
        self.button("返回首页", (64, 669, 140, 44), "home")
        p.text("进度会自动保存在这台电脑上。", 630, 686, 13, MUTED)

    def board_geometry(self):
        n = len(self.board)
        cell = 390 / n
        return 285, 243, cell

    def draw_playing(self):
        p = self.painter
        level = LEVELS[self.level_index]
        p.text(f"关卡 {self.level_index + 1:02d} / {len(LEVELS):02d}     ·     {level.difficulty}", 64, 108, 13, ACCENT)
        p.text(level.name, 63, 143, 33)
        p.text(level.tip, 65, 194, 15, MUTED)
        p.box((562, 110, 149, 83), WHITE, 16, LINE)
        p.text("剩余箭头", 580, 124, 12, MUTED)
        p.text(str(self.count_arrows()), 580, 150, 26)
        p.text("支", 623, 161, 12, MUTED)
        p.box((726, 110, 170, 83), WHITE, 16, LINE)
        p.text("剩余机会", 744, 124, 12, MUTED)
        for i in range(3):
            p.circle((754 + i * 26, 166), 8, "#DEDAE5" if i >= self.mistakes else "#B19ACE")
        p.text(f"{self.mistakes} / 3", 833, 159, 13, MUTED)
        x, y, cell = self.board_geometry()
        rows = [row[:] for row in self.board]
        highlight = self.highlight or self.hover
        if self.animation and self.animation["kind"] == "fly":
            rows[self.animation["row"]][self.animation["col"]] = "."
        p.board(x, y, cell, rows=rows, highlight=None)
        for position, color in ((highlight, ORANGE if self.hint_active else ACCENT),):
            if position and self.board[position[0]][position[1]] != "." and not self.animation:
                r, c = position
                p.box((x+c*cell+4, y+r*cell+4, cell-8, cell-8), "#FAEEDD" if self.hint_active else "#E5DFF4", 12, color, 2)
                p.arrow((x+(c+.5)*cell,y+(r+.5)*cell), self.board[r][c], cell*.39, color, 4)
        if self.animation and self.animation["kind"] == "collision":
            a = self.animation
            elapsed = min(1, (time.monotonic()-a["start"])/a["duration"])
            for position in ((a["row"], a["col"]), a["blocker"]):
                if position:
                    r,c = position
                    p.box((x+c*cell+4,y+r*cell+4,cell-8,cell-8),"#F9E6ED",12,RED,2)
                    dr,dc={"U":(-1,0),"D":(1,0),"L":(0,-1),"R":(0,1)}[self.board[r][c]]
                    shift = 7*math.sin(elapsed*math.pi) if position == (a["row"],a["col"]) else 0
                    p.arrow((x+(c+.5)*cell+dc*shift,y+(r+.5)*cell+dr*shift), self.board[r][c],cell*.39,RED,4)
        # Animate the moving arrow over the static board.
        if self.animation and self.animation["kind"] == "fly":
            a = self.animation
            progress = min(1.0, (time.monotonic() - a["start"]) / a["duration"])
            dr, dc = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}[a["direction"]]
            distance = {"U":(a["row"]+1)*cell+32,"D":(len(rows)-a["row"])*cell+32,"L":(a["col"]+1)*cell+32,"R":(len(rows)-a["col"])*cell+32}[a["direction"]]
            cx = x + a["col"] * cell + cell / 2 + dc * progress * distance
            cy = y + a["row"] * cell + cell / 2 + dr * progress * distance
            p.arrow((cx, cy), a["direction"], cell * .39, ACCENT, 4)
        p.text(self.feedback, 480, 658, 14, self.feedback_color, center=True)
        self.button(f"提示  {self.hints} / 3", (264, 693, 146, 38), "hint", enabled=self.hints > 0 and self.animation is None and not self.hint_active)
        self.button("重新开始", (421, 693, 146, 38), "restart")
        self.button("返回选关", (578, 693, 118, 38), "levels")

    def draw_result(self):
        kind = self.scene
        p = self.painter
        # Draw a dimmed board background, then lock all board input behind modal.
        self.draw_playing()
        self.regions.clear()
        shade = pygame.Surface(p.canvas.get_size(), pygame.SRCALPHA)
        shade.fill((53, 45, 75, 83))
        p.canvas.blit(shade, (0, 0))
        p.box((240, 189, 480, 424), WHITE, 26)
        failed = kind == "fail"
        p.circle((480, 260), 31, "#F9E6ED" if failed else PALE)
        if failed:
            p.text("!", 480, 242, 36, RED, center=True)
        else:
            p.line((467, 260), (477, 270), ACCENT, 4); p.line((477, 270), (494, 249), ACCENT, 4)
        title = "这一次，差一点点" if failed else "六关完成，箭箭有序" if kind == "complete" else f"{LEVELS[self.level_index].name}，顺利解开！"
        subtitle = "三次机会已用完。换个顺序，再试一次。" if failed else "谢谢你，把每一支箭头送往了出口。" if kind == "complete" else "每解除一个阻挡，就离出口更近一步。"
        p.text(title, 480, 317, 29, INK, center=True); p.text(subtitle, 480, 370, 15, MUTED, center=True)
        p.box((287, 410, 386, 62), "#F1EDF8", 13)
        p.text(f"失误   {3 - self.mistakes} / 3", 322, 434, 16, RED if failed else ACCENT); p.line((480, 425), (480, 458)); p.text(f"提示   {3 - self.hints} / 3", 520, 434, 16, ACCENT)
        if failed:
            self.button("再试一次", (287, 494, 386, 49), "restart", True)
            self.button("返回首页", (287, 557, 186, 34), "home"); self.button("返回选关", (487, 557, 186, 34), "levels")
        elif kind == "complete":
            self.button("从第一关重玩", (287, 494, 386, 49), "first", True)
            self.button("返回首页", (287, 557, 186, 34), "home"); self.button("返回选关", (487, 557, 186, 34), "levels")
        else:
            self.button("下一关   →", (287, 494, 386, 49), "next", True)
            self.button("重玩本关", (287, 557, 186, 34), "restart"); self.button("返回选关", (487, 557, 186, 34), "levels")

    def render(self):
        self.painter.canvas.fill(BG); self.painter.buttons.clear(); self.painter.text_bounds.clear(); self.regions.clear(); self.draw_header_footer()
        if self.scene == "home": self.draw_home()
        elif self.scene == "levels": self.draw_levels()
        elif self.scene == "playing": self.draw_playing()
        else: self.draw_result()
        return pygame.transform.smoothscale(self.painter.canvas, SIZE)

    def board_cell(self, point):
        x, y, cell = self.board_geometry(); n = len(self.board)
        outer = pygame.Rect(x - 18, y - 18, cell * n + 36, cell * n + 36)
        if not outer.collidepoint(point): return None
        col, row = int((point[0] - x) // cell), int((point[1] - y) // cell)
        return (row, col) if 0 <= row < n and 0 <= col < n else None

    def click(self, point):
        for rect, action in reversed(self.regions):
            if rect.collidepoint(point):
                self.action(action); return
        if self.scene == "playing" and self.animation is None:
            cell = self.board_cell(point)
            if cell and self.board[cell[0]][cell[1]] != ".": self.select_arrow(*cell)

    def select_arrow(self, row, col):
        if can_exit(self.board, row, col):
            self.sound.play("click"); direction = self.board[row][col]
            self.animation = {"kind":"fly", "row":row, "col":col, "direction":direction, "start":time.monotonic(), "duration":.32}
            self.feedback, self.feedback_color = "飞出棋盘……", ACCENT
        else:
            self.sound.play("hit"); self.mistakes -= 1
            self.animation = {"kind":"collision", "row":row, "col":col, "blocker":first_blocker(self.board,row,col), "start":time.monotonic(), "duration":.26}
            self.highlight = (row, col); self.feedback, self.feedback_color = "前方有箭头挡住了，先解除阻挡吧。", RED

    def action(self, action):
        self.sound.play("click")
        if action == "sound": self.sound.toggle(); self.save_progress()
        elif action == "music": self.sound.toggle_music(); self.save_progress()
        elif action == "start": self.reset_level(next((i for i in range(len(LEVELS)) if str(i) not in self.best), 0))
        elif action == "levels": self.scene, self.animation = "levels", None
        elif action == "home": self.scene, self.animation = "home", None
        elif action == "restart": self.reset_level()
        elif action == "hint" and self.hints > 0 and self.animation is None and not self.hint_active:
            options = [(r, c) for r in range(len(self.board)) for c in range(len(self.board)) if self.board[r][c] != "." and can_exit(self.board, r, c)]
            if options:
                self.hints -= 1; self.highlight = options[0]; self.hint_active = True; self.feedback, self.feedback_color = "金色箭头前方畅通，可以先点击它。", ORANGE
        elif action == "next": self.reset_level(self.level_index + 1)
        elif action == "first": self.reset_level(0)
        elif isinstance(action, tuple) and action[0] == "level": self.reset_level(action[1])

    def update(self):
        if not self.animation: return
        if time.monotonic() - self.animation["start"] < self.animation["duration"]: return
        a = self.animation; self.animation = None
        if a["kind"] == "fly":
            self.board[a["row"]][a["col"]] = "."; self.sound.play("fly"); self.highlight = None; self.hint_active = False
            if self.count_arrows() == 0:
                record = {"mistakes": 3 - self.mistakes, "hints": 3 - self.hints}
                old = self.best.get(str(self.level_index))
                if old is None or (record["mistakes"], record["hints"]) < (old["mistakes"], old["hints"]): self.best[str(self.level_index)] = record
                self.unlocked = min(len(LEVELS), max(self.unlocked, self.level_index + 2)); self.save_progress(); self.sound.play("win")
                self.scene = "complete" if self.level_index == len(LEVELS) - 1 else "win"
            else: self.feedback = "很好，继续观察下一支畅通的箭头。"
        elif self.mistakes <= 0:
            self.scene = "fail"

    def run(self):
        clock = pygame.time.Clock(); running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: running = False
                    elif event.key == pygame.K_r and self.scene == "playing": self.reset_level()
                elif event.type == pygame.VIDEORESIZE: self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.MOUSEMOTION and self.scene == "playing" and self.animation is None: self.hover = self.board_cell(self.logical_point(event.pos))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.click(self.logical_point(event.pos))
            self.update(); frame = self.render(); sw, sh = self.screen.get_size(); scale = min(sw / SIZE[0], sh / SIZE[1]); fitted = (round(SIZE[0]*scale), round(SIZE[1]*scale)); offset=((sw-fitted[0])//2,(sh-fitted[1])//2); self.screen.fill("#EBE5F0"); self.screen.blit(pygame.transform.smoothscale(frame, fitted), offset); pygame.display.flip(); clock.tick(FPS)
        self.save_progress(); pygame.quit()


def main():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    Game().run()


if __name__ == "__main__": main()
