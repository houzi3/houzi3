"""Refresh public GitHub totals without modifying the animated profile artwork."""

import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def github(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-totals",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def collect_totals(owner):
    user = github(f"users/{quote(owner, safe='')}")
    repositories = {}
    page = 1
    while True:
        batch = github(
            f"users/{quote(owner, safe='')}/repos?type=owner&per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise ValueError("Expected a list of public repositories")
        for repo in batch:
            if not repo["private"] and repo["owner"]["id"] == user["id"]:
                repositories[repo["id"]] = repo
        if len(batch) < 100:
            break
        page += 1
    totals = {
        "stars": sum(repo["stargazers_count"] for repo in repositories.values()),
        "forks": sum(repo["forks_count"] for repo in repositories.values()),
        "followers": user["followers"],
        "repositories": len(repositories),
    }
    if any(type(value) is not int or value < 0 for value in totals.values()):
        raise ValueError("GitHub returned invalid totals")
    if totals["repositories"] != user["public_repos"]:
        raise ValueError("Repository listing is incomplete; keeping existing totals")
    return totals


def totals_description(totals):
    return (
        f"{totals['stars']:,} stars · {totals['forks']:,} forks · "
        f"{totals['followers']:,} followers · "
        f"{totals['repositories']:,} public repos"
    )


def render_stats(totals):
    # Bind visibility explicitly to GitHub's selected theme, including manual
    # overrides. The wrapper links are required because GitHub applies theme
    # visibility to href; picture sources only handle layout and motion.
    heroes = []
    statistics = []
    for theme in ("light", "dark"):
        fragment = f"#gh-{theme}-mode-only"
        hero = "\n".join([
            "<picture>",
            '  <source media="(max-width: 600px) and (prefers-reduced-motion: reduce)" '
            f'srcset="assets/profile-{theme}-mobile.png{fragment}">',
            '  <source media="(prefers-reduced-motion: reduce)" '
            f'srcset="assets/profile-{theme}.png{fragment}">',
            '  <source media="(max-width: 600px)" '
            f'srcset="assets/profile-{theme}-mobile.gif{fragment}">',
            f'  <img src="assets/profile-{theme}.gif{fragment}" width="960" '
            'alt="Jaeger · 一只好奇的猴子。Software engineer in Shanghai. '
            'Sun Wukong stands above the clouds with a gently flowing red ribbon.">',
            "</picture>",
        ])
        heroes.append(f'<a href="assets/profile-{theme}.gif{fragment}">{hero}</a>')
        stats = "\n".join([
            "<picture>",
            '  <source media="(max-width: 600px)" '
            f'srcset="assets/stats-{theme}-mobile.svg{fragment}">',
            f'  <img src="assets/stats-{theme}.svg{fragment}" width="960" '
            f'alt="{totals_description(totals)}">',
            "</picture>",
        ])
        statistics.append(f'<a href="assets/stats-{theme}.svg{fragment}">{stats}</a>')
    # A block container keeps Markdown from splitting the first inline link and
    # picture into separate paragraphs. Adjacent themes leave no blank rows.
    return "<div>\n" + "".join(heroes) + "\n<br>\n" + "".join(statistics) + "\n</div>"


def render_artwork(totals, dark=True, mobile=False):
    """Render only the statistics strip; never overwrite the animated artwork."""
    width, height = (480, 48) if mobile else (960, 56)
    background = "#0d1117" if dark else "#ffffff"
    primary = "#e8e6e1" if dark else "#252525"
    secondary = "#a5abb3" if dark else "#72757a"
    rule = "#343a42" if dark else "#dce0e4"
    number_size, label_size = (16, 14) if mobile else (18, 14)
    # Each value and label is one inline group on a shared text baseline.
    metrics = []
    for index, (key, label) in enumerate((
        ("stars", "stars"), ("forks", "forks"),
        ("followers", "followers"), ("repositories", "public repos"),
    )):
        if index:
            metrics.append(f'<tspan fill="{secondary}">  ·  </tspan>')
        metrics.append(
            f'<tspan fill="{primary}" font-size="{number_size}">'
            f'{totals[key]:,}</tspan>'
            f'<tspan fill="{secondary}" font-size="{label_size}"> {label}</tspan>'
        )
    description = totals_description(totals)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">Public GitHub totals</title>
<desc id="description">{description}</desc>
<rect width="{width}" height="{height}" fill="{background}"/>
<path d="M{24 if mobile else 52} 1 H{width - (24 if mobile else 52)}" stroke="{rule}" stroke-width="1"/>
<text x="{width / 2:g}" y="{29 if mobile else 32}" text-anchor="middle" font-family="'Helvetica Neue', 'Segoe UI', Arial, sans-serif" font-weight="400" xml:space="preserve">{"".join(metrics)}</text>
</svg>\n'''


def update_artwork(directory, totals):
    directory.mkdir(parents=True, exist_ok=True)
    for dark in (False, True):
        theme = "dark" if dark else "light"
        for mobile in (False, True):
            suffix = "-mobile" if mobile else ""
            path = directory / f"stats-{theme}{suffix}.svg"
            content = render_artwork(totals, dark=dark, mobile=mobile)
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                path.write_text(content, encoding="utf-8")
                print(f"Updated {theme}{suffix} public GitHub totals")


def update_readme(path, totals):
    original = path.read_text(encoding="utf-8")
    start, end = "<!-- stats:start -->", "<!-- stats:end -->"
    if original.count(start) != 1 or original.count(end) != 1:
        raise ValueError("Expected one pair of stats markers")
    before, rest = original.split(start, 1)
    _, after = rest.split(end, 1)
    updated = f"{before}{start}\n{render_stats(totals)}\n{end}{after}"
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        print("Updated public GitHub totals")
    else:
        print("Public GitHub totals are unchanged")


if __name__ == "__main__":
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "houzi3")
    root = Path(__file__).resolve().parents[1]
    totals = collect_totals(owner)
    update_readme(root / "README.md", totals)
    update_artwork(root / "assets", totals)
