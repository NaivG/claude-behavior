# Claude 行为准则 _（claude-behavior）_

[English](README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/agent%20skill-SKILL.md-8b5cf6.svg)](SKILL.md)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Standard-Readme](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=badge)](https://github.com/RichardLitt/standard-readme)

把 Claude 的工程与设计习惯，落成 agent 当场就能核验的动作与产物。

agent 最容易犯的错，是不看输出就下结论：构建通过、首屏截图顺眼，评审到此为止。可第 11 页的文字溢出、切换动画里撞在一起的两个元素、375px 下断得难看的标题，都不在第一张截图里，也都不在源码里。这个仓库把“先看，再判断”做成两件能拿在手上的东西。

## 目录

- [背景](#背景)
- [安装](#安装)
  - [使用 `skills` CLI](#使用-skills-cli)
  - [手动安装](#手动安装)
  - [依赖](#依赖)
- [使用](#使用)
  - [命令行](#命令行)
- [仓库结构](#仓库结构)
- [API](#api)
  - [命令清单](#命令清单)
  - [函数](#函数)
- [许可证](#许可证)

## 背景

agent 经常被要求评估自己刚做完的东西，而它的判断依据常常只剩一句“我觉得没问题”。这不是态度问题，是流程缺了一环：把产物真正拿出来看。

这个仓库补的就是这一环。它用平实的语言重述一套工程与设计原则，再给每条视觉原则配一件可复现的产物——一张比较拼图，或者一张巡检表。原则本身来自 Claude 在工程与设计任务上的工作方式；把原则落成可执行的工具与流程，是本仓库做的事。

## 安装

### 使用 `skills` CLI

推荐，支持 75 多种代理运行时：

```bash
npx skills add NaivG/claude-behavior
```

或者从全局安装/使用 `skills` CLI：

```bash
npm i -g skills@latest
skills add NaivG/claude-behavior
```

### 手动安装

把目录复制进你的 agent 会读取的 skills 目录。DeepSeek Harness 的个人 skill 位于 `~/.agents/skills`，Claude Code 位于 `~/.claude/skills`，其他 runtime 请查各自的文档。

```bash
cp -r claude-behavior ~/.agents/skills/claude-behavior
```

```powershell
Copy-Item -Recurse .\claude-behavior "$HOME\.agents\skills\claude-behavior"
```

装好后目录里能看到 `SKILL.md` 即为成功。多数 runtime 会在下次会话启动时发现它；如果技能目录里仍然没有，重启会话即可。

### 依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Python 3.10+ | `scripts/cmp_board.py` | 用到 PEP 604 联合类型注解，3.9 及更早版本无法导入。 |
| [Pillow](https://pypi.org/project/Pillow/) 9.1+ | 全部子命令 | 负责缩放、拼接与标签渲染。 |
| [Playwright](https://playwright.dev/python/) 与 Chromium | `cmp` 的 `.html` 输入、`html-sheet`、`stress` | `pip install playwright && playwright install chromium` |
| [FFmpeg](https://ffmpeg.org/)（`ffprobe`、`ffmpeg` 在 `PATH` 中） | `keyframes` | `ffprobe` 读时长，`ffmpeg` 抽帧。 |

`SKILL.md` 本身不需要任何依赖；上表只针对内置脚本。

## 使用

在会话里加载这个 skill，然后像往常一样提要求。触发词写在 `SKILL.md` 的 description 里：`claude-behavior`、`claude style`、`claude workflow`、`cmp`、`拼图比较`、`关键帧检查`、`按claude习惯做`。

```text
按 claude 习惯做：把 A、B 两版并排比较，先说评分标准，再给结论。
```

```text
用 claude-behavior 评审这个页面：把它渲染出来，告诉我 375px 和深色模式下哪里坏。不要只读源码。
```

skill 生效期间，这些原则会一直跟着任务走。视觉流程由内置脚本完成，每个子命令把拼好的图写到 `--out`。

### 命令行

下文的 `$CB` 指包含 `SKILL.md` 的目录。脚本可以在任意目录下运行。

```bash
# 1. 把候选图或 HTML 拼成一张比较板
python "$CB/scripts/cmp_board.py" cmp opt-a.png opt-b.png opt-c.png \
  --labels "A: Restrained Serif,B: Dense Grid,C: Dark Split" \
  --out cmp-directions.png

# 2. 从视频里抽 12–20 张关键帧，拼成一张巡检表
python "$CB/scripts/cmp_board.py" keyframes output.mp4 \
  --count 16 --cols 4 --out inspect-keyframes.png

# 3. 从 HTML 里采 12–20 个滚动切片、幻灯片或时间轴帧
python "$CB/scripts/cmp_board.py" html-sheet index.html --mode scroll \
  --count 16 --cols 4 --out inspect-scroll.png

# 4. 把已有截图拼成带编号的巡检表
python "$CB/scripts/cmp_board.py" grid shots/*.png --cols 4 --out inspect-grid.png

# 5. 跨视口与明暗主题做压力测试
python "$CB/scripts/cmp_board.py" stress index.html --out cmp-stress.png
```

每个子命令都有 `--help`；[API](#api) 里列了可复用的函数与命令清单。

## 仓库结构

```text
claude-behavior/
├── SKILL.md                      # 技能本体：原则、两套视觉流程、执行规则
├── references/
│   └── visual-cmp-playbook.md    # cmp 板与巡检表的长文指南
├── scripts/
│   └── cmp_board.py              # 五个子命令；Pillow，可选 Playwright 与 FFmpeg
├── LICENSE                       # MIT
├── README.md                     # English
└── README.ZH.md                  # 本文件
```

## API

`scripts/cmp_board.py` 既可直接当命令行用，也可作为模块导入：

```python
import sys
sys.path.insert(0, "claude-behavior/scripts")
import cmp_board
```

### 命令清单

| 命令 | 做什么 |
|---|---|
| `cmp` | 把两张或更多图片或 `.html` 文件拼成一张比较板。 |
| `keyframes` | 从视频里采 12–20 帧，拼成一张巡检表。 |
| `html-sheet` | 从一个 `.html` 文件里采 12–20 个滚动切片、幻灯片或时间轴帧。 |
| `grid` | 给任意数量的已有截图编号，拼成一张巡检表。 |
| `stress` | 在六个视口与主题组合下渲染同一个 `.html` 文件。 |

`keyframes` 还接受 `--keep-frames`，把每一帧按原分辨率另存，而不只是拼成巡检表。

相对路径按当前目录解析。shell 没有展开的通配符由脚本自己展开，这在 Windows PowerShell 下尤其重要。

### 函数

- `stitch_tiles(tiles, out_path, cols, tile_width=640, title=None) -> Path`：所有拼图背后的排版引擎。`tiles` 是 `(label, Pillow.Image)` 列表；过高的图会按 1.6 倍宽度裁切，避免一张整页截图撑满整块板。
- `render_html_to_image(html_path, out_path, width=1440, height=900, color_scheme="light", wait_ms=1200) -> Path`：单文件 Playwright 渲染，能容忍加载缓慢或不可达的外部资源。
- `expand_inputs(raw_inputs) -> list[Path]`：展开通配符，并丢掉不存在的路径。
- `build_parser() -> argparse.ArgumentParser` 与 `main() -> int`：命令行入口；`main()` 返回进程退出码。

## 许可证

[MIT](LICENSE) © 2026–2027 NaivG。

SPDX 标识符：`MIT`。在保留版权声明与许可声明的前提下，允许商用与非商用使用、修改与再分发。完整条款见 [LICENSE](LICENSE)。
