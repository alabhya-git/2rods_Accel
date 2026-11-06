"""Render an SVG or HTML file to PNG/PDF in headless Chrome with the self-hosted Baloo fonts.

usage: python render.py input.svg output.png [width height scale]
       python render.py input.html output.pdf
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "web" / "node_modules" / "@fontsource"


def font_css() -> str:
    rules = []
    for fam, pkg in (("Baloo 2", "baloo-2"),):
        for w in (400, 600, 700, 800):
            for sub in ("latin", "devanagari"):
                f = FONTS / pkg / "files" / f"{pkg}-{sub}-{w}-normal.woff2"
                if f.exists():
                    rules.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('{f.as_uri()}') format('woff2');}}")
    return "\n".join(rules)


async def main(src: str, dst: str, w: int, h: int, scale: float):
    s = Path(src).resolve()
    body = s.read_text(encoding="utf-8")
    if s.suffix == ".svg":
        html = f"<html><head><style>{font_css()} html,body{{margin:0}}</style></head><body>{body}</body></html>"
    else:
        html = body.replace("</head>", f"<style>{font_css()}</style></head>")
    tmp = s.with_suffix(".render.html")
    tmp.write_text(html, encoding="utf-8")
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--allow-file-access-from-files"])
        pg = await br.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        await pg.goto(tmp.as_uri())
        await pg.wait_for_timeout(600)
        if dst.endswith(".pdf"):
            await pg.pdf(path=dst, format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        else:
            await pg.screenshot(path=dst, clip={"x": 0, "y": 0, "width": w, "height": h})
        await br.close()
    tmp.unlink()


if __name__ == "__main__":
    a = sys.argv
    asyncio.run(main(a[1], a[2], int(a[3]) if len(a) > 3 else 1920, int(a[4]) if len(a) > 4 else 1080, float(a[5]) if len(a) > 5 else 1))
