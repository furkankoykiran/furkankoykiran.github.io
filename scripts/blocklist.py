#!/usr/bin/env python3
"""Manage and test the hashed blocklist in ``data/blocklist.toml``.

Examples::

    python scripts/blocklist.py hash "some name"   # print a TOML entry to add
    python scripts/blocklist.py check data/*.json   # fail if a file contains a blocked term
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from common import add_logging_flags, is_blocked, setup_logging, term_hash

log = logging.getLogger("blocklist")


def cmd_hash(args: argparse.Namespace) -> int:
    for term in args.terms:
        clean = term.strip().lower()
        print(f'[[terms]]\n  length = {len(clean)}\n  sha256 = "{term_hash(clean)}"\n')
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    hits = 0
    for name in args.files:
        path = Path(name)
        if not path.is_file():
            log.error("%s: not a file", path)
            hits += 1
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if is_blocked(line):
                log.error("%s:%d contains a blocked term", path, lineno)
                hits += 1
    if hits:
        return 1
    log.info("%d file(s) clean", len(args.files))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_logging_flags(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash", help="print blocklist entries for the given terms")
    p_hash.add_argument("terms", nargs="+", metavar="TERM")
    p_hash.set_defaults(func=cmd_hash)

    p_check = sub.add_parser("check", help="exit 1 if any file contains a blocked term")
    p_check.add_argument("files", nargs="+", metavar="FILE")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.quiet)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
