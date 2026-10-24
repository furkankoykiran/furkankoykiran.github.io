#!/usr/bin/env python3
"""Build ``data/projects.json``, the source of the project pages.

Two modes:

``--audit FILE`` / ``--inventory FILE``
    Full rebuild from a curated repository audit (categories, Turkish and
    English blurbs, featured flags) or, as a fallback, a plain repository
    inventory. Paths can also come from ``PORTFOLIO_AUDIT`` and
    ``PORTFOLIO_INVENTORY``. Live numbers are refreshed from the GitHub API
    unless ``--no-refresh`` is given.

``--refresh-only``
    Update stars and push dates in the existing file; repositories that turned
    private or became forks are removed. This is what CI runs.

Private repositories, forks and anything matching ``data/blocklist.toml`` are
never written. The tables below control ordering and grouping.

Exit codes: 0 success or skipped, 1 unexpected error, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import (
    DATA_DIR,
    ScriptError,
    add_logging_flags,
    base_url,
    dump_json,
    find_gh,
    gh_json,
    github_user,
    is_blocked,
    setup_logging,
    site_host,
    site_params,
    write_json,
)

log = logging.getLogger("projects")

DEFAULT_OUTPUT = DATA_DIR / "projects.json"

# ---------------------------------------------------------------- policy ---
# Public repositories that are not projects of their own.
EXCLUDE_REPOS = {
    "TestTestAa",  # empty
    "typescript-sdk",  # copy of the official MCP SDK
    "contextify-examples",  # placeholder repositories (licence only)
    "contextify-mcp",
    "contextify-hooks",
    "contextify-sdk",
}

CATEGORIES = [
    {"id": "mcp", "tr": "MCP ve yapay zekâ ajanları", "en": "MCP & AI agents", "color": "violet"},
    {"id": "devtools", "tr": "Geliştirici araçları", "en": "Developer tools", "color": "blue"},
    {
        "id": "trading",
        "tr": "Trading, kripto ve ödeme",
        "en": "Trading, crypto & payments",
        "color": "amber",
    },
    {"id": "web", "tr": "Oyunlar ve web uygulamaları", "en": "Games & web apps", "color": "rose"},
    {"id": "data", "tr": "Veri ve makine öğrenmesi", "en": "Data & ML", "color": "emerald"},
    {"id": "early", "tr": "İlk projeler", "en": "Early projects", "color": "slate"},
]
CATEGORY_IDS = {c["id"] for c in CATEGORIES}

# Display order of featured projects. Which projects are featured comes from
# the audit; with the inventory fallback this list decides it.
FEATURED = [
    ".claude",
    "freqtrade-mcp",
    "Quorum",
    "OmniWire-MCP",
    "DevTo-MCP",
    "telegram-wallet-p2p-sdk",
    "awesome-trending-repos",
    "EarthquakeSim",
    "ai-face-detector",
]

# Category for repositories the source does not categorise.
CATEGORY_OVERRIDES = {
    ".claude": "devtools",
    "claude-codex-gateway": "devtools",
    "claude-gemini-gateway": "devtools",
    "contextify-cli": "devtools",
    "fcode": "devtools",
    "fsecurity": "devtools",
    "awesome-trending-repos": "devtools",
    "codelyze": "web",
    "ProspectForge": "web",
    "telegram-wallet-p2p-sdk": "trading",
    "speedapi_lib": "trading",
    "Flash-Loan-Arbitrage": "trading",
    "ai-face-detector": "data",
    "Memoryze": "web",
    "EarthquakeSim": "web",
    "hues-and-cues": "web",
    "wavelength": "web",
    "XRLabLLM": "data",
}

# Early work, listed in its own group (inventory fallback only; the audit
# marks these with the "early" category).
EARLY = {
    "Telegram-Channel-Replicator",
    "Telegram-Anonymous-Chat-Bot",
    "Telegram-Blacklist-Adding-System",
    "Roblox-2010-Collector",
    "Legit-Wallet-Stealer",
    "Orekas",
    "SiparisUretimPlanlama",
    "CBU-Rent-A-Car",
    "Kodla-Gel",
    "Flash-Loan-Arbitrage",
    "speedapi_lib",
    "XRLabLLM",
}

SLUG_OVERRIDES: dict[str, str] = {}

# Homepages on these domains (besides the site's own) count as live sites.
EXTRA_OWN_DOMAINS = ("contextify.live",)

# Generic tooling that adds nothing as a technology tag.
IGNORED_TAGS = {
    "GitHub Actions",
    "Node.js/npm",
    "Python packaging (pip/pyproject)",
    "Static HTML/CSS/JS",
    "python-dotenv",
    "Make",
}


# --------------------------------------------------------------- helpers ---
def slugify(name: str) -> str:
    """Lower-case repository name with dots replaced, e.g. ``.claude`` -> ``claude``."""
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    s = name.strip().lower().replace(".", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    return s or "project"


def first_sentence(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    if len(s) > limit:
        s = s[: limit - 1].rsplit(" ", 1)[0] + "…"
    return s


def clean_desc(text: str) -> str:
    """Drop leading emoji/punctuation and collapse whitespace."""
    text = re.sub(r"^[^\w(\"'`]+", "", (text or "").strip())
    return re.sub(r"\s+", " ", text)


def live_sites() -> dict[str, str]:
    """Repositories published under this domain, from ``params.projectSites``."""
    root = base_url()
    return {name: f"{root}{name}/" for name in site_params().get("projectSites", [])}


def classify_link(url: str | None, own_domains: tuple[str, ...]) -> dict[str, str]:
    """Split a homepage URL into live site / package / model links.

    Homepages elsewhere point at upstream products and are ignored.
    """
    out: dict[str, str] = {}
    if not url:
        return out
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    if "npmjs.com" in url or "pypi.org" in url:
        out["package"] = url
    elif "kaggle.com" in url:
        out["model"] = url
    elif any(d in url for d in own_domains):
        out["live"] = url
    return out


def guess_category(name: str, topics: list[str], desc: str) -> str:
    if name in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[name]
    blob = " ".join([name, desc, *topics]).lower()
    if any(k in blob for k in ("mcp", "agent", "llm")):
        return "mcp"
    if any(k in blob for k in ("trade", "trading", "crypto", "forex", "wallet", "arbitrage")):
        return "trading"
    if any(k in blob for k in ("telegram", "bot", "automation", "scraper")):
        return "devtools"
    if any(k in blob for k in ("game", "three.js", "threejs", "web")):
        return "web"
    if any(k in blob for k in ("learning", "model", "vision")):
        return "data"
    return "devtools"


def gh_repo(gh: str, owner: str, name: str) -> dict[str, Any] | None:
    """Repository metadata, or None if it cannot be read (private, renamed, deleted)."""
    try:
        meta = gh_json(gh, ["api", f"repos/{owner}/{name}"])
    except ScriptError as exc:
        log.debug("repos/%s/%s: %s", owner, name, exc)
        return None
    return meta if isinstance(meta, dict) else None


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------- sources ---
def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScriptError(f"cannot read {path}: {exc}") from exc


def load_inventory(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    raw = load_json(path)
    return {
        r["name"]: r
        for r in raw.get("repositories", [])
        if r.get("ownership") == "owner" and r.get("visibility") == "public"
    }


def from_audit(path: Path, inventory: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows from a repository audit (schema 1.0: ``repos[]`` with current/proposed/portfolio)."""
    out = []
    for r in load_json(path).get("repos", []):
        name = r.get("repo", "")
        port = r.get("portfolio") or {}
        cat = port.get("category_key", "")
        # Forks belong to contributions; the profile repository is not a project.
        if not name or r.get("is_fork") or cat in ("oss", "profile", ""):
            continue
        if str(r.get("deletion_status", "")).upper().startswith("DELETE"):
            continue
        cur, prop = r.get("current") or {}, r.get("proposed") or {}
        inv = inventory.get(name, {})
        tech = inv.get("technologies") or {}
        dates = inv.get("dates") or {}
        desc_en = clean_desc(prop.get("description") or cur.get("description") or "")
        homepage = prop.get("homepage") or ""
        if "/projects/" in homepage:  # points back at this site
            homepage = ""
        out.append(
            {
                "name": name,
                "description": desc_en,
                "tr": port.get("blurb_tr", ""),
                "en": port.get("blurb_en", ""),
                "tr_long": (inv.get("purpose") or "").strip(),
                "en_long": desc_en,
                "category": cat,
                "tags": tech.get("frameworks_and_tools") or [],
                "topics": prop.get("topics") or cur.get("topics") or [],
                "language": tech.get("primary_language") or "",
                "homepage": homepage,
                "package_hint": cur.get("homepage") or "",
                "stars": int(cur.get("stars") or 0),
                "pushed": (dates.get("pushed_at") or "")[:10],
                "created": (dates.get("created_at") or "")[:10],
                "featured": bool(port.get("featured")),
                "early": cat == "early",
                "license": "",
            }
        )
    return out


