# 一箭又一箭 · 箭序

使用 Python 与 pygame-ce 开发的单格箭头解谜游戏，课程项目。

**当前进度：阶段 1，界面预览，等待用户确认。尚非完整可玩游戏，暂无 EXE。**

已准备需求与验收文档、8 种真实 Pygame 绘制的界面预览、中文字体资源，以及开发过程记录。预览中的棋盘、成绩、解锁状态均为静态样例，音效与存档功能尚未实现。阶段 2 将实现六关和全部玩法，阶段 3 提供 EXE 与完整博客材料。

## 看预览

直接打开 [交互预览画廊](docs/previews/index.html)，切换首页、选关、游戏、提示、碰撞、通关、失败和最终完成画面。浏览器画廊不需要 Python。

![首页](docs/previews/home.png)

![游戏界面](docs/previews/game.png)

## 运行 Pygame 预览

开发环境：Windows、CPython 3.13.5、pygame-ce 2.5.8。字体随项目提供，不依赖系统字体，不需要联网运行。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe preview.py
```

预览窗口支持缩放。按 `1`—`8` 切换画面，`Esc` 退出；部分导航按钮可以切换预览画面。棋盘不执行消除逻辑，声音按钮也只是外观预览。

导出截图（无可见窗口）：

```powershell
.\.venv\Scripts\python.exe preview.py --export
```

资源路径基于脚本文件定位，因此也可从其他目录通过 `preview.py` 的绝对路径启动。

## 设计与记录

- [需求与验收标准](docs/PRD.md)
- [开发记录、PSP 与本人试玩记录](docs/DEVELOPMENT.md)
- [来源与字体许可说明](docs/REFERENCES.md)
- [阶段 1 检查记录](docs/PREVIEW_REVIEW.md)

## 字体

`assets/fonts/ArrowOrder-Regular.ttf` 与 `ArrowOrder-Semibold.ttf` 是 Noto Sans SC 的常规/半粗静态字重子集，包含 GB2312 字符集和界面符号，已改名为 ArrowOrder Sans。完整字体许可见 [SIL OFL 1.1](assets/fonts/OFL.txt)。

运行不需要重新生成字体。仅开发者重建资源时，运行 `tools/fetch_font.py` 下载 Google Fonts 官方源字体，然后在安装了 `fonttools` 的环境执行 `tools/prepare_font.py`。字体生成工具不属于游戏运行依赖。

## 项目范围

最终版本计划含 6 个递进关卡、每关 3 次失误机会与 3 次提示、选关解锁、最佳成绩保存和可静音音效。每关需用户本人实际试玩；自动化检查不能代替本人试玩。GitHub 目标仓库与学号待最终材料阶段补齐。
