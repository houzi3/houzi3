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
TOTALS = {"stars": 11047, "forks": 2082, "followers": 850, "repositories": 32}


class Pictures(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pictures = []
        self.picture_links = []
        self.active_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.active_href = dict(attrs).get("href")
        elif tag == "picture":
            self.pictures.append([])
            self.picture_links.append(self.active_href)
        elif tag in ("source", "img"):
            self.pictures[-1].append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == "a":
            self.active_href = None


class ProfileTests(unittest.TestCase):
    def test_theme_fragments_follow_github_theme_without_os_color_queries(self):
        rendered = profile.render_stats(TOTALS)
        self.assertTrue(rendered.startswith("<div>\n"))
        self.assertTrue(rendered.endswith("\n</div>"))
        self.assertNotIn("prefers-color-scheme", rendered)
        self.assertEqual(rendered.count("</picture></a><a "), 2)
        self.assertEqual(rendered.count("<br>"), 1)
        parser = Pictures()
        parser.feed(rendered)
        self.assertEqual(len(parser.pictures), 4)
        for index, picture in enumerate(parser.pictures):
            theme = "light" if index % 2 == 0 else "dark"
            fragment = f"#gh-{theme}-mode-only"
            path = f"profile-{theme}-wide.gif" if index < 2 else f"stats-{theme}.svg"
            self.assertEqual(parser.picture_links[index], f"assets/{path}{fragment}")
            for image in picture:
                self.assertTrue(image.get("srcset", image.get("src")).endswith(fragment))

    def test_same_wide_artwork_is_used_for_every_viewport(self):
        rendered = profile.render_stats(TOTALS)
        self.assertNotIn("max-width", rendered)
        self.assertNotIn("-mobile.", rendered)
        parser = Pictures()
        parser.feed(rendered)
        for index, theme in enumerate(("light", "dark")):
            hero = parser.pictures[index]
            fragment = f"#gh-{theme}-mode-only"
            self.assertEqual(len(hero), 2)
            self.assertEqual(hero[0]["media"], "(prefers-reduced-motion: reduce)")
            self.assertEqual(hero[0]["srcset"], f"assets/profile-{theme}-wide.png{fragment}")
            self.assertEqual(hero[1]["src"], f"assets/profile-{theme}-wide.gif{fragment}")
            self.assertEqual(hero[1]["width"], "960")
            stats = parser.pictures[index + 2]
            self.assertEqual(len(stats), 1)
            self.assertEqual(stats[0]["src"], f"assets/stats-{theme}.svg{fragment}")
            self.assertIn("11,047 stars", stats[0]["alt"])

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
            artwork = assets / "profile-light-wide.gif"
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
