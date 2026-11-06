"""Verify playback, loop timing, and stationary type/character regions."""

from pathlib import Path

import numpy as np
from PIL import Image


def check(path):
    with Image.open(path) as animation:
        expected_size = (1920, 704)
        assert animation.size == expected_size, (path, animation.size)
        assert animation.info.get("loop") == 0, f"{path}: not an infinite loop"
        assert animation.n_frames == 90, f"{path}: expected 90 frames"
        frames, duration = [], 0
        for index in range(animation.n_frames):
            animation.seek(index)
            duration += animation.info["duration"]
            if index in (0, 22, 67, 89):
                frames.append(np.asarray(animation.convert("RGB")))
        assert duration == 6000, (path, duration)
    first, quarter, three_quarters, last = frames
    assert np.count_nonzero(first != quarter) > 1000, f"{path}: no visible ribbon motion"
    # Below the ribbon and left of its shoulder anchor, all pixels must stay fixed.
    floor, left = 410, 470
    for other in frames[1:]:
        assert np.array_equal(first[floor:], other[floor:]), f"{path}: text/landscape moved"
        assert np.array_equal(first[:, :left], other[:, :left]), f"{path}: figure moved"
    seam = np.abs(first.astype(float) - last.astype(float)).mean()
    peak = np.abs(quarter.astype(float) - three_quarters.astype(float)).mean()
    assert seam < peak * 0.35, f"{path}: visible loop seam ({seam} vs {peak})"
    assert path.stat().st_size < 10_000_000, f"{path}: animation too large"
    assert path.with_suffix(".png").is_file(), f"{path}: static alternative missing"
    print(f"PASS {path.name}: 90 frames, 6 s, fixed text/figure, seam={seam:.3f}")


if __name__ == "__main__":
    assets = Path(__file__).resolve().parents[1] / "assets"
    for theme in ("light", "dark"):
        check(assets / f"profile-{theme}-wide.gif")
