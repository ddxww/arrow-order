"""Playable Arrow Order game.

Run with ``python game.py`` after installing pygame-ce. The earlier
``preview.py`` remains a static visual review tool.
"""
from __future__ import annotations

import array
import json
import math
import os
import random
import sys
import time
import webbrowser
from pathlib import Path

import pygame

from arrowgame.levels import LEVELS
from arrowgame.effects import DangerVignette, HEARTBEAT_PERIOD, HEARTBEAT_PULSES
from arrowgame.preview_ui import Painter, BG, PANEL, INK, MUTED, ACCENT, PALE, LINE, WHITE, ORANGE, RED, DIRECTION_COLORS
from arrowgame.rules import can_exit, first_blocker
from arrowgame.scoring import LevelTimer, award_stars, better_record, clean_record, format_time
from arrowgame.endless import generate_level
from arrowgame.cg import AnimatedSticker, load_image

SIZE = (960, 800)
FPS = 60
INTRO_FADE_IN = .6
INTRO_HOLD = 1.0
INTRO_FADE_OUT = .7
INTRO_DURATION = INTRO_FADE_IN + INTRO_HOLD + INTRO_FADE_OUT


def intro_alpha(elapsed):
    """Ease both ends of a full-opacity hold, with no first-frame flash."""
    if elapsed < INTRO_FADE_IN:
        visibility = max(0.0, elapsed / INTRO_FADE_IN)
    else:
        visibility = 1 - max(0.0, (elapsed - INTRO_FADE_IN - INTRO_HOLD) / INTRO_FADE_OUT)
    visibility = max(0.0, min(1.0, visibility))
    return round(255 * visibility * visibility * (3 - 2 * visibility))


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
        self.heartbeat = None
        self.heartbeat_channel = None
        self.heartbeat_started = None
        self.danger = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            sample_rate, sample_format, channels = pygame.mixer.get_init()
            if sample_format != -16:
                raise pygame.error("16-bit signed audio required")
            pygame.mixer.set_reserved(2)
            self.music_channel = pygame.mixer.Channel(0)
            self.heartbeat_channel = pygame.mixer.Channel(1)
            self.heartbeat = self.make_heartbeat(sample_rate, channels)
            for name, freq, duration in (("click", 440, .07), ("fly", 587.33, .16), ("hit", 170, .15)):
                samples = array.array("h")
                total = int(sample_rate * duration)
                for i in range(total):
                    envelope = math.sin(math.pi * i / total) ** 2
                    value = int(4000 * envelope * math.sin(2 * math.pi * freq * i / sample_rate))
                    samples.extend([value] * channels)
                self.sounds[name] = pygame.mixer.Sound(buffer=samples.tobytes())
            self.sounds['win'] = self.make_victory(sample_rate, channels)
        except pygame.error:
            self.enabled = False
            self.music_enabled = False
            return
        try:
            self.music = pygame.mixer.Sound(str(Path(__file__).resolve().parent / "assets" / "audio" / "quiet_afternoon.wav"))
        except (pygame.error, OSError):
            self.music_enabled = False

    @staticmethod
    def make_heartbeat(sample_rate, channels):
        """A rounded double thump with harmonics audible on small speakers."""
        samples = array.array("h")
        for i in range(round(sample_rate * HEARTBEAT_PERIOD)):
            t = i / sample_rate
            value = 0.0
            for start, duration, gain in HEARTBEAT_PULSES:
                local = t - start
                if 0 <= local < duration:
                    envelope = math.sin(math.pi * local / duration) ** 2
                    envelope *= math.exp(-local * 4)
                    # 100 Hz body plus 200/300 Hz warmth survives laptop bass rolloff.
                    phase = 2 * math.pi * (112 * local - 35 * local * local)
                    value += gain * envelope * (math.sin(phase) + .55 * math.sin(2 * phase) + .20 * math.sin(3 * phase))
            samples.extend([round(value * 32767)] * channels)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    @staticmethod
    def make_victory(sample_rate, channels):
        """Original ascending chime with a soft major-chord finish."""
        mix = [0.0] * round(sample_rate * 1.65)
        notes = ((0, 392, .44, .18), (.16, 493.88, .44, .18),
                 (.32, 587.33, .48, .17), (.50, 783.99, .95, .12),
                 (.58, 392, 1.02, .065), (.58, 493.88, 1.02, .065),
                 (.58, 587.33, 1.02, .065))
        for start, frequency, duration, gain in notes:
            first = round(start * sample_rate)
            for i in range(round(duration * sample_rate)):
                t = i / sample_rate
                attack = .5 - .5 * math.cos(math.pi * min(1, t / .025))
                release = .5 - .5 * math.cos(math.pi * min(1, (duration - t) / .3))
                envelope = attack * release * math.exp(-t * 2)
                phase = 2 * math.pi * frequency * t
                mix[first+i] += gain * envelope * (math.sin(phase) + .08 * math.sin(2*phase))
        pcm = array.array('h')
        for value in mix:
            pcm.extend([round(value * 32767)] * channels)
        return pygame.mixer.Sound(buffer=pcm.tobytes())

    def set_danger(self, active):
        if self.danger != active:
            self.danger = active
            self.sync_danger_audio()

    def sync_danger_audio(self):
        if self.music_channel:
            self.music_channel.set_volume(.22 if self.danger else .65)
        if self.heartbeat_channel and self.heartbeat:
            if self.danger and self.music_enabled:
                self.heartbeat_channel.set_volume(.85)
                self.heartbeat_channel.play(self.heartbeat, loops=-1, fade_ms=650)
                self.heartbeat_started = time.monotonic()
            else:
                self.heartbeat_channel.stop()
                self.heartbeat_started = None

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        self.enabled = not self.enabled and bool(self.sounds)

    def start_music(self):
        if self.music_enabled and self.music and self.music_channel:
            self.music_channel.set_volume(.22 if self.danger else .65)
            if self.music_channel.get_sound() == self.music:
                self.music_channel.unpause()
            else:
                self.music_channel.play(self.music, loops=-1, fade_ms=1200)

    def toggle_music(self):
        self.music_enabled = not self.music_enabled and self.music is not None
        if self.music_enabled:
            self.start_music()
        elif self.music_channel:
            self.music_channel.pause()
        self.sync_danger_audio()


