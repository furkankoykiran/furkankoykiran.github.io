#!/usr/bin/env python3
"""Fail if the build output would shadow a path owned by another site.

Other repositories publish GitHub Pages sites under this domain
(``projectSites`` in params.toml). If ``public/`` contained one of those
top-level paths, deploying would hide that site.

Exit codes: 0 no conflicts, 1 conflict found, 2 usage error.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from common import REPO_ROOT, add_logging_flags, setup_logging, site_params

log = logging.getLogger("reserved")

# Reserved in addition to the project sites.
EXTRA_RESERVED = ("blog",)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--public-dir",
        type=Path,
        default=REPO_ROOT / "public",
        help="Hugo output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--reserved",
        action="append",
        default=[],
        metavar="NAME",
        help="extra reserved top-level path; repeatable",
    )
    add_logging_flags(parser)
    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.quiet)

    if not args.public_dir.is_dir():
        log.error("%s does not exist; build the site first", args.public_dir)
        return 2
    reserved = {
        name.lower()
        for name in (*site_params().get("projectSites", []), *EXTRA_RESERVED, *args.reserved)
    }
    clashes = sorted(p.name for p in args.public_dir.iterdir() if p.name.lower() in reserved)
    for name in clashes:
        # GitHub Actions turns this line into an error annotation.
        print(f"::error::{args.public_dir.name}/{name} would shadow a reserved path")
    if clashes:
        return 1
    log.info("no reserved paths in %s (%d checked)", args.public_dir, len(reserved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
