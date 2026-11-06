# Profile artwork

The selected Wukong illustration has matching light and dark treatments. The
README uses GitHub's `#gh-light-mode-only` / `#gh-dark-mode-only` link contexts
for the visitor's GitHub theme, including a manually selected theme that differs
from the system setting. Every viewport uses the same selected wide composition,
with no mobile crop or alternate layout. Inside each theme link, a picture element
chooses only between the wide GIF and its PNG first frame for reduced motion.
The wide artwork is rendered at 1920 × 704 and displayed at up to 960 px wide.
The separate statistics SVGs remain sharp and are refreshed daily without
rebuilding the animation.

The hero is a six-second, 90-frame seamless loop. A feathered displacement field
follows the red ribbon, anchored near Wukong's shoulder. Only the ribbon and its
immediate edge neighbourhood move; the figure, mountains and all text stay still.
The desktop name is 34 px, smaller than the design mockup. The statistics share
one baseline at every viewport width, using the same theme-specific statistics SVG.

## Rebuild

Install FFmpeg and `requirements-artwork.txt` into a virtual environment, then run:

```sh
python scripts/build_artwork.py
```

The builder uses Helvetica Neue and Hiragino Sans GB on macOS, or DejaVu Sans and
Noto Sans CJK on Linux. Use `--font` and `--cjk-font` to supply equivalent local
font files. The generated GIFs and PNGs are committed, so no artwork dependencies
or font installation are needed in the daily GitHub Actions workflow.

The text-free source PNGs in `assets/source/` were prepared with the built-in
image generation tool from the selected design. The edit instruction was to
remove all type and the statistics divider while preserving the composition,
Wukong, ribbon, lighting and landscape. Typography and motion are produced by the
builder, rather than baked into those source images.

`scripts/update_profile.py` updates only README alternate text and the four
`stats-*.svg` files. It retains the public repository pagination and completeness
checks before replacing the current totals.

GitHub can pause GIF playback according to a visitor's accessibility settings.
The first frame is a complete, readable header in that case.