def from_inventory(path: Path) -> list[dict[str, Any]]:
    """Rows from a plain repository inventory: public, non-fork, non-empty repositories."""
    out = []
    for r in load_json(path).get("repositories", []):
        if r.get("visibility") != "public" or r.get("is_fork") or r.get("ownership") != "owner":
            continue
        if r.get("is_empty"):
            continue
        tech = r.get("technologies") or {}
        dates = r.get("dates") or {}
        desc = clean_desc(r.get("description") or "")
        out.append(
            {
                "name": r["name"],
                "description": desc,
                "tr": first_sentence(r.get("purpose") or ""),
                "en": first_sentence(desc),
                "tr_long": (r.get("purpose") or "").strip(),
                "en_long": desc,
                "category": "",
                "tags": tech.get("frameworks_and_tools") or [],
                "topics": r.get("topics") or [],
                "language": tech.get("primary_language") or "",
                "homepage": r.get("homepage_url") or "",
                "package_hint": "",
                "stars": 0,
                "pushed": (dates.get("pushed_at") or "")[:10],
                "created": (dates.get("created_at") or "")[:10],
                "featured": r["name"] in FEATURED,
                "early": r["name"] in EARLY,
                "license": "",
            }
        )
    return out


# ------------------------------------------------------------------ build ---
def build(rows: list[dict[str, Any]], source: str, owner: str, gh: str | None) -> dict[str, Any]:
    own_domains = (site_host(), *EXTRA_OWN_DOMAINS)
    sites = live_sites()
    excluded = {*EXCLUDE_REPOS, owner}  # the profile README repository
    projects = []
    for r in rows:
        name = r["name"]
        texts = (
            name,
            r["description"],
            r["homepage"],
            r["tr"],
            r["en"],
            r["tr_long"],
            r["en_long"],
        )
        if name in excluded or is_blocked(*texts):
            continue
        meta = gh_repo(gh, owner, name) if gh else None
        if gh and meta is None:
            log.info("skipping %s: not readable via the API", name)
            continue
        if meta:
            if meta.get("private") or meta.get("fork"):
                continue
            r["stars"] = meta.get("stargazers_count", r["stars"])
            r["pushed"] = (meta.get("pushed_at") or r["pushed"])[:10]
            r["created"] = (meta.get("created_at") or r["created"])[:10]
            r["language"] = r["language"] or meta.get("language") or ""
            r["topics"] = r["topics"] or meta.get("topics") or []
            spdx = (meta.get("license") or {}).get("spdx_id")
            if spdx and spdx != "NOASSERTION":
                r["license"] = r["license"] or spdx

        links = classify_link(r["homepage"], own_domains)
        for kind, url in classify_link(r.get("package_hint"), own_domains).items():
            if kind in ("package", "model"):
                links.setdefault(kind, url)
        if is_blocked(links.get("live", "")):
            links.pop("live")
        if name in sites:
            links["live"] = sites[name]

        category = (
            r["category"]
            if r["category"] in CATEGORY_IDS
            else guess_category(name, r["topics"], r["description"])
        )
        tags: list[str] = []
        for t in [r["language"], *r["tags"]]:
            if t and t not in tags and t not in IGNORED_TAGS:
                tags.append(t)
        en = clean_desc(r["en"] or r["description"])
        tr = clean_desc(r["tr"] or en)
        projects.append(
            {
                "slug": slugify(name),
                "name": name,
                "repo": f"{owner}/{name}",
                "url": f"https://github.com/{owner}/{name}",
                "links": links,
                "stars": int(r["stars"] or 0),
                "language": r["language"],
                "tags": tags[:8],
                "topics": r["topics"][:10],
                "category": category,
                "featured": bool(r["featured"]),
                "featured_rank": FEATURED.index(name) if name in FEATURED else 99,
                "early": bool(r["early"]),
                "license": r["license"],
                "created": r["created"],
                "pushed": r["pushed"],
                "tr": {"summary": tr, "description": (r["tr_long"] or tr).strip()},
                "en": {"summary": en, "description": (r["en_long"] or en).strip()},
            }
        )

    # Featured order first, then stars; most recent push breaks ties.
    projects.sort(key=lambda p: p["pushed"], reverse=True)
    projects.sort(key=lambda p: (p["early"], p["featured_rank"], -p["stars"]))
    used: set[str] = set()
    for p in projects:
        base, i = p["slug"], 2
        while p["slug"] in used:
            p["slug"] = f"{base}-{i}"
            i += 1
        used.add(p["slug"])

    return {
        "generated_at": now_iso(),
        "source": source,
        "categories": CATEGORIES,
        "projects": projects,
    }


