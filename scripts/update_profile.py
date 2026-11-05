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
        '  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="assets/profile-dark-mobile.svg">\n'
        '  <source media="(max-width: 600px)" srcset="assets/profile-light-mobile.svg">\n'
        '  <source media="(prefers-color-scheme: dark)" srcset="assets/profile-dark.svg">\n'
        f'  <img src="assets/profile-light.svg" width="960" alt="{description}">\n'
        '</picture>'
    )


def render_artwork(totals, dark=False, mobile=False):
    background, ink, muted, rule = (
        ("#0d1117", "#eeeaf8", "#b0adbf", "#303341") if dark
        else ("#ffffff", "#303348", "#77798a", "#e9e7ee")
    )
    accent = "#c1b2eb" if dark else "#74649c"
    width, height = (480, 490) if mobile else (960, 408)
    name_x, name_y = (22, 113) if mobile else (37, 146)
    name_size, chinese_size = (74, 24) if mobile else (100, 29)
    text_x, chinese_y, bio_y = (24, 166, 210) if mobile else (43, 199, 241)
    mascot_transform = "translate(-100 18) scale(.6)" if mobile else "translate(0 0)"
    line = "M24 254 H456" if mobile else "M40 290 H920"
    metrics = "\n".join(
        f'<g transform="translate({24 + (index % 2) * 240 if mobile else 40 + index * 230} {318 + (index // 2) * 105 if mobile else 350})">'
        f'<text class="number" y="0">{totals[key]:,}</text>'
        f'<text class="label" y="29">{label}</text></g>'
        for index, (key, label) in enumerate((
            ("stars", "stars"), ("forks", "forks"),
            ("followers", "followers"), ("repositories", "public repositories"),
        ))
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">Jaeger — 一只好奇的猴子。</title>
<desc id="description">Software engineer in Shanghai. {totals['stars']:,} stars, {totals['forks']:,} forks, {totals['followers']:,} followers and {totals['repositories']:,} public repositories. A curious little monkey holds a peach.</desc>
<style>
  text {{ font-family: 'Avenir Next', Avenir, 'Trebuchet MS', sans-serif; fill: {ink}; }}
  .name {{ font-size: {name_size}px; font-weight: 700; letter-spacing: -4px; }}
  .chinese {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; font-size: {chinese_size}px; font-weight: 500; fill: {accent}; }}
  .bio {{ font-size: 19px; fill: {muted}; }}
  .number {{ font-size: 39px; font-weight: 600; letter-spacing: -1px; }}
  .label {{ font-size: {18 if mobile else 16}px; fill: {muted}; }}
  .eyes {{ transform-box: fill-box; transform-origin: center; animation: blink 8s infinite; }}
  @keyframes blink {{ 0%, 43%, 47%, 100% {{ transform: scaleY(1); }} 45% {{ transform: scaleY(.12); }} }}
  @media (prefers-reduced-motion: reduce) {{ .eyes {{ animation: none; }} }}
</style>
<rect width="{width}" height="{height}" fill="{background}"/>
<text class="name" x="{name_x}" y="{name_y}">Jaeger<tspan fill="{accent}">.</tspan></text>
<text class="chinese" x="{text_x}" y="{chinese_y}">一只好奇的猴子。</text>
<text class="bio" x="{text_x}" y="{bio_y}">Software engineer in Shanghai.</text>

<g transform="{mascot_transform}">
<g stroke="#464057" stroke-width="3.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M795 235 C867 255 894 211 875 189 C860 171 836 184 847 202 C852 210 863 209 866 202" fill="none" stroke="#9787b8" stroke-width="14"/>
  <path d="M719 171 C688 188 686 229 708 251 C722 266 783 268 803 250 C823 232 815 185 790 173 Z" fill="#9787b8"/>
  <ellipse cx="754" cy="224" rx="35" ry="34" fill="#f7e6ce" stroke="none"/>
  <path d="M715 244 C700 241 685 251 691 261 C697 270 724 264 734 258" fill="#9787b8"/>
  <path d="M782 251 C797 242 815 247 816 257 C815 269 789 267 777 260" fill="#9787b8"/>
  <ellipse cx="687" cy="121" rx="23" ry="25" fill="#9787b8"/>
  <ellipse cx="820" cy="121" rx="23" ry="25" fill="#9787b8"/>
  <ellipse cx="688" cy="122" rx="11" ry="13" fill="#e5c8d8" stroke="none"/>
  <ellipse cx="819" cy="122" rx="11" ry="13" fill="#e5c8d8" stroke="none"/>
  <path d="M691 113 C685 70 714 47 752 49 C793 44 824 75 816 119 C825 151 800 179 756 181 C713 181 682 154 691 113 Z" fill="#9787b8"/>
  <path d="M744 53 C746 38 758 36 765 44 M754 50 C768 34 779 40 778 48" fill="none"/>
  <path d="M754 95 C736 73 703 86 707 115 C693 137 713 164 754 164 C793 164 813 137 800 116 C805 87 773 73 754 95 Z" fill="#f7e6ce" stroke="none"/>
  <g class="eyes" fill="#464057" stroke="none">
    <ellipse cx="734" cy="119" rx="4.5" ry="6.8"/>
    <ellipse cx="775" cy="116" rx="4.5" ry="6.8"/>
  </g>
  <path d="M726 102 Q732 98 739 100 M768 98 Q775 95 781 99" fill="none" stroke-width="2.8"/>
  <path d="M749 135 Q754 138 759 134 M738 145 Q755 158 774 140" fill="none" stroke-width="2.8"/>
  <ellipse cx="717" cy="137" rx="8" ry="4.8" fill="#edb7b7" stroke="none"/>
  <ellipse cx="791" cy="134" rx="8" ry="4.8" fill="#edb7b7" stroke="none"/>
  <path d="M710 187 C694 200 698 218 730 226 M795 187 C810 203 800 222 778 227" fill="none" stroke="#9787b8" stroke-width="18"/>
  <path d="M755 208 C730 191 710 212 726 234 C735 249 751 247 755 245 C763 249 779 247 788 233 C801 209 778 191 755 208 Z" fill="#f2b2ac" stroke-width="3"/>
  <path d="M755 210 C760 221 758 232 754 238" fill="none" stroke="#d88d98" stroke-width="2.3"/>
  <path d="M756 207 C753 193 768 184 781 187 C777 202 765 205 756 207 Z" fill="#8daf96" stroke-width="2.6"/>
  <ellipse cx="726" cy="222" rx="10" ry="8" fill="#f7e6ce" stroke-width="2.8"/>
  <ellipse cx="784" cy="222" rx="10" ry="8" fill="#f7e6ce" stroke-width="2.8"/>
</g>
<path d="M850 73 Q853 63 861 62 M866 86 l9 -2" fill="none" stroke="{accent}" stroke-width="3.5" stroke-linecap="round"/>
</g>
<path d="{line}" stroke="{rule}"/>
{metrics}
</svg>\n'''


def update_artwork(directory, totals):
    directory.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        for mobile in (False, True):
            suffix = "-mobile" if mobile else ""
            path = directory / f"profile-{theme}{suffix}.svg"
            content = render_artwork(totals, dark=theme == "dark", mobile=mobile)
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                path.write_text(content, encoding="utf-8")
                print(f"Updated {theme}{suffix} profile artwork")


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
