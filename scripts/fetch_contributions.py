#!/usr/bin/env python3
"""Collect merged pull requests in repositories the author does not own.

Writes ``data/contributions.json``, grouped by repository and sorted by stars.
Only public repositories are kept; anything matching ``data/blocklist.toml``
or an excluded repository is dropped.

The GitHub CLI (``gh``) does the API calls: locally it uses your ``gh``
login, in CI set ``GH_TOKEN``. If GitHub cannot be reached the existing file
is kept and the script exits 0, so a scheduled build still succeeds with the
last known data. Reruns with unchanged results leave the file untouched.

Exit codes: 0 success or skipped, 1 unexpected error, 2 usage error.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import (
    DATA_DIR,
    ScriptError,
    add_logging_flags,
    dump_json,
    find_gh,
    gh_json,
    github_user,
    is_blocked,
    setup_logging,
    write_json,
)

log = logging.getLogger("contributions")

DEFAULT_OUTPUT = DATA_DIR / "contributions.json"
DEFAULT_HIGHLIGHT_MIN_STARS = 50
DEFAULT_LIMIT = 500


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write merged pull requests in other people's repositories to "
        "data/contributions.json.",
    )
    parser.add_argument(
        "--user",
        help="GitHub user (default: $PORTFOLIO_GITHUB_USER or author.githubUser in params.toml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="output file (default: %(default)s)",
    )
    parser.add_argument(
        "--highlight-min-stars",
        type=int,
        default=int(os.environ.get("CONTRIB_HIGHLIGHT_MIN_STARS", DEFAULT_HIGHLIGHT_MIN_STARS)),
        help="repositories with at least this many stars are highlighted (default: %(default)s)",
    )
    parser.add_argument(
        "--exclude-repo",
        action="append",
        default=[],
        metavar="OWNER/NAME",
        help="skip a repository; repeatable. $CONTRIB_EXCLUDE_REPOS adds a comma-separated list",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="maximum number of pull requests to fetch (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the result instead of writing it"
    )
    add_logging_flags(parser)
    return parser.parse_args(argv)


def excluded_repos(args: argparse.Namespace) -> set[str]:
    extra = [r for r in os.environ.get("CONTRIB_EXCLUDE_REPOS", "").split(",") if r.strip()]
    return {r.strip().lower() for r in (*args.exclude_repo, *extra)}


def collect(gh: str, user: str, args: argparse.Namespace) -> dict[str, Any]:
    prs = gh_json(
        gh,
        [
            "search",
            "prs",
            "--author",
            user,
            "--merged",
            "--limit",
            str(args.limit),
            "--json",
            "repository,title,url,number,closedAt",
            "--",
            f"-user:{user}",
        ],
    )
    skip = excluded_repos(args)

    by_repo: dict[str, list[dict[str, Any]]] = {}
    for pr in prs or []:
        full = pr["repository"]["nameWithOwner"]
        owner = full.split("/")[0].lower()
        if owner == user.lower() or full.lower() in skip:
            continue
        if is_blocked(full, pr.get("title", "")):
            continue
        by_repo.setdefault(full, []).append(pr)

    repos = []
    for full, items in sorted(by_repo.items()):
        try:
            meta = gh_json(gh, ["api", f"repos/{full}"])
        except ScriptError as exc:
            log.warning("dropping %s: %s", full, exc)
            continue
        if meta.get("private") or meta.get("visibility", "public") != "public":
            continue
        if is_blocked(meta.get("description"), meta.get("homepage")):
            continue
        prs_out = sorted(
            (
                {
                    "title": p["title"].strip(),
                    "url": p["url"],
                    "number": p["number"],
                    "merged_at": (p.get("closedAt") or "")[:10],
                }
                for p in items
            ),
            key=lambda p: (p["merged_at"], p["number"]),
            reverse=True,
        )
        stars = int(meta.get("stargazers_count", 0))
        repos.append(
            {
                "repo": meta["full_name"],
                "name": meta["name"],
                "owner": meta["owner"]["login"],
                "url": meta["html_url"],
                "description": (meta.get("description") or "").strip(),
                "stars": stars,
                "language": meta.get("language") or "",
                "highlight": stars >= args.highlight_min_stars,
                "pr_count": len(prs_out),
                "last_merged": prs_out[0]["merged_at"] if prs_out else "",
                "prs": prs_out,
            }
        )

    repos.sort(key=lambda r: (r["stars"], r["last_merged"]), reverse=True)
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author": user,
        "total_prs": sum(r["pr_count"] for r in repos),
        "total_repos": len(repos),
        "total_stars": sum(r["stars"] for r in repos if r["highlight"]),
        "repos": repos,
    }


def run(args: argparse.Namespace) -> int:
    user = args.user or github_user()
    gh = find_gh()
    if not gh:
        log.warning("GitHub CLI not found (install gh or set GH_PATH); keeping existing data")
        return 0
    try:
        data = collect(gh, user, args)
    except ScriptError as exc:
        log.warning("GitHub API unavailable, keeping existing data: %s", exc)
        return 0

    if args.dry_run:
        sys.stdout.buffer.write(dump_json(data).encode("utf-8"))
        return 0
    if not data["repos"] and args.output.exists():
        log.warning("empty result, keeping existing data")
        return 0
    if write_json(args.output, data, volatile=("generated_at",)):
        log.info(
            "%d PRs in %d repositories -> %s", data["total_prs"], data["total_repos"], args.output
        )
    else:
        log.info("no changes in %s", args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose, args.quiet)
    try:
        return run(args)
    except ScriptError as exc:
        log.error("%s", exc)
        return 2
    except Exception:
        log.exception("unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
