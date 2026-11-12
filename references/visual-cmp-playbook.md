# Visual `cmp` & Contact-Sheet Playbook

This reference details the two core visual verification habits in `claude-behavior`:
1. **`cmp` (Compare) Puzzle Boards** for design exploration, A/B variable tuning, and multi-option selection.
2. **12–20 Keyframe / Screen Contact Sheets** for comprehensive detail inspection upon initial build completion.

---

## Part 1 · The `cmp` (Compare) Puzzle Board Workflow

### Why `cmp` Boards Beat Sequential Viewing
When an agent views `option-a.png`, `option-b.png`, and `option-c.png` as separate images across tool calls:
- Each image is auto-scaled independently by the viewer, disguising font-size and density differences.
- Subtle variations in spacing, contrast, and hierarchy fade between turns.
- Selection degenerates into vague gut feel rather than structured comparison.

Placing candidates into a **single stitched `cmp` board** forces uniform scale, immediate juxtaposition, and objective criteria-based evaluation.

### When to Build a `cmp` Board
1. **Direction Selection (2–4 candidates)**: Comparing distinct layout structures, typographic systems, or aesthetic directions.
2. **Single-Variable Tuning (`Before / After`)**: Isolating one change at a time (e.g., `padding: 24px` vs `40px`, or `warm-paper` vs `cool-slate` palette) to verify the change genuinely improved hierarchy or legibility.
3. **Cross-Context Check**: Juxtaposing Light vs. Dark mode, or Desktop vs. Mobile, in one frame to verify visual consistency.

### Step-by-Step `cmp` Protocol

1. **Generate the `cmp` image**:
   ```bash
   python "$CB/scripts/cmp_board.py" cmp dir-a.html dir-b.html dir-c.html \
     --labels "A: Editorial Serif,B: Modular Grid,C: Minimal Split" \
     --out cmp-options.png
   ```
   *(Accepts `.png`/`.jpg`/`.webp` images directly, or `.html` files which are rendered automatically via Playwright.)*

2. **Open `cmp-options.png` with your vision (`read`) tool.**

3. **Name explicit criteria first, then score each option**:
   Never jump straight to "I like B". Write a short criteria matrix tailored to the user's goal:

   | Criterion | Why it matters here | Option A | Option B | Option C |
   |---|---|---|---|---|
   | **1. Hierarchy** | User must grasp core metric in <2s | Strong headline, weak data | Clear 3-tier focal path | Flat; cards compete |
   | **2. Readability** | Dense technical copy | Good contrast, narrow measure | Best line height & scanability | Low contrast on subtext |
   | **3. Context / Brand Fit** | B2B developer tool | Too magazine-like | Fits existing dashboard conventions | Too playful |
   | **4. Effort / Simplicity** | Must remain easy to maintain | Custom SVG mask | Pure CSS grid, minimal DOM | Complex absolute positioning |

4. **State reasoning and a clear recommendation**:
   - Example: *"I recommend **Option B**. Against our criteria, it gives the clearest 3-tier hierarchy for dense technical data, fits your existing dashboard conventions, and uses a straightforward CSS grid without fragile positioning. Option A is stronger if you want an editorial marketing feel, while Option C loses readability on secondary labels. Which direction would you like to proceed with?"*

---

## Part 2 · The 12–20 Keyframe / Screen Contact Sheet Inspection

### Why 12–20 Frames in One Image?
- **1–3 screenshots are too few**: They miss mid-animation collisions, scroll-triggered overlaps, slide #11 text overflow, or empty-state breakage.
- **20 separate full-size images are too noisy**: They consume massive context window budget and make it hard to spot cross-frame jumps, inconsistent margins, or pacing dead zones.
- **12–20 frames stitched into a single 4×3, 4×4, or 5×4 contact sheet** hit the sweet spot: high enough temporal/spatial density to catch almost every detail bug, compact enough to scan holistically in one vision pass.

### How to Sample 12–20 Frames by Artifact Type