def refresh(path: Path, owner: str, gh: str | None) -> dict[str, Any] | None:
    """Refresh live numbers in an existing file. Returns None if nothing can be done."""
    if not path.is_file():
        log.warning("%s does not exist; nothing to refresh", path)
        return None
    if not gh:
        log.warning("GitHub CLI not found (install gh or set GH_PATH); keeping existing data")
        return None
    data = load_json(path)
    kept, missing = [], 0
    for p in data.get("projects", []):
        meta = gh_repo(gh, owner, p["name"])
        if meta is None:
            missing += 1
        elif meta.get("private") or meta.get("fork"):
            log.info("removing %s: no longer a public source repository", p["name"])
            continue
        else:
            p["stars"] = meta.get("stargazers_count", p.get("stars", 0))
            p["pushed"] = (meta.get("pushed_at") or p.get("pushed", ""))[:10]
        kept.append(p)
    if kept and missing == len(kept):
        log.warning("GitHub API unreachable; keeping existing data")
        return None
    if missing:
        log.warning("%d repositories could not be read; their entries are kept unchanged", missing)
    data["projects"] = kept
    data["refreshed_at"] = now_iso()
    return data


# ------------------------------------------------------------------- main ---
def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or refresh data/projects.json.",
        epilog="Either --refresh-only or a source (--audit / --inventory) is required.",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=os.environ.get("PORTFOLIO_AUDIT") or None,
        help="curated repository audit JSON (default: $PORTFOLIO_AUDIT)",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=os.environ.get("PORTFOLIO_INVENTORY") or None,
        help="repository inventory JSON, used for extra metadata or as the fallback source "
        "(default: $PORTFOLIO_INVENTORY)",
    )
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="only refresh stars and push dates in the existing output file",
    )
    parser.add_argument(
        "--no-refresh", action="store_true", help="do not query the GitHub API during a rebuild"
    )
    parser.add_argument(
        "--user",
        help="GitHub user (default: $PORTFOLIO_GITHUB_USER or author.githubUser in params.toml)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="output file (default: %(default)s)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the result instead of writing it"
    )
    add_logging_flags(parser)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    owner = args.user or github_user()

    if args.refresh_only:
        data = refresh(args.output, owner, find_gh())
        if data is None:
            return 0
        volatile: tuple[str, ...] = ("generated_at", "refreshed_at")
    else:
        if args.audit and args.audit.is_file():
            source, rows = "repo-audit", from_audit(args.audit, load_inventory(args.inventory))
        elif args.inventory and args.inventory.is_file():
            if args.audit:
                log.warning("audit %s not found; using the inventory", args.audit)
            source, rows = "inventory", from_inventory(args.inventory)
        else:
            raise ScriptError("no source: pass --audit or --inventory (or use --refresh-only)")
        gh = None if args.no_refresh else find_gh()
        if not gh and not args.no_refresh:
            log.warning("GitHub CLI not found; using the numbers from the source file")
        data = build(rows, source, owner, gh)
        volatile = ("generated_at",)

    if args.dry_run:
        sys.stdout.buffer.write(dump_json(data).encode("utf-8"))
    elif write_json(args.output, data, volatile=volatile):
        log.info("%d projects -> %s", len(data["projects"]), args.output)
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
