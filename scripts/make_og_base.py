#!/usr/bin/env python3
"""Render the Open Graph background images used by Hugo at build time.

Outputs (both committed under ``assets/img/``):

``og-base.png``
    1200x630 navy background with the prism light beam, the round profile
    photo, the author's name and the site's domain.
``og-textbox.png``
    Transparent 720x340 canvas. ``layouts/partials/fk/og-image.html`` draws
    each page's title on it and overlays it on the background.

Only needs to run again when the photo or the brand changes. Requires Pillow
(``pip install pillow``).

Exit codes: 0 success, 1 unexpected error, 2 usage error (missing input).
"""

from __future__ import annotations

import argparse
import itertools
import logging
import sys
from pathlib import Path

from common import REPO_ROOT, ScriptError, add_logging_flags, setup_logging, site_host, site_params

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # pragma: no cover - reported at runtime
    Image = None  # type: ignore[assignment]

log = logging.getLogger("og")

ASSETS = REPO_ROOT / "assets"
W, H = 1200, 630
NAVY = (17, 21, 29)
BLUE = (47, 124, 246)
CYAN = (34, 184, 232)
TEAL = (45, 212, 191)
VIOLET = (139, 124, 246)
PRISM = [(0.0, BLUE), (0.35, CYAN), (0.6, TEAL), (1.0, VIOLET)]

RGB = tuple[int, int, int]


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def gradient(t: float, stops: list[tuple[float, RGB]]) -> RGB:
    for (p0, c0), (p1, c1) in itertools.pairwise(stops):
        if p0 <= t <= p1:
            return lerp(c0, c1, (t - p0) / (p1 - p0 or 1))
    return stops[-1][1]


def render(photo: Path, fonts: Path, name: str, domain: str) -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)

    # Soft glows.
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-260, -320, 560, 360), fill=(20, 60, 120))
    g.ellipse((760, 260, 1500, 900), fill=(12, 80, 90))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.55)

    # Dotted grid, fading out towards the left where the title goes.
    dots = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(dots)
    for y in range(18, H, 28):
        for x in range(18, W, 28):
            alpha = int(max(0, min(1, (x - 300) / 700)) * 38)
            if alpha:
                d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=alpha)
    img.paste(Image.new("RGB", (W, H), (190, 210, 240)), (0, 0), dots)

    # The prism light beam from the logo: a blurred diagonal band.
    beam = Image.new("RGB", (W * 2, 140), (0, 0, 0))
    mask = Image.new("L", (W * 2, 140), 0)
    bd, md = ImageDraw.Draw(beam), ImageDraw.Draw(mask)
    for x in range(W * 2):
        t = x / (W * 2)
        bd.line([(x, 0), (x, 140)], fill=gradient(t, PRISM))
        edge = min(t / 0.25, (1 - t) / 0.25, 1)
        md.line([(x, 40), (x, 100)], fill=int(120 * max(0, edge)))
    beam_rgba = beam.convert("RGBA")
    beam_rgba.putalpha(mask.filter(ImageFilter.GaussianBlur(26)))
    beam_rgba = beam_rgba.rotate(-14, resample=Image.BICUBIC, expand=True)
    img = img.convert("RGBA")
    img.alpha_composite(beam_rgba, (-W // 2, 300 - beam_rgba.height // 2))

    # Prism hairline along the top edge.
    top = ImageDraw.Draw(img)
    for x in range(W):
        top.line([(x, 0), (x, 5)], fill=(*gradient(x / W, PRISM), 255))

    # Round photo with a gradient ring. The square photo is masked, not cropped.
    size, ring = 300, 14
    cx, cy = 980, 268
    face = Image.open(photo).convert("RGB").resize((size, size), Image.LANCZOS)
    circle = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(circle).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    circle = circle.resize((size, size), Image.LANCZOS)
    rs = size + ring * 2
    ring_img = Image.new("RGBA", (rs * 4, rs * 4), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_img)
    for deg in range(360):
        col = (*gradient(deg / 360, [*PRISM, (1.0, BLUE)]), 255)
        rd.pieslice((0, 0, rs * 4 - 1, rs * 4 - 1), deg - 90, deg - 89 + 1.5, fill=col)
    ring_img = ring_img.resize((rs, rs), Image.LANCZOS)
    inner = Image.new("L", (rs * 4, rs * 4), 0)
    ImageDraw.Draw(inner).ellipse((24, 24, rs * 4 - 25, rs * 4 - 25), fill=255)
    ring_img.paste((*NAVY, 255), (0, 0), inner.resize((rs, rs), Image.LANCZOS))
    img.alpha_composite(ring_img, (cx - rs // 2, cy - rs // 2))
    img.paste(face, (cx - size // 2, cy - size // 2), circle)

    draw = ImageDraw.Draw(img)
    name_font = ImageFont.truetype(str(fonts / "Poppins-SemiBold.ttf"), 30)
    mono = ImageFont.truetype(str(fonts / "IBMPlexMono-Medium.ttf"), 24)
    nw = draw.textlength(name, font=name_font)
    draw.text((cx - nw / 2, cy + rs // 2 + 22), name, font=name_font, fill=(233, 238, 245))
    draw.text((80, 548), domain, font=mono, fill=(120, 200, 255))
    return img.convert("RGB")


def main(argv: list[str] | None = None) -> int:
    author = site_params().get("author", {})
    parser = argparse.ArgumentParser(
        description="Render assets/img/og-base.png and og-textbox.png."
    )
    parser.add_argument(
        "--photo",
        type=Path,
        default=ASSETS / author.get("image", "img/furkan-koykiran.jpg"),
        help="square profile photo (default: author.image in params.toml)",
    )
    parser.add_argument("--fonts", type=Path, default=ASSETS / "fonts", help="font directory")
    parser.add_argument("--out-dir", type=Path, default=ASSETS / "img", help="output directory")
    parser.add_argument("--name", default=author.get("name", ""), help="name under the photo")
    parser.add_argument("--domain", help="domain in the corner (default: host of baseURL)")
    add_logging_flags(parser)
    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.quiet)

    try:
        if Image is None:
            raise ScriptError("Pillow is required: pip install pillow")
        if not args.photo.is_file():
            raise ScriptError(f"photo not found: {args.photo}")
        img = render(args.photo, args.fonts, args.name, args.domain or site_host())
        args.out_dir.mkdir(parents=True, exist_ok=True)
        img.save(args.out_dir / "og-base.png", optimize=True)
        Image.new("RGBA", (720, 340), (0, 0, 0, 0)).save(
            args.out_dir / "og-textbox.png", optimize=True
        )
    except ScriptError as exc:
        log.error("%s", exc)
        return 2
    except Exception:
        log.exception("unexpected error")
        return 1
    log.info("wrote %s", args.out_dir / "og-base.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
