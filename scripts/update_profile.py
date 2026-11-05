"""Refresh public GitHub totals without changing the hand-written introduction."""

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
    values = " | ".join(
        f"**{totals[key]:,}**" for key in ("stars", "forks", "followers", "repositories")
    )
    return (
        "| Stars | Forks | Followers | Public repositories |\n"
        "| :---: | :---: | :---: | :---: |\n"
        f"| {values} |"
    )


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
    update_readme(Path(__file__).resolve().parents[1] / "README.md", collect_totals(owner))
