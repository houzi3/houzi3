"""Render the profile artwork and refresh public GitHub totals."""

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


def render_stats(totals):
    description = (
        "Jaeger · 一只好奇的猴子。Software engineer in Shanghai. "
        f"{totals['stars']:,} stars, {totals['forks']:,} forks, "
        f"{totals['followers']:,} followers, {totals['repositories']:,} public repositories."
    )
    return (
        '<picture>\n'
        '  <source media="(max-width: 600px)" srcset="assets/profile-dark-mobile.svg">\n'
        f'  <img src="assets/profile-dark.svg" width="960" alt="{description}">\n'
        '</picture>'
    )


def render_artwork(totals, dark=True, mobile=False):
    width, height = (480, 560) if mobile else (960, 480)
    right = 432 if mobile else 872
    avatar_transform = (
        "translate(-74 -4) scale(.6)" if mobile
        else "translate(368 0) scale(.6)"
    )
    name_y, tagline_y, bio_y = (215, 258, 294) if mobile else (216, 263, 301)
    name_size = 54 if mobile else 62
    tagline_size = 25 if mobile else 28
    rule_y = 340 if mobile else 352
    metrics = "\n".join(
        f'<g text-anchor="end" transform="translate('
        f'{216 + (index % 2) * 216 if mobile else 224 + index * 216} '
        f'{403 + (index // 2) * 94 if mobile else 411})">'
        f'<text class="number">{totals[key]:,}</text>'
        f'<text class="label" y="27">{label}</text></g>'
        for index, (key, label) in enumerate((
            ("stars", "stars"), ("forks", "forks"),
            ("followers", "followers"), ("repositories", "public repos"),
        ))
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">Jaeger — 一只好奇的猴子。</title>
<desc id="description">Software engineer in Shanghai. {totals['stars']:,} stars, {totals['forks']:,} forks, {totals['followers']:,} followers and {totals['repositories']:,} public repositories. A silver monkey on a deep black background.</desc>
<style>
  text {{ font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif; fill: #e9e9e9; font-weight: 300; }}
  .name {{ font-size: {name_size}px; letter-spacing: 3px; }}
  .tagline {{ font-family: 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif; font-size: {tagline_size}px; letter-spacing: 2px; }}
  .bio {{ font-size: {17 if mobile else 18}px; letter-spacing: .6px; fill: #a7a7a7; }}
  .number {{ font-size: {34 if mobile else 35}px; letter-spacing: .5px; }}
  .label {{ font-size: {17 if mobile else 16}px; letter-spacing: .5px; fill: #a7a7a7; }}
  .eyes {{ transform-box: fill-box; transform-origin: center; animation: blink 9s infinite; }}
  @keyframes blink {{ 0%, 43%, 47%, 100% {{ transform: scaleY(1); }} 45% {{ transform: scaleY(.15); }} }}
  @media (prefers-reduced-motion: reduce) {{ .eyes {{ animation: none; }} }}
</style>
<rect width="{width}" height="{height}" fill="#151515"/>

<g transform="{avatar_transform}" stroke="#aeb2b8" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
  <ellipse cx="687" cy="121" rx="23" ry="25" fill="#151515"/>
  <ellipse cx="820" cy="121" rx="23" ry="25" fill="#151515"/>
  <path d="M688 109 C678 108 676 129 687 132 M820 109 C831 108 832 129 821 132" fill="none" stroke="#72777e"/>
  <path d="M691 113 C685 70 714 47 752 49 C793 44 824 75 816 119 C825 151 800 179 756 181 C713 181 682 154 691 113 Z" fill="#1e1e1e"/>
  <path d="M744 53 C746 38 758 36 765 44 M754 50 C768 34 779 40 778 48" fill="none"/>
  <path d="M754 95 C736 73 703 86 707 115 C693 137 713 164 754 164 C793 164 813 137 800 116 C805 87 773 73 754 95 Z" fill="#151515" stroke="#72777e" stroke-width="2"/>
  <g class="eyes" fill="#cfd1d4" stroke="none">
    <ellipse cx="734" cy="119" rx="3.8" ry="5.7"/>
    <ellipse cx="775" cy="116" rx="3.8" ry="5.7"/>
  </g>
  <path d="M726 102 Q732 98 739 100 M768 98 Q775 95 781 99" fill="none" stroke-width="2.2"/>
  <path d="M749 135 Q754 138 759 134 M738 145 Q755 158 774 140" fill="none" stroke-width="2.2"/>
</g>

<text class="name" x="{right}" y="{name_y}" text-anchor="end">Jaeger</text>
<text class="tagline" x="{right}" y="{tagline_y}" text-anchor="end">一只好奇的猴子。</text>
<text class="bio" x="{right}" y="{bio_y}" text-anchor="end">Software engineer in Shanghai.</text>
<path d="M{40 if mobile else 88} {rule_y} H{right}" fill="none" stroke="#525252" stroke-width="1"/>
{metrics}
</svg>\n'''


def update_artwork(directory, totals):
    directory.mkdir(parents=True, exist_ok=True)
    for mobile in (False, True):
        suffix = "-mobile" if mobile else ""
        path = directory / f"profile-dark{suffix}.svg"
        content = render_artwork(totals, mobile=mobile)
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            print(f"Updated black{suffix} profile artwork")


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