class Game:
    def __init__(self, data_dir=None):
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.init()
        pygame.display.set_caption("箭序 · 一箭又一箭")
        self.screen = pygame.display.set_mode(SIZE, pygame.RESIZABLE)
        self.painter = Painter()
        try:
            github_mark = pygame.image.load(str(Path(__file__).resolve().parent / 'assets' / 'images' / 'github_mark.png')).convert_alpha()
            self.github_mark = pygame.transform.smoothscale(github_mark, (44, 44))
        except (pygame.error, OSError):
            self.github_mark = None
        self.timer = LevelTimer()
        self.result_stars = 0
        self.result_record = None
        self.victory_started = None
        self.three_star_panel = self.make_three_star_panel()
        self.mode = 'campaign'
        self.endless_level = None
        self.endless_round = 0
        self.endless_clears = 0
        self.endless_round_cleared = False
        self.endless_reward_shown = False
        self.endless_rng = random.Random()
        self.cg_started = None
        self.cg_wechat = load_image('wechat.jpg', 600)
        self.cg_emoji = load_image('red_envelope.png', 76)
        self.cg_sticker = AnimatedSticker()
        self.danger_effect = DangerVignette(self.painter.canvas.get_size())
        self.fail_overlay = self.make_fail_overlay()
        self.fail_intro_started = None
        self.last_chance_overlay = self.make_last_chance_overlay()
        self.last_chance_started = None
        self.sound = SoundKit()
        self.scene = "home"
        self.level_index = 0
        self.board = []
        self.mistakes = 3
        self.hints = 3
        self.animation = None
        self.auto_solve_queue = None
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
            self.best = {}
            if isinstance(raw_best, dict):
                for key, value in raw_best.items():
                    if str(key).isdigit() and 0 <= int(key) < len(LEVELS):
                        record = clean_record(value, LEVELS[int(key)].target_seconds)
                        if record is not None:
                            self.best[str(int(key))] = record
            self.sound.enabled = bool(data.get("sound", True)) and bool(self.sound.sounds)
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

    @property
    def current_level(self):
        return self.endless_level if self.mode == 'endless' else LEVELS[self.level_index]

    def start_endless(self):
        self.mode = 'endless'
        self.endless_round, self.endless_clears = 0, 0
        self.endless_reward_shown = False
        self.next_endless_level()

    def next_endless_level(self):
        self.endless_round += 1
        self.endless_level = generate_level(self.endless_round, self.endless_rng)
        self.endless_round_cleared = False
        self.reset_level()

    def reset_level(self, index=None):
        if index is not None:
            self.mode = 'campaign'
            self.level_index = max(0, min(len(LEVELS) - 1, index))
        level = self.current_level
        self.board = [list(row) for row in level.rows]
        self.mistakes, self.hints = 3, 3
        self.animation, self.highlight, self.hover = None, None, None
        self.auto_solve_queue = None
        self.fail_intro_started = None
        self.last_chance_started = None
        self.hint_active = False
        self.feedback, self.feedback_color = "选择一支箭头，让它沿方向飞出去。", MUTED
        self.scene = "playing"
        self.timer.reset()
        self.result_stars, self.result_record, self.victory_started = 0, None, None
        self.sync_game_audio()

    def sync_game_audio(self):
        if self.scene == 'playing':
            self.timer.resume()
        else:
            self.timer.pause()
        active = self.mistakes == 1 and self.scene in ("playing", "last_chance")
        self.danger_effect.set_active(active, self.sound.heartbeat_started)
        self.sound.set_danger(active)

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
        self.button("无尽模式   →", (76, 548, 208, 38), "endless")
        p.text("随机关卡 · 三关解锁特殊 CG", 300, 561, 12, MUTED)
        if self.github_mark is not None:
            self.painter.canvas.blit(self.github_mark, (826 * 2, 544 * 2))
        else:
            self.painter.github_icon((848, 566), 21)
        self.regions.append((pygame.Rect((752, 548, 144, 38)), "github"))
        p.pill("6 个关卡", (78, 509, 91, 28), size=12)
        p.pill("3 次机会", (181, 509, 91, 28), size=12)
        p.pill("3 次提示", (284, 509, 91, 28), size=12)
        p.board(552, 192, 59, highlight=(0, 1))
        p.pill("从一支畅通的箭头开始", (581, 520, 231, 34), "#382B18", ORANGE)
        cards = (("01", "观察方向", "箭头只能沿自身方向飞出。"), ("02", "解除阻挡", "先送走挡在前面的箭头。"), ("03", "清空棋盘", "用三次机会，找到通关顺序。"))
        for i, (num, title, body) in enumerate(cards):
            x = 64 + i * 283
            p.box((x, 602, 266, 103), PANEL, 16, LINE)
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
            p.box((x, y, 266, 187), PANEL if unlocked else "#111014", 20, ACCENT if unlocked and i == self.level_index else LINE)
            p.text(f"0{i + 1}", x + 23, y + 23, 33, ACCENT if unlocked else "#77717F")
            p.pill("已完成" if completed else "可挑战" if unlocked else "待解锁", (x + 164, y + 24, 80, 28), PALE, ACCENT if unlocked else MUTED, 12)
            p.text(level.name, x + 23, y + 80, 22, INK if unlocked else MUTED)
            p.text(f"{level.difficulty}   ·   {len(level.rows)} × {len(level.rows)}", x + 24, y + 118, 13, MUTED)
            record = self.best.get(str(i))
            if record and 'stars' in record:
                self.draw_stars(record['stars'], x+56, y+163, 9, 24)
                p.text(f"最佳 {format_time(record['elapsed_ms'])}", x+105, y+156, 12, ACCENT)
            else:
                p.text("已通关 · 重玩获取星级" if record else "点击开始挑战" if unlocked else f"完成第 {i} 关后解锁", x + 24, y + 151, 12, ACCENT if unlocked else MUTED)
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
        level = self.current_level
        heading = f"无尽模式  ·  已通关 {self.endless_clears} 关  ·  {level.difficulty}" if self.mode == 'endless' else f"关卡 {self.level_index + 1:02d} / {len(LEVELS):02d}     ·     {level.difficulty}"
        p.text(heading, 64, 108, 13, ACCENT)
        p.text(level.name, 63, 143, 33)
        p.text(level.tip, 65, 194, 15, MUTED)
        p.box((562, 110, 149, 83), PANEL, 16, LINE)
        p.text("剩余箭头", 580, 124, 12, MUTED)
        p.text(str(self.count_arrows()), 580, 150, 26)
        p.text("支", 623, 161, 12, MUTED)
        p.box((726, 110, 170, 83), PANEL, 16, LINE)
        p.text("剩余机会", 744, 124, 12, MUTED)
        for i in range(3):
            p.circle((754 + i * 26, 166), 8, "#45414A" if i >= self.mistakes else "#A99AE8")
        p.text(f"{self.mistakes} / 3", 833, 159, 13, MUTED)
        p.box((64, 253, 180, 148), PANEL, 16, LINE)
        p.text("本关用时", 82, 273, 13, MUTED)
        p.text(format_time(self.timer.elapsed_ms()), 81, 303, 28, ACCENT)
        if self.mode == 'endless':
            p.text('不限时 · 自由挑战', 82, 363, 13, MUTED)
            p.text('特殊 CG', 66, 435, 17, ACCENT)
            p.text(f'本轮已通关 {self.endless_clears} 关', 66, 471, 13, MUTED)
            p.text('已解锁，继续挑战吧！' if self.endless_reward_shown else f'再通过 {max(0, 3-self.endless_clears)} 关解锁', 66, 503, 13, MUTED)
            p.text('每关恢复 3 次机会', 66, 547, 12, MUTED)
        else:
            p.text(f"速度星目标  {level.target_seconds} 秒", 82, 363, 13, MUTED)
            p.text("三星条件", 66, 435, 17, ACCENT)
            p.text("清空棋盘  +1 星", 66, 471, 13, MUTED)
            p.text("剩余至少 2 次机会", 66, 501, 13, MUTED)
            p.text("再得 1 星", 66, 523, 12, MUTED)
            p.text(f"{level.target_seconds} 秒内完成  +1 星", 66, 556, 13, MUTED)
        x, y, cell = self.board_geometry()
        rows = [row[:] for row in self.board]
        highlight = self.highlight or self.hover
        if self.animation and self.animation["kind"] == "fly":
            rows[self.animation["row"]][self.animation["col"]] = "."
        p.board(x, y, cell, rows=rows, highlight=None)
        highlight_color = ORANGE if self.hint_active else DIRECTION_COLORS.get(self.board[highlight[0]][highlight[1]], ACCENT) if highlight else ACCENT
        for position, color in ((highlight, highlight_color),):
            if position and self.board[position[0]][position[1]] != "." and not self.animation:
                r, c = position
                p.box((x+c*cell+4, y+r*cell+4, cell-8, cell-8), "#3B2D18" if self.hint_active else "#29233A", 12, color, 2)
                p.arrow((x+(c+.5)*cell,y+(r+.5)*cell), self.board[r][c], cell*.39, color, 4)
        if self.animation and self.animation["kind"] == "collision":
            a = self.animation
            elapsed = min(1, (time.monotonic()-a["start"])/a["duration"])
            for position in ((a["row"], a["col"]), a["blocker"]):
                if position:
                    r,c = position
                    p.box((x+c*cell+4,y+r*cell+4,cell-8,cell-8),"#3D202A",12,RED,2)
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
            p.arrow((cx, cy), a["direction"], cell * .39, DIRECTION_COLORS.get(a["direction"], ACCENT), 4)
        p.text(self.feedback, 480, 658, 14, self.feedback_color, center=True)
        auto_active = self.auto_solve_queue is not None
        self.button("自动求解中" if auto_active else "自动求解", (64, 693, 170, 38), "auto_solve",
                    enabled=not auto_active and self.animation is None)
        self.button(f"提示  {self.hints} / 3", (246, 693, 130, 38), "hint",
                    enabled=self.hints > 0 and self.animation is None and not self.hint_active and not auto_active)
        self.button("重新开始", (388, 693, 130, 38), "restart")
        self.button("返回首页" if self.mode == 'endless' else "返回选关", (530, 693, 166, 38),
                    "home" if self.mode == 'endless' else "levels")

    def draw_stars(self, count, center_x, center_y, radius=23, spacing=76):
        for index in range(3):
            cx = center_x + (index - 1) * spacing
            points = []
            for point in range(10):
                angle = -math.pi / 2 + point * math.pi / 5
                r = radius if point % 2 == 0 else radius * .46
                points.append((round((cx + math.cos(angle)*r)*2),
                               round((center_y + math.sin(angle)*r)*2)))
            filled = index < count
            pygame.draw.polygon(self.painter.canvas, '#E4B44C' if filled else '#343139', points)
            pygame.draw.polygon(self.painter.canvas, '#B98A2D' if filled else '#5A5560', points, 2)

    def make_three_star_panel(self):
        try:
            photo = pygame.image.load(str(Path(__file__).resolve().parent / 'assets' / 'images' / 'three_star_cat.jpg')).convert()
        except (pygame.error, OSError):
            return None
        panel = pygame.Surface((520, 744), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL, panel.get_rect(), border_radius=32)
        width = 480
        height = round(width * photo.get_height() / photo.get_width())
        panel.blit(pygame.transform.smoothscale(photo, (width, height)), (20, 20))
        font = pygame.font.Font(str(self.painter.bold_path), 46)
        caption = font.render('三星达成！', True, ACCENT)
        caption = caption.subsurface(caption.get_bounding_rect())
        panel.blit(caption, ((520-caption.get_width())//2, 666))
        return panel

    def draw_win_result(self):
        if self.mode == 'endless':
            self.draw_endless_win()
            return
        p = self.painter
        celebrated = self.result_stars == 3 and self.three_star_panel is not None
        x = 64 if celebrated else 206
        center = x + 274
        p.box((x, 170, 548, 460), PANEL, 26, LINE)
        title = '六关完成，箭箭有序' if self.scene == 'complete' else f'{LEVELS[self.level_index].name}，顺利解开！'
        p.text(title, center, 201, 27, INK, center=True)
        p.text('三星到手，这次真的强！' if self.result_stars == 3 else '再快一点、稳一点，挑战三颗星。', center, 246, 15, MUTED, center=True)
        self.draw_stars(self.result_stars, center, 304)
        fast = self.timer.elapsed_ms() <= LEVELS[self.level_index].target_seconds * 1000
        for i, (label, earned) in enumerate((('通关 +1 星', True), ('机会 +1 星', self.mistakes >= 2), ('速度 +1 星', fast))):
            p.pill(label if earned else label.replace('+1', '+0'), (x+35+i*162, 349, 154, 29), '#382B18' if earned else PALE, ORANGE if earned else MUTED, 12)
        p.text(f'用时 {format_time(self.timer.elapsed_ms())}   ·   目标 {LEVELS[self.level_index].target_seconds} 秒', center, 398, 17, ACCENT, center=True)
        p.text(f'剩余机会 {self.mistakes} / 3   ·   使用提示 {3-self.hints} / 3', center, 432, 14, MUTED, center=True)
        if self.scene == 'complete':
            self.button('从第一关重玩', (x+35, 487, 478, 49), 'first', True)
        else:
            self.button('下一关   →', (x+35, 487, 478, 49), 'next', True)
        self.button('重玩本关', (x+35, 554, 231, 38), 'restart')
        self.button('返回选关', (x+282, 554, 231, 38), 'levels')
        if celebrated:
            progress = min(1.0, max(0.0, (time.monotonic() - self.victory_started) / .6)) if self.victory_started is not None else 1.0
            self.three_star_panel.set_alpha(round(255 * progress * progress * (3-2*progress)))
            p.canvas.blit(self.three_star_panel, (640*2, 211*2))

    def draw_endless_win(self):
        p = self.painter
        p.box((206, 170, 548, 460), PANEL, 26, LINE)
        p.text(f'第 {self.endless_round} 关，顺利通过！', 480, 217, 29, INK, center=True)
        p.text(f'本轮已通关 {self.endless_clears} 关', 480, 284, 25, ACCENT, center=True)
        message = '特殊 CG 已解锁，继续挑战更多关卡。' if self.endless_reward_shown else f'再通过 {3-self.endless_clears} 关，解锁特殊 CG。'
        p.text(message, 480, 339, 16, MUTED, center=True)
        p.text(f'本关用时 {format_time(self.timer.elapsed_ms())}   ·   剩余机会 {self.mistakes} / 3', 480, 396, 16, ACCENT, center=True)
        self.button('继续挑战   →', (241, 474, 478, 49), 'endless_next', True)
        if self.endless_reward_shown:
            self.button('查看特殊 CG', (241, 547, 231, 38), 'show_cg')
            self.button('返回首页', (488, 547, 231, 38), 'home')
        else:
            self.button('返回首页', (241, 547, 478, 38), 'home')

    def draw_endless_cg(self):
        p = self.painter
        elapsed = max(0.0, time.monotonic() - self.cg_started)
        fade = min(1.0, elapsed / .6)
        alpha = round(255 * fade * fade * (3-2*fade))
        p.text('无尽模式', 64, 111, 31)
        p.text(f'本轮已通关 {self.endless_clears} 关，恭喜解锁！可以截图保存这份通关纪念。', 65, 161, 15, MUTED)
        p.box((64, 192, 832, 486), PANEL, 23, LINE)
        if self.cg_wechat is not None:
            self.cg_wechat.set_alpha(alpha)
            p.canvas.blit(self.cg_wechat, (88*2, 210*2))
        else:
            p.text('微信图片未找到', 116, 385, 20, MUTED)
        frame = self.cg_sticker.frame(elapsed)
        if frame is not None:
            frame.set_alpha(alpha)
            p.canvas.blit(frame, (548*2, 218*2))
        p.text(f'已通过 {self.endless_clears} 关！', 665, 479, 24, ACCENT, center=True)
        p.text('加作者凭借这个通过图片', 435, 529, 21, INK)
        p.text('可以获得0.01元', 435, 566, 23, ORANGE)
        if self.cg_emoji is not None:
            p.canvas.blit(self.cg_emoji, (627*2, 555*2))
        self.button('继续挑战   →', (435, 617, 223, 40), 'endless_next', True)
        self.button('返回首页', (673, 617, 191, 40), 'home')

    def make_fail_overlay(self):
        """Cache the supplied photo and caption at the painter's 2x resolution."""
        try:
            photo = pygame.image.load(str(Path(__file__).resolve().parent / "assets" / "images" / "fail_cat.jpg")).convert()
        except (pygame.error, OSError):
            return None
        overlay = pygame.Surface(self.painter.canvas.get_size()).convert()
        overlay.fill(BG)
        pygame.draw.rect(overlay, PANEL, (500, 260, 920, 1080), border_radius=40)
        width = 800
        height = round(width * photo.get_height() / photo.get_width())
        photo = pygame.transform.smoothscale(photo, (width, height))
        overlay.blit(photo, ((overlay.get_width() - width) // 2, 300))
        font = pygame.font.Font(str(self.painter.bold_path), 72)
        caption = font.render("你好菜啊", True, INK)
        caption = caption.subsurface(caption.get_bounding_rect())
        overlay.blit(caption, ((overlay.get_width() - caption.get_width()) // 2, 1160))
        return overlay

    def make_last_chance_overlay(self):
        try:
            photo = pygame.image.load(str(Path(__file__).resolve().parent / "assets" / "images" / "last_chance_cat.jpg")).convert()
        except (pygame.error, OSError):
            return None
        overlay = pygame.Surface(self.painter.canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((24, 20, 30, 220))
        # Preserve the entire tall meme, including its original captions.
        height = 1280
        width = round(height * photo.get_width() / photo.get_height())
        photo = pygame.transform.smoothscale(photo, (width, height))
        x, y = (overlay.get_width() - width) // 2, 160
        pygame.draw.rect(overlay, PANEL, (x - 14, y - 14, width + 28, height + 28), border_radius=22)
        overlay.blit(photo, (x, y))
        return overlay

    def draw_last_chance(self):
        self.draw_playing()
        self.regions.clear()
        elapsed = time.monotonic() - self.last_chance_started
        self.last_chance_overlay.set_alpha(intro_alpha(elapsed))
        self.painter.canvas.blit(self.last_chance_overlay, (0, 0))

    def draw_fail_intro(self):
        elapsed = time.monotonic() - self.fail_intro_started
        # Reveal the photo over the board first; reveal results only on fade-out.
        # Switch the underlying screen while the overlay is fully opaque.
        if elapsed < INTRO_FADE_IN + INTRO_HOLD:
            self.draw_playing()
        else:
            self.draw_result()
        self.regions.clear()
        self.fail_overlay.set_alpha(intro_alpha(elapsed))
        self.painter.canvas.blit(self.fail_overlay, (0, 0))

    def draw_result(self):
        kind = self.scene
        p = self.painter
        # Draw a dimmed board background, then lock all board input behind modal.
        self.draw_playing()
        self.regions.clear()
        shade = pygame.Surface(p.canvas.get_size(), pygame.SRCALPHA)
        shade.fill((53, 45, 75, 83))
        p.canvas.blit(shade, (0, 0))
        if kind not in ('fail', 'fail_intro'):
            self.draw_win_result()
            return
        p.box((240, 189, 480, 424), PANEL, 26, LINE)
        p.circle((480, 260), 31, "#3D202A")
        p.text("!", 480, 242, 36, RED, center=True)
        title = "这一次，差一点点"
        subtitle = "三次机会已用完。换个顺序，再试一次。"
        p.text(title, 480, 317, 29, INK, center=True); p.text(subtitle, 480, 370, 15, MUTED, center=True)
        p.box((287, 410, 386, 62), PALE, 13)
        p.text(f"失误   {3 - self.mistakes} / 3", 322, 434, 16, RED); p.line((480, 425), (480, 458)); p.text(f"提示   {3 - self.hints} / 3", 520, 434, 16, ACCENT)
        self.button("再试一次", (287, 494, 386, 49), "restart", True)
        self.button("返回首页", (287, 557, 186, 34), "home")
        self.button("新一轮无尽" if self.mode == 'endless' else "返回选关", (487, 557, 186, 34), "endless" if self.mode == 'endless' else "levels")

    def render(self):
        self.painter.canvas.fill(BG); self.painter.buttons.clear(); self.painter.text_bounds.clear(); self.regions.clear(); self.draw_header_footer()
        if self.scene == "home": self.draw_home()
        elif self.scene == "levels": self.draw_levels()
        elif self.scene == "playing": self.draw_playing()
        elif self.scene == "last_chance": self.draw_last_chance()
        elif self.scene == "fail_intro": self.draw_fail_intro()
        elif self.scene == 'endless_cg': self.draw_endless_cg()
        else: self.draw_result()
        self.danger_effect.draw(self.painter.canvas, self.sound.heartbeat_started)
        return pygame.transform.smoothscale(self.painter.canvas, SIZE)

    def board_cell(self, point):
        x, y, cell = self.board_geometry(); n = len(self.board)
        outer = pygame.Rect(x - 18, y - 18, cell * n + 36, cell * n + 36)
        if not outer.collidepoint(point): return None
        col, row = int((point[0] - x) // cell), int((point[1] - y) // cell)
        return (row, col) if 0 <= row < n and 0 <= col < n else None

    def click(self, point):
        if self.scene in ("fail_intro", "last_chance"): return
        for rect, action in reversed(self.regions):
            if rect.collidepoint(point):
                self.action(action); return
        if self.scene == "playing" and self.animation is None and self.auto_solve_queue is None:
            cell = self.board_cell(point)
            if cell and self.board[cell[0]][cell[1]] != ".": self.select_arrow(*cell)

    def select_arrow(self, row, col):
        if self.scene != "playing" or self.animation is not None: return
        if can_exit(self.board, row, col):
            self.sound.play("click"); direction = self.board[row][col]
            self.animation = {"kind":"fly", "row":row, "col":col, "direction":direction, "start":time.monotonic(), "duration":.32}
            self.feedback, self.feedback_color = "飞出棋盘……", ACCENT
        else:
            self.sound.play("hit"); self.mistakes -= 1
            self.animation = {"kind":"collision", "row":row, "col":col, "blocker":first_blocker(self.board,row,col), "start":time.monotonic(), "duration":.26}
            self.highlight = (row, col); self.feedback, self.feedback_color = "前方有箭头挡住了，先解除阻挡吧。", RED
        self.sync_game_audio()

    def action(self, action):
        if self.scene in ("fail_intro", "last_chance"): return
        self.sound.play("click")
        if action == "sound": self.sound.toggle(); self.save_progress()
        elif action == "music": self.sound.toggle_music(); self.save_progress()
        elif action == "start": self.reset_level(next((i for i in range(len(LEVELS)) if str(i) not in self.best), 0))
        elif action == 'endless': self.start_endless()
        elif action == 'github': webbrowser.open('https://github.com/ddxww/arrow-order', new=2)
        elif action == 'endless_next' and self.mode == 'endless' and self.scene in ('endless_win', 'endless_cg'):
            self.next_endless_level()
        elif action == 'show_cg' and self.mode == 'endless' and self.endless_reward_shown and self.scene == 'endless_win':
            self.cg_started = time.monotonic()
            self.scene = 'endless_cg'
        elif action == "levels": self.scene, self.animation, self.auto_solve_queue = "levels", None, None
        elif action == "home": self.scene, self.animation, self.auto_solve_queue = "home", None, None
        elif action == "restart": self.reset_level()
        elif action == "hint" and self.hints > 0 and self.animation is None and not self.hint_active:
            options = [(r, c) for r in range(len(self.board)) for c in range(len(self.board)) if self.board[r][c] != "." and can_exit(self.board, r, c)]
            if options:
                self.hints -= 1; self.highlight = options[0]; self.hint_active = True; self.feedback, self.feedback_color = "金色箭头前方畅通，可以先点击它。", ORANGE
        elif action == "auto_solve" and self.scene == "playing" and self.animation is None and self.auto_solve_queue is None:
            order = self.current_level.solution
            if order:
                self.auto_solve_queue = list(order)
                self.highlight = None
                self.hint_active = False
                self.feedback, self.feedback_color = "自动求解已开始，正在按合法顺序清空棋盘。", ACCENT
                self.advance_auto_solve()
            else:
                self.feedback, self.feedback_color = "当前棋盘没有可用的完整解序。", RED
        elif action == "next": self.reset_level(self.level_index + 1)
        elif action == "first": self.reset_level(0)
        elif isinstance(action, tuple) and action[0] == "level": self.reset_level(action[1])
        self.sync_game_audio()

    def update(self):
        self.update_animations()
        self.sync_game_audio()

    def update_animations(self):
        if self.scene == "last_chance":
            if time.monotonic() - self.last_chance_started >= INTRO_DURATION:
                self.scene = "playing"
                self.last_chance_started = None
                self.hover = None
                self.feedback, self.feedback_color = "只剩一次机会，仔细观察再出手。", RED
            return
        if self.scene == "fail_intro":
            if time.monotonic() - self.fail_intro_started >= INTRO_DURATION:
                self.scene = "fail"
                self.fail_intro_started = None
            return
        if not self.animation: return
        if time.monotonic() - self.animation["start"] < self.animation["duration"]: return
        a = self.animation; self.animation = None
        if a["kind"] == "fly":
            self.board[a["row"]][a["col"]] = "."; self.sound.play("fly"); self.highlight = None; self.hint_active = False
            if self.count_arrows() == 0:
                self.auto_solve_queue = None
                self.timer.pause()
                elapsed_ms = self.timer.elapsed_ms()
                if self.mode == 'endless':
                    if not self.endless_round_cleared:
                        self.endless_clears += 1
                        self.endless_round_cleared = True
                    self.result_stars, self.result_record = 0, None
                    self.victory_started = time.monotonic()
                    self.sound.play('win')
                    if self.endless_clears >= 3 and not self.endless_reward_shown:
                        self.endless_reward_shown = True
                        self.cg_started = time.monotonic()
                        self.scene = 'endless_cg'
                    else:
                        self.scene = 'endless_win'
                    return
                self.result_stars = award_stars(self.mistakes, elapsed_ms, LEVELS[self.level_index].target_seconds)
                record = {"mistakes": 3 - self.mistakes, "hints": 3 - self.hints,
                          "elapsed_ms": elapsed_ms, "stars": self.result_stars}
                self.result_record = record
                self.victory_started = time.monotonic()
                old = self.best.get(str(self.level_index))
                if better_record(record, old): self.best[str(self.level_index)] = record
                self.unlocked = min(len(LEVELS), max(self.unlocked, self.level_index + 2)); self.save_progress(); self.sound.play("win")
                self.scene = "complete" if self.level_index == len(LEVELS) - 1 else "win"
            else:
                self.feedback = "自动求解中……" if self.auto_solve_queue is not None else "很好，继续观察下一支畅通的箭头。"
                self.advance_auto_solve()
        elif self.mistakes <= 0:
            self.auto_solve_queue = None
            self.scene = "fail_intro" if self.fail_overlay is not None else "fail"
            self.fail_intro_started = time.monotonic() if self.fail_overlay is not None else None
        elif self.mistakes == 1 and self.last_chance_overlay is not None:
            self.auto_solve_queue = None
            self.scene = "last_chance"
            self.last_chance_started = time.monotonic()

    def advance_auto_solve(self):
        """Start the next solver-selected move after the previous animation ends."""
        if self.scene != "playing" or self.animation is not None or self.auto_solve_queue is None:
            return
        if not self.auto_solve_queue:
            self.auto_solve_queue = None
            return
        row, col = self.auto_solve_queue.pop(0)
        self.select_arrow(row, col)

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
            self.update(); frame = self.render(); sw, sh = self.screen.get_size(); scale = min(sw / SIZE[0], sh / SIZE[1]); fitted = (round(SIZE[0]*scale), round(SIZE[1]*scale)); offset=((sw-fitted[0])//2,(sh-fitted[1])//2); self.screen.fill(BG); self.screen.blit(pygame.transform.smoothscale(frame, fitted), offset); pygame.display.flip(); clock.tick(FPS)
        self.save_progress(); pygame.quit()


def main():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    Game().run()


if __name__ == "__main__": main()
