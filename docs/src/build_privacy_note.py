"""Build submission HTML from docs/privacy-note.md; render it with render.py."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
text = (ROOT / "docs/privacy-note.md").read_text(encoding="utf-8")


def inline(value: str) -> str:
    value = escape(value)
    value = re.sub(r"\[([^]]+)\]\((https://[^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", value)


intro, *parts = re.split(r"^## ", text, flags=re.M)
paragraphs = intro.strip().split("\n\n")
title = paragraphs[0].removeprefix("# ")
sections, footnotes = [], []
for part in parts:
    heading, body = part.split("\n", 1)
    content = []
    for paragraph in body.strip().split("\n\n"):
        if paragraph.startswith(("**Basis:", "**Reference:")):
            footnotes.append(paragraph)
        else:
            content.append(f"<p>{inline(paragraph)}</p>")
    sections.append(f"<section><h2>{escape(heading)}</h2>{''.join(content)}</section>")
assert len(sections) == 8
style = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html,body { margin:0; background:white; color:#1B1F3B; }
body { font-family:'Baloo 2',sans-serif; font-size:9.7pt; line-height:1.29; }
.page { width:210mm; min-height:297mm; padding:11mm 13mm 9mm; }
header { border-bottom:2px solid #C8102E; padding-bottom:3mm; }
h1 { margin:0; font-size:21pt; line-height:1.1; font-weight:800; }
.meta { color:#4A4F6E; font-size:9pt; margin-top:1.5mm; }
.intro { margin-top:2.7mm; color:#4A4F6E; font-size:9.7pt; }
.grid { display:grid; grid-template-columns:1fr 1fr; column-gap:7mm; row-gap:2.7mm; margin-top:3mm; }
section { border-top:1px solid #D5DEEE; padding-top:2mm; break-inside:avoid; }
h2 { margin:0 0 1mm; font-size:10.6pt; line-height:1.15; font-weight:700; }
p { margin:0; }
footer { border-top:1px solid #D5DEEE; margin-top:3mm; padding-top:2mm; font-size:8pt; line-height:1.25; color:#4A4F6E; }
footer p+p { margin-top:1mm; }
a { color:#2B4C8C; text-decoration:none; }
code { font-family:inherit; }
"""
html = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    f"<title>{escape(title)}</title><style>{style}</style></head><body><main class=\"page\">"
    f"<header><h1>{escape(title)}</h1><div class=\"meta\">{inline(paragraphs[1])}</div></header>"
    f'<p class="intro">{inline(paragraphs[2])}</p><div class="grid">'
    + "".join(sections)
    + "</div><footer>"
    + "".join(f"<p>{inline(p)}</p>" for p in footnotes)
    + "</footer></main></body></html>\n"
)
(ROOT / "docs/src/privacy-note.html").write_bytes(html.encode("utf-8"))
print("Privacy note HTML generated from Markdown.")
