"""Verify the SVG loop, embedded artwork, and reduced-motion image."""

import base64
import io
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

SVG = "{http://www.w3.org/2000/svg}"
HREF = "{http://www.w3.org/1999/xlink}href"


def image_data(element, kind):
    prefix, payload = element.attrib[HREF].split(",", 1)
    assert prefix == f"data:image/{kind};base64"
    return base64.b64decode(payload, validate=True)


def check(path):
    root = ET.parse(path).getroot()
    assert root.attrib["viewBox"] == "0 0 960 352", path
    assert path.stat().st_size < 350_000, path
    assert root.find(f".//{SVG}text") is None, path

    photo = image_data(root.find(f".//{SVG}image"), "jpeg")
    assert path.with_suffix(".jpg").read_bytes() == photo, path
    with Image.open(io.BytesIO(photo)) as image:
        assert image.size == (1920, 704), path

    maps = root.findall(f".//{SVG}feImage")
    assert len(maps) == 2, path
    for offset in maps:
        with Image.open(io.BytesIO(image_data(offset, "png"))) as image:
            assert image.size == (740, 202), path
            assert image.getpixel((0, 0)) == (128, 128, 128), path
            assert any(low != high for low, high in image.getextrema()[:2]), path

    loops = root.findall(f".//{SVG}feDisplacementMap/{SVG}animate")
    assert len(loops) == 2, path
    for loop in loops:
        assert loop.attrib["attributeName"] == "scale", path
        assert loop.attrib["dur"] == "6s", path
        assert loop.attrib["repeatCount"] == "indefinite", path
        scales = loop.attrib["values"].split(";")
        assert scales[0] == scales[-1] and len(set(scales)) > 1, path
    assert loops[0].attrib["values"] != loops[1].attrib["values"], path
    print(f"PASS {path.name}: {path.stat().st_size:,} bytes, 6 s, matching still")


if __name__ == "__main__":
    assets = Path(__file__).resolve().parents[1] / "assets"
    for theme in ("light", "dark"):
        check(assets / f"ribbon-{theme}.svg")
