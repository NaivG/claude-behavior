# Claude Behavior _(claude-behavior)_

English | [简体中文](README.ZH.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/agent%20skill-SKILL.md-8b5cf6.svg)](SKILL.md)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Standard-Readme](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=badge)](https://github.com/RichardLitt/standard-readme)

An agent skill that turns Claude-style engineering discipline into artifacts an agent can check.

Coding agents are confident about output they have not looked at. This repository packages the working habits that keep that confidence honest: build the simplest thing that solves the stated problem, fit the conventions already in the repository, make targeted edits instead of rewrites, and remove before adding. Two visual workflows make those habits verifiable.

## Table of Contents

- [Background](#background)
- [Install](#install)
  - [Use `skills` CLI](#use-skills-cli)
  - [Manual](#manual)
  - [Dependencies](#dependencies)
- [Usage](#usage)
  - [CLI](#cli)
- [Repository Layout](#repository-layout)
- [API](#api)
  - [Command surface](#command-surface)
  - [Functions](#functions)
- [License](#license)

## Background

Agents are usually asked to judge their own work, and the failure mode is predictable: the build passes, the first screenshot looks acceptable, and the review stops there. Overflow on slide 11, a badge that collides mid-transition, a title that wraps badly at 375px — none of it appears in a single hero screenshot, and none of it is visible in the source.

This repository exists to make that review step concrete. It restates a set of engineering and design principles in plain language, then attaches each visual principle to a small reproducible artifact: a comparison board or a contact sheet. The principles come from how Claude works through engineering and design tasks; the artifacts and the command-line tooling are this repository's contribution.

## Install

### Use `skills` CLI

Recommended, supports over 75 Agent runtimes:

```bash
npx skills add NaivG/claude-behavior
```

or use/install `skills` CLI from global:

```bash
npm i -g skills@latest
skills add NaivG/claude-behavior
```

### Manual

Copy the directory into the skills folder your agent reads. Personal skills live under `~/.agents/skills` for DeepSeek Harness and `~/.claude/skills` for Claude Code; check your runtime's documentation for the exact path.

```bash
cp -r claude-behavior ~/.agents/skills/claude-behavior
```

```powershell
Copy-Item -Recurse .\claude-behavior "$HOME\.agents\skills\claude-behavior"
```

The result is a directory containing `SKILL.md`. Most runtimes discover it on the next session start; restart the session if it does not show up in the skill catalog.

### Dependencies

| Dependency | Needed for | Notes |
|---|---|---|
| Python 3.10+ | `scripts/cmp_board.py` | Requires 3.10 or newer for PEP 604 union annotations. |
| [Pillow](https://pypi.org/project/Pillow/) 9.1+ | every subcommand | Resizing, stitching, and label rendering. |
| [Playwright](https://playwright.dev/python/) with Chromium | `cmp` on `.html` inputs, `html-sheet`, `stress` | `pip install playwright && playwright install chromium` |
| [FFmpeg](https://ffmpeg.org/) (`ffprobe` and `ffmpeg` on `PATH`) | `keyframes` | `ffprobe` reads duration, `ffmpeg` extracts frames. |

`SKILL.md` itself needs no dependencies; the table covers the bundled script only.

## Usage

Load the skill for a session, then ask for the work as usual. The `SKILL.md` description lists the trigger phrases: `claude-behavior`, `claude style`, `claude workflow`, `cmp`, `拼图比较`, `关键帧检查`, and `按claude习惯做`.

```text
Use claude-behavior for this review: render the page, then tell me what breaks at 375px
and in dark mode. Don't judge it from the source.
```

```text
按 claude 习惯做：把 A、B 两版并排比较，先说评分标准，再给结论。
```

The principles stay active for the whole task. The visual workflows run through the bundled script, and each subcommand writes its image to `--out`.

### CLI

`$CB` below stands for the directory containing `SKILL.md`. Run the script from anywhere.

```bash
# 1. Compare candidate images or HTML files on one board
python "$CB/scripts/cmp_board.py" cmp opt-a.png opt-b.png opt-c.png \
  --labels "A: Restrained Serif,B: Dense Grid,C: Dark Split" \
  --out cmp-directions.png

# 2. Pull 12–20 keyframes from a video into one contact sheet
python "$CB/scripts/cmp_board.py" keyframes output.mp4 \
  --count 16 --cols 4 --out inspect-keyframes.png

# 3. Sample 12–20 scroll slices, slides, or timeline frames from an HTML file
python "$CB/scripts/cmp_board.py" html-sheet index.html --mode scroll \
  --count 16 --cols 4 --out inspect-scroll.png

# 4. Stitch existing screenshots into a numbered audit sheet
python "$CB/scripts/cmp_board.py" grid shots/*.png --cols 4 --out inspect-grid.png

# 5. Stress-test one page across viewports and light/dark themes
python "$CB/scripts/cmp_board.py" stress index.html --out cmp-stress.png
```

Each subcommand has `--help`; [API](#api) lists the reusable functions and the command surface.

## Repository Layout

```text
claude-behavior/
├── SKILL.md                      # the skill: principles, both visual workflows, operating rules
├── references/
│   └── visual-cmp-playbook.md    # long-form guide to cmp boards and contact sheets
├── scripts/
│   └── cmp_board.py              # five subcommands; Pillow, plus optional Playwright and FFmpeg
├── LICENSE                       # MIT
├── README.md                     # this file
└── README.ZH.md                  # 简体中文
```

## API

`scripts/cmp_board.py` is both a CLI and an importable module:

```python
import sys
sys.path.insert(0, "claude-behavior/scripts")
import cmp_board
```

### Command surface

| Command | What it does |
|---|---|
| `cmp` | Stitches two or more images or `.html` files into one comparison board. |
| `keyframes` | Samples 12–20 frames from a video and puts them on one contact sheet. |
| `html-sheet` | Captures 12–20 scroll slices, slides, or timeline frames from one `.html` file. |
| `grid` | Numbers and stitches any number of existing screenshots into one sheet. |
| `stress` | Renders one `.html` file at six viewport and theme combinations. |

`keyframes` also takes `--keep-frames`, which saves every captured frame at full resolution instead of only building the sheet.

Relative paths resolve against the current directory. The script expands globs the shell may not have expanded, which matters on Windows PowerShell.

### Functions

- `stitch_tiles(tiles, out_path, cols, tile_width=640, title=None) -> Path` — the layout engine behind every board. `tiles` is a list of `(label, Pillow.Image)` pairs; tall tiles are cropped at 1.6× their width so one full-page screenshot cannot dominate the sheet.
- `render_html_to_image(html_path, out_path, width=1440, height=900, color_scheme="light", wait_ms=1200) -> Path` — single-file Playwright render that tolerates slow or unreachable external assets.
- `expand_inputs(raw_inputs) -> list[Path]` — expands globs and drops paths that do not exist.
- `build_parser() -> argparse.ArgumentParser` and `main() -> int` — the CLI entry point; `main()` returns the process exit code.

## License

[MIT](LICENSE) © 2026–2027 NaivG.

SPDX identifier: `MIT`. Commercial and non-commercial use, modification, and redistribution are permitted as long as the copyright notice and permission notice are included. See [LICENSE](LICENSE) for the full text.
