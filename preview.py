"""Run the first-stage design preview or export its screens.

This is an explicitly labelled preview, not the playable game. Arrow clicks
do not run rules yet. Use the gallery or number keys to inspect sample states.
"""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="箭序 · 第一阶段界面预览")
    parser.add_argument("--export", action="store_true", help="Export PNGs without a visible window")
    parser.add_argument("--output", type=Path, help="Directory for exported PNGs (use with --export)")
    parser.add_argument("--scene", default="home", choices=("home", "levels", "game", "hint", "collision", "win", "fail", "complete"))
    args = parser.parse_args()
    if args.export:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    from arrowgame.preview_ui import Painter, SCENES, SIZE

    pygame.display.init()
    pygame.font.init()
    painter = Painter()
    if args.export:
        pygame.display.set_mode((1, 1))
        output = args.output or Path(__file__).resolve().parent / "docs" / "previews"
        output.mkdir(parents=True, exist_ok=True)
        report = {}
        for scene in SCENES:
            surface = painter.render(scene)
            overflow = [label for label, rect in painter.text_bounds if not pygame.Rect(0, 0, *SIZE).contains(rect)]
            if overflow:
                raise ValueError(f"{scene}: text exceeds canvas: {overflow}")
            pygame.image.save(surface, str(output / f"{scene}.png"))
            report[scene] = {"size": list(SIZE), "text_runs": len(painter.text_bounds), "text_overflow": overflow}
        (output / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exported {len(SCENES)} preview screens. Text stays inside the canvas.")
        pygame.quit()
        return

    screen = pygame.display.set_mode(SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("箭序 · 界面预览（非可玩版）| 按 1—8 切换画面，Esc 退出")
    scene = args.scene
    clock = pygame.time.Clock()
    running = True
    while running:
        surface = painter.render(scene)
        sw, sh = screen.get_size()
        scale = min(sw / SIZE[0], sh / SIZE[1])
        fitted = (max(1, round(SIZE[0] * scale)), max(1, round(SIZE[1] * scale)))
        offset = ((sw - fitted[0]) // 2, (sh - fitted[1]) // 2)
        screen.fill("#000000")
        screen.blit(pygame.transform.smoothscale(surface, fitted), offset)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    scene = SCENES[event.key - pygame.K_1]
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                point = ((event.pos[0] - offset[0]) / scale, (event.pos[1] - offset[1]) / scale)
                for button in painter.buttons:
                    if button.rect.collidepoint(point) and button.target in SCENES:
                        scene = button.target
                        break
        clock.tick(30)
    pygame.quit()


if __name__ == "__main__":
    main()
