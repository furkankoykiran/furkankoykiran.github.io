"""Shared helpers for the site's maintenance scripts.

Paths, site settings and the GitHub user are derived from the repository
itself (``config/_default/*.toml``), so the scripts work from any checkout
on any platform without editing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tomllib
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config" / "_default"
DATA_DIR = REPO_ROOT / "data"
BLOCKLIST_FILE = DATA_DIR / "blocklist.toml"


class ScriptError(RuntimeError):
    """An expected failure that should end the script with a message, not a traceback."""


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def add_logging_flags(parser: Any) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    group.add_argument("-q", "--quiet", action="store_true", help="only show warnings and errors")


# --------------------------------------------------------------- config ---
@cache
def _load_toml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def site_config() -> dict[str, Any]:
    """Return ``hugo.toml`` as a dict (empty if it is missing)."""
    return _load_toml("hugo.toml")


def site_params() -> dict[str, Any]:
    """Return ``params.toml`` as a dict (empty if it is missing)."""
    return _load_toml("params.toml")


def base_url() -> str:
    """The production base URL with a trailing slash, e.g. ``https://example.com/``."""
    url = os.environ.get("HUGO_BASEURL") or site_config().get("baseURL", "")
    if not url:
        raise ScriptError("baseURL is not set in config/_default/hugo.toml")
    return url if url.endswith("/") else url + "/"


def site_host() -> str:
    """Host name of the production site, overridable with ``SITE_HOST``."""
    return os.environ.get("SITE_HOST") or urlsplit(base_url()).netloc


def github_user() -> str:
    """GitHub user: ``PORTFOLIO_GITHUB_USER`` or ``author.githubUser`` in params.toml."""
    user = os.environ.get("PORTFOLIO_GITHUB_USER") or site_params().get("author", {}).get(
        "githubUser", ""
    )
    if not user:
        raise ScriptError("set author.githubUser in config/_default/params.toml or pass --user")
    return user


# ------------------------------------------------------------ blocklist ---
@cache
def _blocklist() -> tuple[tuple[int, str], ...]:
    if not BLOCKLIST_FILE.is_file():
        return ()
    with BLOCKLIST_FILE.open("rb") as fh:
        terms = tomllib.load(fh).get("terms", [])
    return tuple((int(t["length"]), str(t["sha256"]).lower()) for t in terms)


def term_hash(term: str) -> str:
    """SHA-256 of a term as stored in ``data/blocklist.toml``."""
    return hashlib.sha256(term.strip().lower().encode("utf-8")).hexdigest()


def is_blocked(*texts: object) -> bool:
    """True if any text contains a blocked term (case-insensitive).

    Every substring with the length of a blocked term is hashed and compared,
    so the terms never need to appear in the repository in plain text.
    """
    terms = _blocklist()
    if not terms:
        return False
    for text in texts:
        if not text:
            continue
        low = str(text).lower()
        for length, digest in terms:
            for i in range(len(low) - length + 1):
                if hashlib.sha256(low[i : i + length].encode("utf-8")).hexdigest() == digest:
                    return True
    return False


# --------------------------------------------------------------- GitHub ---
def find_gh() -> str | None:
    """Locate the GitHub CLI (``GH_PATH`` wins over ``PATH``)."""
    explicit = os.environ.get("GH_PATH")
    if explicit and Path(explicit).is_file():
        return explicit
    return shutil.which("gh")


def gh_env() -> dict[str, str]:
    env = dict(os.environ)
    if not env.get("GH_TOKEN") and env.get("GITHUB_TOKEN"):
        env["GH_TOKEN"] = env["GITHUB_TOKEN"]
    return env


def gh_json(gh: str, args: list[str]) -> Any:
    """Run ``gh`` and parse its JSON output; raise ``ScriptError`` on failure."""
    res = subprocess.run(
        [gh, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=gh_env(),
        check=False,
    )
    if res.returncode != 0:
        raise ScriptError(res.stderr.strip() or f"gh {' '.join(args)} exited with {res.returncode}")
    try:
        return json.loads(res.stdout or "null")
    except json.JSONDecodeError as exc:
        raise ScriptError(f"gh {' '.join(args)} returned invalid JSON: {exc}") from exc


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_json(path: Path, data: dict[str, Any], volatile: tuple[str, ...] = ()) -> bool:
    """Write ``data`` as pretty JSON unless only the ``volatile`` keys changed.

    Keeps reruns idempotent: a timestamp alone never produces a new file.
    Returns True if the file was written.
    """
    if path.is_file():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old = None
        if isinstance(old, dict):
            strip = lambda d: {k: v for k, v in d.items() if k not in volatile}  # noqa: E731
            if strip(old) == strip(data):
                return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(data), encoding="utf-8")
    return True
