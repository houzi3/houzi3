# Profile artwork

The README keeps the full-width Wukong composition in both GitHub themes.
Each theme link displays an animated SVG. For visitors who prefer reduced
motion, the picture element selects a still JPEG of the same composition.

Each SVG contains one compressed copy of the scene and two small displacement
maps. Phase-shifted SVG animations move a wave along the ribbon over six
seconds. The displacement starts near zero at the shoulder and increases
toward the free end.

The name, bio, and statistics are selectable README text below the banner.
The daily GitHub Actions job updates the statistics between the README markers.

## Rebuild

Install `requirements-artwork.txt` into a virtual environment, then run:

```sh
python scripts/build_artwork.py
python scripts/check_artwork.py
```

The builder uses the existing text-free source PNGs in `assets/source/`.
It writes `assets/ribbon-{light,dark}.svg` and the corresponding JPEGs.
