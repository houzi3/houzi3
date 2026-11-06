"""Regression checks for theme selection and safe scheduled totals updates."""

from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_profile.py"
SPEC = importlib.util.spec_from_file_location("update_profile", SCRIPT)
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)
TOTALS = {"stars": 11049, "forks": 2084, "followers": 850, "repositories": 32}


class Pictures(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pictures = []

    def handle_starttag(self, tag, attrs):
        if tag == "picture":
            self.pictures.append([])
        elif tag in ("source", "img"):
            self.pictures[-1].append(dict(attrs))


class ProfileTests(unittest.TestCase):
    def test_specific_static_sources_precede_animated_theme_fallbacks(self):
        parser = Pictures()
        parser.feed(profile.render_stats(TOTALS))
        hero, stats = parser.pictures
        self.assertEqual(len(hero), 9)
        for index, source in enumerate(hero[:-1]):
            self.assertEqual("prefers-reduced-motion: reduce" in source["media"], index < 4)
            self.assertEqual(source["srcset"].endswith(".png"), index < 4)
            self.assertEqual("max-width: 600px" in source["media"], index % 4 < 2)
            self.assertEqual("-mobile." in source["srcset"], index % 4 < 2)
        self.assertEqual(hero[0]["srcset"], "assets/profile-dark-mobile.png")
        self.assertEqual(hero[-1]["src"], "assets/profile-light.gif")
        self.assertEqual(stats[0]["srcset"], "assets/stats-dark-mobile.svg")
        self.assertEqual(stats[-1]["src"], "assets/stats-light.svg")
        self.assertIn("11,049 stars", stats[-1]["alt"])

    def test_every_statistics_variant_has_one_shared_text_baseline(self):
        ns = {"svg": "http://www.w3.org/2000/svg"}
        for dark in (False, True):
            for mobile in (False, True):
                with self.subTest(dark=dark, mobile=mobile):
                    root = ET.fromstring(profile.render_artwork(TOTALS, dark, mobile))
                    lines = root.findall("svg:text", ns)
                    self.assertEqual(len(lines), 1)
                    actual = re.sub(r"\s+", " ", "".join(lines[0].itertext())).strip()
                    self.assertEqual(actual, profile.totals_description(TOTALS))
                    self.assertTrue(all("y" not in span.attrib for span in lines[0]))
                    self.assertEqual(root.attrib["width"], "480" if mobile else "960")
                    self.assertEqual(root.find("svg:rect", ns).attrib["fill"],
                                     "#0d1117" if dark else "#ffffff")

    def test_refresh_is_idempotent_and_preserves_artwork_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            artwork = assets / "profile-light.gif"
            artwork.write_bytes(b"unchanged animation")
            readme = root / "README.md"
            readme.write_text("<!-- stats:start -->\nold\n<!-- stats:end -->\nBlog and X\n")
            profile.update_readme(readme, TOTALS)
            profile.update_artwork(assets, TOTALS)
            before = {path.name: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
            profile.update_readme(readme, TOTALS)
            profile.update_artwork(assets, TOTALS)
            after = {path.name: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(artwork.read_bytes(), b"unchanged animation")
            self.assertIn("Blog and X", readme.read_text())
            self.assertEqual(len(list(assets.glob("stats-*.svg"))), 4)

    def test_collect_totals_paginates_deduplicates_and_filters_ownership(self):
        def repo(index, owner=7, private=False):
            return {"id": index, "owner": {"id": owner}, "private": private,
                    "stargazers_count": index, "forks_count": 1}

        user = {"id": 7, "public_repos": 101, "followers": 850}
        batches = [user, [repo(i) for i in range(100)],
                   [repo(0), repo(100), repo(999, owner=8), repo(1000, private=True)]]
        with patch.object(profile, "github", side_effect=batches) as github:
            totals = profile.collect_totals("houzi3")
        self.assertEqual(totals, {"stars": 5050, "forks": 101,
                                  "followers": 850, "repositories": 101})
        self.assertEqual(github.call_count, 3)
        self.assertIn("page=2", github.call_args.args[0])

    def test_incomplete_repository_results_are_rejected(self):
        with patch.object(profile, "github", side_effect=[
            {"id": 7, "public_repos": 1, "followers": 850}, [],
        ]):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                profile.collect_totals("houzi3")


if __name__ == "__main__":
    unittest.main()
