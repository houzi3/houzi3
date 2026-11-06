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
        "name": ImageFont.truetype(latin, NAME_SIZE),
        "mobile_name": ImageFont.truetype(latin, 30),
        "handle": ImageFont.truetype(latin, 12),
        "tagline": ImageFont.truetype(cjk, 18),
        "bio": ImageFont.truetype(latin, 14),
    }


class RibbonLoop:
    """A smooth local displacement field; the character and type never move.

    An expanded, feathered ribbon mask transports both its edge and the
    immediately adjacent sky together, avoiding exposed holes or doubled edges.
    Outside that narrow field the original pixels are copied unchanged.
    """

    def __init__(self, source):
        image = Image.open(source).convert("RGB").resize((960, 420), Image.Resampling.LANCZOS)
        self.source = np.asarray(image).astype(np.float32)
        self.y, self.x = np.mgrid[:420, :960].astype(np.float32)
        r, g, b = self.source.transpose(2, 0, 1)
        red = (r > 65) & (r > 1.8 * g) & (r > 1.55 * b)
        red &= (self.y < 180) & (self.x > 235)
        mask = Image.fromarray((red * 255).astype(np.uint8))
        mask = mask.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(7))
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
        sy = np.clip(self.y - wave * self.mask * self.ramp, 0, 419)
        sx = np.clip(self.x - 0.8 * math.sin(phase) * self.mask * self.ramp, 0, 959)
        x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, 959), np.minimum(y0 + 1, 419)
        fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
        top = self.source[y0, x0] * (1 - fx) + self.source[y0, x1] * fx
        bottom = self.source[y1, x0] * (1 - fx) + self.source[y1, x1] * fx
        return Image.fromarray(np.rint(top * (1 - fy) + bottom * fy).astype(np.uint8))


def compose(image, dark, mobile, typefaces):
    background = (13, 17, 23) if dark else (255, 255, 255)
    primary = (232, 230, 225) if dark else (35, 35, 35)
    secondary = (164, 170, 178) if dark else (114, 114, 114)
    if mobile:
        scene = image.crop((0, 0, 690, 380)).resize((480, 264), Image.Resampling.LANCZOS)
        fade = np.ones((264, 480), dtype=np.uint8) * 255
        fade[216:] = np.linspace(255, 0, 48, dtype=np.uint8)[:, None]
        canvas = Image.new("RGB", (480, 390), background)
        canvas.paste(scene, (0, 0), Image.fromarray(fade))
        x, handle_y, name_y, tagline_y, bio_y = 24, 276, 317, 350, 378
    else:
        canvas = image.crop((0, 0, 960, 352))
        x, handle_y, name_y, tagline_y, bio_y = 525, 151, 204, 239, 264
    draw = ImageDraw.Draw(canvas)
    for text, y, font, color in (
        ("houzi3 /", handle_y, typefaces["handle"], primary),
        ("Jaeger", name_y, typefaces["mobile_name" if mobile else "name"], primary),
        ("一只好奇的猴子。", tagline_y, typefaces["tagline"], primary),
        ("Software engineer in Shanghai.", bio_y, typefaces["bio"], secondary),
    ):
        draw.text((x, y), text, font=font, fill=color, anchor="ls")
    return canvas


def build_variant(loop, theme, mobile, typefaces, output):
    dark = theme == "dark"
    stem = f"profile-{theme}{'-mobile' if mobile else ''}"
    first = compose(loop.frame(0), dark, mobile, typefaces)
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
                image = first if index == 0 else compose(loop.frame(index), dark, mobile, typefaces)
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
        for mobile in (False, True):
            build_variant(loop, theme, mobile, typefaces, output)


if __name__ == "__main__":
    main()
