"""Build small, self-contained SVG ribbon animations from the source artwork."""

import argparse
import base64
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 960, 352
FILTER_X, FILTER_HEIGHT = 220, 202
FILTER_WIDTH = WIDTH - FILTER_X
DISPLACEMENT = 34
LOOP_SECONDS = 6


def encode_image(image, format, **options):
    encoded = io.BytesIO()
    image.save(encoded, format=format, **options)
    return encoded.getvalue()


def image_uri(data, media_type):
    payload = base64.b64encode(data).decode("ascii")
    return f"data:{media_type};base64,{payload}"


def ribbon_maps(art):
    # Neutral red/green channels leave the scenery fixed. The field tapers to
    # zero at the shoulder and extends slightly past the fabric's edges.
    scene = art.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    rgb = np.asarray(scene)[:FILTER_HEIGHT, FILTER_X:].astype(np.float32)
    y, x = np.mgrid[:FILTER_HEIGHT, FILTER_X:WIDTH]
    red, green, blue = rgb.transpose(2, 0, 1)
    cloth = (red > 65) & (red > 1.8 * green) & (red > 1.55 * blue)
    cloth &= (y < 180) & (x > 235)
    mask = Image.fromarray(cloth.astype(np.uint8) * 255)
    mask = mask.filter(ImageFilter.MaxFilter(45)).filter(ImageFilter.GaussianBlur(9))
    ramp = np.clip((x - 235) / 590, 0, 1)
    weight = (np.asarray(mask) / 255) * ramp * ramp * (3 - 2 * ramp)
    weight *= np.clip(y / 12, 0, 1) * np.clip((FILTER_HEIGHT - y) / 18, 0, 1)
    phase = (x - 235) * (2 * math.pi / 580)

    # Two phase-shifted fields approximate a traveling wave with a single
    # still photo. The fabric near the shoulder barely moves.
    for wave, cross_wave in ((np.cos(phase), np.sin(phase)),
                             (-np.sin(phase), np.cos(phase))):
        channels = np.full((*weight.shape, 3), 128, dtype=np.uint8)
        channels[..., 0] = np.rint(128 + 255 * 1.2 * cross_wave * weight / DISPLACEMENT)
        channels[..., 1] = np.rint(128 + 255 * 14 * wave * weight / DISPLACEMENT)
        yield Image.fromarray(channels)


def displacement_pass(offsets, index, source, waveform):
    samples = [DISPLACEMENT * waveform(math.tau * step / 16) for step in range(16)]
    samples.append(samples[0])
    values = ";".join(f"{sample:.3f}" for sample in samples)
    return f'''    <feImage x="{FILTER_X}" y="0" width="{FILTER_WIDTH}" height="{FILTER_HEIGHT}" preserveAspectRatio="none" xlink:href="{offsets}" result="map-{index}"/>
    <feComponentTransfer in="map-{index}" result="offset-{index}">
      <feFuncR type="linear" slope="1" intercept="-0.0019607843"/>
      <feFuncG type="linear" slope="1" intercept="-0.0019607843"/>
    </feComponentTransfer>
    <feDisplacementMap in="{source}" in2="offset-{index}" scale="0" xChannelSelector="R" yChannelSelector="G" result="wave-{index}">
      <animate attributeName="scale" values="{values}" dur="{LOOP_SECONDS}s" repeatCount="indefinite"/>
    </feDisplacementMap>'''


def build(theme):
    source = ROOT / "assets" / "source" / f"wukong-{theme}.png"
    with Image.open(source) as original:
        art = original.convert("RGB").resize((WIDTH * 2, 840), Image.Resampling.LANCZOS)
    art = art.crop((0, 0, WIDTH * 2, HEIGHT * 2))
    still = encode_image(art, "JPEG", quality=86, optimize=True, subsampling=0)
    artwork = image_uri(still, "image/jpeg")
    maps = [image_uri(encode_image(offset, "PNG", optimize=True), "image/png")
            for offset in ribbon_maps(art)]
    passes = "\n".join([
        displacement_pass(maps[0], 1, "SourceGraphic", math.sin),
        displacement_pass(maps[1], 2, "wave-1", math.cos),
    ])
    # An SVG loaded as an image can use embedded data, but cannot fetch
    # external image layers. Store one photo and two small displacement maps.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<title>Sun Wukong above the clouds</title>
<style>
@media (prefers-reduced-motion: reduce) {{ .moving-ribbon {{ display: none; }} }}
</style>
<defs>
  <image id="art" width="{WIDTH}" height="{HEIGHT}" xlink:href="{artwork}"/>
  <filter id="ribbon" x="{FILTER_X}" y="0" width="{FILTER_WIDTH}" height="{FILTER_HEIGHT}" filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
{passes}
  </filter>
</defs>
<use xlink:href="#art"/>
<use class="moving-ribbon" xlink:href="#art" filter="url(#ribbon)"/>
</svg>
'''
    return svg, still


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "all"), default="all")
    args = parser.parse_args()
    for theme in ("light", "dark") if args.theme == "all" else (args.theme,):
        target = ROOT / "assets" / f"ribbon-{theme}.svg"
        svg, still = build(theme)
        target.write_text(svg, encoding="utf-8")
        target.with_suffix(".jpg").write_bytes(still)
        print(f"Built {target.name}: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
