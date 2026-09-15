# 参考资料与资源来源

项目：《一箭又一箭 · 箭序》  
建立日期：2026-09-15

## 1. 课程与用户提供的参考

| 来源 | 链接 | 使用范围 |
|---|---|---|
| 福州大学 2026 软件工程与软件工程实践课程作业 | <https://edu.cnblogs.com/campus/fzu/2026-01SoftwareEngineeringandSoftwareEngineeringPractice/homework/16718> | 作业要求、基础规则、验收和提交材料的来源 |
| 宝硕的参考博客（用户提供） | <https://www.cnblogs.com/baoshuo/p/22957201> | 参考交互边界、测试组织及课程文章组织方式，不复制其完整工程、关卡或素材 |
| 用户批准的《一箭又一箭 · 箭序》总方案 | 本项目对应的 Codex 会话 | 六关设计、界面风格、扩展功能、技术路线与三个确认节点的直接实施依据 |

阶段 1 的需求文档按用户明确要求实施的总方案整理。主代理已通过浏览器核验这两个页面：课程要求与方案中的基础规则和交付方向一致。参考文章中实际查阅的内容包括 `pygame-ce`、米白浅绿界面、规则与状态分离、动画期间忽略重复点击、结果页锁定、动画取消、贪心可解性检查、字体随包及 AI 协作、测试、PSP 记录。这里只借鉴理念，不复制其实现；课程原文的精确表述仍以课程网页为准。

## 2. 独立实现约定

- 代码、关卡与视觉设计由本项目独立完成，不复制他人的完整项目。
- 不使用原商业游戏的代码、图片、音效或关卡数据。
- 箭头、网格、按钮和背景以程序绘制；操作音效计划由程序合成。
- 中文字体须使用允许分发的字体，并随项目附带许可文件。实际选用名称、上游地址、版本及许可路径在资源落地时记录。
- 如后续使用其他外部代码片段、库或媒体资源，注明来源与许可，不把参考阅读写成代码引入。

## 3. 技术文档

| 技术 | 官方资料 | 用途 |
|---|---|---|
| Python 3.13 | <https://docs.python.org/3.13/> | 编程语言与标准库 |
| pygame-ce | <https://pyga.me/docs/> | 窗口、输入、绘制、文字和音频；预览阶段选用 `2.5.8` |
| PyInstaller | <https://pyinstaller.org/en/stable/> | 后续 Windows EXE 打包 |

使用第三方库不意味着项目获得了库文档或示例素材的任意再分发权；随包的实际资源按其各自许可处理。

## 4. 当前资源登记

预览使用 Google Fonts 官方发布的 **Noto Sans SC** 中文字体，许可为 **SIL Open Font License 1.1（OFL）**。来源页面：<https://fonts.google.com/noto/specimen/Noto+Sans+SC>。

| 项目内文件 | 内容 | 上游来源 |
|---|---|---|
| `assets/fonts/NotoSansSC.ttf` | 保留在本地的原始可变字体，作为字体构建输入，不纳入 Git 分发 | [Google Fonts 官方目录](https://github.com/google/fonts/tree/main/ofl/notosanssc) |
| `assets/fonts/ArrowOrder-Regular.ttf` | 由原字体生成、子集化并改名的静态字重 450，用于常规文本 | 本项目 `tools/prepare_font.py` 生成 |
| `assets/fonts/ArrowOrder-Semibold.ttf` | 由原字体生成、子集化并改名的静态字重 650，用于强调文本 | 本项目 `tools/prepare_font.py` 生成 |
| [assets/fonts/OFL.txt](../assets/fonts/OFL.txt) | 字体版权与 SIL OFL 1.1 完整许可 | 与字体一同取得的官方许可文件 |

字体处理原因：可变字体在当前渲染环境的默认字重为 100，视觉过细。因此使用本机已有的 fontTools 实例化为 450 与 650，提取当前界面所需字符，并将修改后的字体改名为 ArrowOrder；生成工具为 `tools/prepare_font.py`。后续加入新的界面文字时，需要同步重新生成子集，避免缺字。

以上静态字体沿用 SIL OFL 1.1，并保留上游版权说明；改名不改变其许可。分发源码或 EXE 时须同时保留 [OFL.txt](../assets/fonts/OFL.txt)，且遵守 OFL 对字体单独销售、修改名称及许可传递的约定。

无外部图像或音频素材计划。不能将 Windows 系统自带字体直接当作可自由分发的项目资源。
