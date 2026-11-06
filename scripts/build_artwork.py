"""Build the theme-aware, six-second ribbon loops from the selected artwork.

This is an explicit asset build, not part of the daily statistics refresh.
Install the optional build dependencies from requirements-artwork.txt first.
"""

import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FRAMES = 90
DURATION_MS = 6000
NAME_SIZE = 34
SCALE = 2
WIDTH, HEIGHT = 960 * SCALE, 420 * SCALE


def font_path(override, candidates):
    if override:
        return override
    for candidate in candidates:
        try:
            ImageFont.truetype(candidate, 14)
            return candidate
        except OSError:
            continue
    raise RuntimeError("Provide --font and --cjk-font for the artwork build")


def fonts(latin=None, cjk=None):
    latin = font_path(latin, (
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ))
    cjk = font_path(cjk, (
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ))
    return {
        "name": ImageFont.truetype(latin, NAME_SIZE * SCALE),
        "handle": ImageFont.truetype(latin, 12 * SCALE),
        "tagline": ImageFont.truetype(cjk, 18 * SCALE),
        "bio": ImageFont.truetype(latin, 14 * SCALE),
    }


class RibbonLoop:
    """A smooth local displacement field; the character and type never move.

    An expanded, feathered ribbon mask transports both its edge and the
    immediately adjacent sky together, avoiding exposed holes or doubled edges.
    Outside that narrow field the original pixels are copied unchanged.
    """

    def __init__(self, source):
        image = Image.open(source).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        self.source = np.asarray(image).astype(np.float32)
        self.y, self.x = np.mgrid[:HEIGHT, :WIDTH].astype(np.float32) / SCALE
        r, g, b = self.source.transpose(2, 0, 1)
        red = (r > 65) & (r > 1.8 * g) & (r > 1.55 * b)
        red &= (self.y < 180) & (self.x > 235)
        mask = Image.fromarray((red * 255).astype(np.uint8))
        mask = mask.filter(ImageFilter.MaxFilter(24 * SCALE + 1)).filter(ImageFilter.GaussianBlur(7 * SCALE))
        self.mask = np.asarray(mask).astype(np.float32) / 255
        ramp = np.clip((self.x - 235) / 590, 0, 1)
        self.ramp = ramp * ramp * (3 - 2 * ramp)
        self.mask *= self.x > 235

    def frame(self, index):
        phase = 2 * math.pi * index / FRAMES
        wave = (
            3.6 * math.sin(phase) * np.cos(self.x / 215)
            + 1.1 * math.sin(2 * phase) * np.sin(self.x / 140)
        )
        sy = np.clip((self.y - wave * self.mask * self.ramp) * SCALE, 0, HEIGHT - 1)
        sx = np.clip((self.x - 0.8 * math.sin(phase) * self.mask * self.ramp) * SCALE, 0, WIDTH - 1)
        x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, WIDTH - 1), np.minimum(y0 + 1, HEIGHT - 1)
        fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
        top = self.source[y0, x0] * (1 - fx) + self.source[y0, x1] * fx
        bottom = self.source[y1, x0] * (1 - fx) + self.source[y1, x1] * fx
        return Image.fromarray(np.rint(top * (1 - fy) + bottom * fy).astype(np.uint8))


def compose(image, dark, typefaces):
    primary = (232, 230, 225) if dark else (35, 35, 35)
    secondary = (164, 170, 178) if dark else (114, 114, 114)
    # Preserve the selected wide composition at every display size. A separately
    # cropped mobile layout changed the approved framing and could be upscaled.
    canvas = image.crop((0, 0, WIDTH, 352 * SCALE))
    x, handle_y, name_y, tagline_y, bio_y = 525, 151, 204, 239, 264
    draw = ImageDraw.Draw(canvas)
    for text, y, font, color in (
        ("houzi3 /", handle_y, typefaces["handle"], primary),
        ("Jaeger", name_y, typefaces["name"], primary),
        ("一只好奇的猴子。", tagline_y, typefaces["tagline"], primary),
        ("Software engineer in Shanghai.", bio_y, typefaces["bio"], secondary),
    ):
        draw.text((x * SCALE, y * SCALE), text, font=font, fill=color, anchor="ls")
    return canvas


def build_variant(loop, theme, typefaces, output):
    dark = theme == "dark"
    stem = f"profile-{theme}-wide"
    first = compose(loop.frame(0), dark, typefaces)
    first.save(output / f"{stem}.png", optimize=True)
    target = output / f"{stem}.gif"
    # A shared palette and ordered dither keep stationary pixels fixed, unlike
    # per-frame error diffusion. FFmpeg also stores just changed rectangles.
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pixel_format", "rgb24", "-video_size", f"{first.width}x{first.height}",
        "-framerate", str(FRAMES * 1000 // DURATION_MS), "-i", "pipe:0",
        "-filter_complex", "split[a][b];[a]palettegen=stats_mode=full[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
        "-loop", "0", str(target),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            for index in range(FRAMES):
                image = first if index == 0 else compose(loop.frame(index), dark, typefaces)
                process.stdin.write(image.tobytes())
            process.stdin.close()
        except BrokenPipeError:
            pass
        error = process.stderr.read().decode("utf-8", errors="replace")
        if process.wait():
            raise RuntimeError(f"Animation encoding failed: {error}")
    print(f"Built {target.name}: {first.width}×{first.height}, {target.stat().st_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "all"), default="all")
    parser.add_argument("--font", help="Latin TrueType/OpenType font path")
    parser.add_argument("--cjk-font", help="Chinese TrueType/OpenType font path")
    args = parser.parse_args()
    typefaces = fonts(args.font, args.cjk_font)
    output = ROOT / "assets"
    for theme in ("light", "dark") if args.theme == "all" else (args.theme,):
        loop = RibbonLoop(output / "source" / f"wukong-{theme}.png")
        build_variant(loop, theme, typefaces, output)


if __name__ == "__main__":
    main()