| Artifact Type | What the 12–20 Tiles Should Represent | Command (`cmp_board.py`) |
|---|---|---|
| **Video / Remotion / Canvas / CSS Animation** | 16–20 evenly spaced frames across the full duration (or key transition beats) with `#idx` and `t=MM:SS.d` timestamps | `python "$CB/scripts/cmp_board.py" keyframes video.mp4 --count 16 --cols 4 --out inspect-keyframes.png` |
| **Time-Driven HTML Animation** | 16–20 frames captured along the animation timeline (via `window.seekTo(t)`, Web Animations API fast-forward, or real-time sampling) | `python "$CB/scripts/cmp_board.py" html-sheet anim.html --mode timeline --duration 8 --count 16 --out inspect-anim.png` |
| **Long Scrolling Web Page / Report** | 12–16 overlapping viewport scroll slices from top (`y=0`) to footer, plus mobile/dark-mode tiles | `python "$CB/scripts/cmp_board.py" html-sheet page.html --mode scroll --count 12 --cols 4 --out inspect-scroll.png` |
| **Slide Deck / Presentation** | All slides (or 12–20 slides) stepped via `ArrowRight` or slide directory | `python "$CB/scripts/cmp_board.py" html-sheet deck.html --mode slides --count 16 --cols 4 --out inspect-deck.png` |
| **Interactive App / UI Flow** | 12–16 distinct UI states: Default, Empty, Loading, Error, Long-Text Stress, Modal Open, Filter Active, Dark Mode, Mobile (`375px`), Tablet (`768px`) | Capture states to `shots/*.png`, then:<br>`python "$CB/scripts/cmp_board.py" grid shots/*.png --cols 4 --out inspect-states.png` |

### The 6-Point Contact Sheet Audit Checklist

Whenever you open an `inspect-*.png` contact sheet, scan row by row against these 6 checks:

1. **Text Clipping, Wrapping & Orphans**
   - Are any headlines or badges truncated (`overflow: hidden` cutting descenders, or unexpected `...`)?
   - Does any CJK or English heading leave a single awkward character/word on a new line?
2. **Element Collision & Z-Index Bugs**
   - During transitions (e.g., frames `#04`–`#06`) or scroll positions, do cards, tooltips, sticky navbars, or floating labels overlap unreadably?
3. **Blank Frames, Flash of Unstyled Content, or Dead Holds**
   - Is Frame `#01` or `#16` accidentally black/blank?
   - Are 3+ consecutive frames (`#08`, `#09`, `#10`) completely identical when motion should be happening?
4. **Hierarchy & Visual Density Balance**
   - Look at the squint test across all 16 tiles: can you immediately tell the focal point of each screen?
   - If a tile looks cluttered or exhausting, apply **Cut before adding**—remove borders, secondary pills, or decorative icons before tweaking colors.
5. **Alignment & Rhythm Continuity**
   - Do margins, grid columns, and baseline rhythms hold steady across screens/slides, or do headings jump around by a few pixels between states?
6. **Contrast & Edge-Case Resilience**
   - Are muted labels still legible (≥ 4.5:1)?
   - In stress tiles (narrow viewport, long text, empty state, dark mode), does the layout degrade gracefully?

### Zooming In & Surgical Fixing
When the 12–20 frame contact sheet reveals a problem in specific tiles (e.g., *"Tile #06 has text overlap during the card transition, and Tile #13 overflows on narrow width"*):
1. Open the individual full-resolution frame (`inspect-keyframes_frames/frame_06.png`) if you need pixel-level clarity.
2. Make a **targeted edit** to the code (change one variable at a time).
3. Render a 2-up `Before / After` `cmp` board of Frame `#06` to confirm the fix worked without breaking neighbors.

---

## Part 3 · Zero-Dependency Fallback Snippets

If `scripts/cmp_board.py` cannot be invoked directly, use these minimal one-liners:

### Pure FFmpeg 16-Keyframe Contact Sheet (Video → 4×4 Grid)
```bash
# Get duration D first via ffprobe, then sample 16 frames into a 4x4 tiled image with timestamps:
ffmpeg -y -i input.mp4 \
  -vf "select='not(mod(n,max(1,floor(N/16))))',scale=480:-1,drawtext=text='#%{frame_num}  t=%{pts\:hms}':x=12:y=12:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6,tile=4x4:padding=8:margin=8:color=0x18181b" \
  -frames:v 1 inspect-keyframes.png
```

### Pure Pillow `cmp` / Grid Stitcher (Python One-Liner)
```python
from PIL import Image, ImageDraw
import sys, math

imgs = [Image.open(p).convert("RGB") for p in sys.argv[1:-1]]
out = sys.argv[-1]
cols = min(len(imgs), 4)
rows = math.ceil(len(imgs) / cols)
w = 640
thumbs = [im.resize((w, int(im.height * w / im.width)), Image.Resampling.LANCZOS) for im in imgs]
cell_h = max(t.height for t in thumbs) + 36
canvas = Image.new("RGB", (cols * (w + 16) + 16, rows * (cell_h + 16) + 16), (24, 24, 27))
draw = ImageDraw.Draw(canvas)
for idx, (p, t) in enumerate(zip(sys.argv[1:-1], thumbs)):
    r, c = divmod(idx, cols)
    x, y = 16 + c * (w + 16), 16 + r * (cell_h + 16)
    draw.text((x + 6, y + 6), f"#{idx+1:02d}  {p}", fill=(244, 244, 245))
    canvas.paste(t, (x, y + 32))
canvas.save(out)
```
