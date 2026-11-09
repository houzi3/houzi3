"""Regression checks for theme selection and safe scheduled totals updates."""

from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_profile.py"
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
    def test_readme_selects_artwork_by_github_theme_and_motion_preference(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        hero, _, _ = readme.partition("<!-- stats:start -->")
        parser = Pictures()
        parser.feed(hero)
        self.assertEqual(len(parser.pictures), 2)
        self.assertNotIn("prefers-color-scheme", hero)
        self.assertNotIn("max-width", hero)
        for index, theme in enumerate(("light", "dark")):
            fragment = f"#gh-{theme}-mode-only"
            expected_svg = f"assets/ribbon-{theme}.svg{fragment}"
            self.assertEqual(parser.picture_links[index], expected_svg)
            source, image = parser.pictures[index]
            self.assertEqual(source["media"], "(prefers-reduced-motion: reduce)")
            self.assertEqual(source["srcset"], f"assets/ribbon-{theme}.jpg{fragment}")
            self.assertEqual(image["src"], expected_svg)
            self.assertEqual(image["width"], "960")
            self.assertIn("Wukong", image["alt"])
            self.assertNotIn("Jaeger", image["alt"])
        self.assertIn("<strong>Jaeger</strong> · 一只好奇的猴子。", hero)
        self.assertIn("<sub>Software engineer in Shanghai.</sub>", hero)

    def test_statistics_are_one_paragraph_of_selectable_text(self):
        self.assertEqual(profile.render_stats(TOTALS),
                         '<p align="center"><sub><strong>11,047</strong>&nbsp;stars · '
                         '<strong>2,082</strong>&nbsp;forks · <strong>850</strong>&nbsp;followers · '
                         '<strong>32</strong>&nbsp;repos</sub></p>')

    def test_refresh_only_replaces_stats_marker_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            published = (ROOT / "README.md").read_text(encoding="utf-8")
            before, _, rest = published.partition("<!-- stats:start -->")
            _, _, after = rest.partition("<!-- stats:end -->")
            readme.write_text(f"{before}<!-- stats:start -->\nold\n<!-- stats:end -->{after}",
                              encoding="utf-8")
            profile.update_readme(readme, TOTALS)
            stats = profile.render_stats(TOTALS)
            self.assertEqual(readme.read_text(encoding="utf-8"),
                             f"{before}<!-- stats:start -->\n{stats}\n<!-- stats:end -->{after}")
            changed_at = readme.stat().st_mtime_ns
            profile.update_readme(readme, TOTALS)
            self.assertEqual(readme.stat().st_mtime_ns, changed_at)
            self.assertEqual(list(root.iterdir()), [readme])

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
