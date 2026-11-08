"""Builds docs/deck/dukaan-connect-business-case.pptx on the official SYNC template.

Every number is computed from the official data pack or produced by the prototype; see the
source line under each exhibit. Run: python docs/src/build_deck.py <template.pptx>
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
SHOTS = ROOT / "docs" / "screens" / "deck"
OUT = ROOT / "docs" / "deck" / "dukaan-connect-business-case.pptx"
TEMPLATE = Path(sys.argv[1])

RED, INK, SOFT, FAINT, RULE, TINT, WHITE, GREEN, GREY = (
    RGBColor(0xD4, 0x00, 0x00), RGBColor(0x1F, 0x24, 0x30), RGBColor(0x55, 0x5B, 0x6E), RGBColor(0x8A, 0x8F, 0xA0),
    RGBColor(0xDA, 0xDD, 0xE5), RGBColor(0xF4, 0xF5, 0xF8), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x1E, 0x7B, 0x4F),
    RGBColor(0xB8, 0xBC, 0xC8))
FONT = "Arial"
DATA_SOURCE = "Source: smb_leads.csv, official synthetic pack, 5,000 leads, April to June 2026."

prs = Presentation(str(TEMPLATE))
W, H = prs.slide_width, prs.slide_height
L_TITLE_ONLY = prs.slide_layouts[4]

# keep the dark title slide, drop the template's sample content slide (we add our own)
title_slide = prs.slides[0]
content_bg = None
for shp in prs.slides[1].shapes:
    if shp.shape_type == 13:
        content_bg = shp.image.blob
sld_ids = prs.slides._sldIdLst
second = sld_ids[1]
prs.part.drop_rel(second.get(qn("r:id")))
sld_ids.remove(second)
BG_PATH = SRC / "_content_bg.jpg"
BG_PATH.write_bytes(content_bg)


# ---------------------------------------------------------------- helpers
def _no_shadow(shape):
    sppr = shape._element.spPr
    if sppr.find(qn("a:effectLst")) is None:
        etree.SubElement(sppr, qn("a:effectLst"))
    style = shape._element.find(qn("p:style"))
    if style is not None:  # the default style points at the theme's shadow effect
        shape._element.remove(style)


def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         spacing=None, name=None, line_spacing=None):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, {size,bold,color}) tuples."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing is not None and i > 0:
            p.space_before = Pt(spacing)
        if line_spacing:
            p.line_spacing = line_spacing
        parts = para if isinstance(para, list) else [(para, {})]
        for t, o in parts:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = FONT
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.color.rgb = o.get("color", color)
    return tb


def box(slide, x, y, w, h, fill=TINT, line=None, radius=0.08, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    _no_shadow(s)
    s.text_frame.margin_left = s.text_frame.margin_right = Inches(0.08)
    return s


def arrow(slide, x1, y1, x2, y2, color=SOFT, width=1.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    st = c._element.find(qn("p:style"))
    if st is not None:
        c._element.remove(st)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return c


def icon(slide, name, x, y, d=0.46, fill=RED):
    circle = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    pad = d * 0.24
    pic = slide.shapes.add_picture(str(SRC / "icons" / f"{name}.png"), Inches(x + pad), Inches(y + pad), Inches(d - 2 * pad), Inches(d - 2 * pad))
    pic._element.nvPicPr.cNvPr.set("descr", "")
    return circle


def picture(slide, path, x, y, h=None, w=None, alt=""):
    kw = {}
    if h:
        kw["height"] = Inches(h)
    if w:
        kw["width"] = Inches(w)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)
    pic._element.nvPicPr.cNvPr.set("descr", alt)
    return pic


def content_slide(title, subtitle=None, source=None, notes=None):
    s = prs.slides.add_slide(L_TITLE_ONLY)
    bg = s.shapes.add_picture(str(BG_PATH), 0, 0, W, H)
    bg._element.nvPicPr.cNvPr.set("descr", "")
    tree = s.shapes._spTree
    tree.remove(bg._element)
    tree.insert(2, bg._element)  # behind everything
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(0.5), Inches(0.72), Inches(9.0), Inches(0.52)
    tf = t.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.word_wrap = True
    tf.text = title
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    for r in p.runs:
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(26), True, INK
    if subtitle:
        text(s, 0.5, 1.22, 9.0, 0.34, subtitle, size=14, color=SOFT, name="Subtitle")
    if source:
        text(s, 0.5, 5.1, 7.4, 0.3, source, size=9, color=FAINT, name="Source", anchor=MSO_ANCHOR.TOP)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def style_chart(chart, size=10):
    chart.font.name = FONT
    chart.font.size = Pt(size)
    chart.font.color.rgb = SOFT
    chart.has_legend = False
    chart.has_title = False


def bar_chart(slide, x, y, w, h, cats, series, colors, fmt='#,##0', gap=45, overlap=None, label_size=10, cat_size=10,
              horizontal=True, label_color=INK):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    style_chart(ch, cat_size)
    plot = ch.plots[0]
    plot.gap_width = gap
    if overlap is not None:
        plot.overlap = overlap
    plot.vary_by_categories = False
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(label_size)
    dl.font.bold = True
    dl.font.color.rgb = label_color
    dl.font.name = FONT
    ca = ch.category_axis
    ca.has_major_gridlines = False
    ca.format.line.color.rgb = RULE
    ca.tick_labels.font.size = Pt(cat_size)
    ca.tick_labels.font.color.rgb = INK
    ca.tick_labels.font.name = FONT
    if horizontal:
        ca.reverse_order = True
    va = ch.value_axis
    va.has_major_gridlines = False
    va.visible = False
    for i, s in enumerate(plot.series):
        c = colors[i]
        if isinstance(c, list):
            for j, cj in enumerate(c):
                pt = s.points[j]
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = cj
        else:
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = c
    return ch


def table(slide, x, y, w, rows, col_w, row_h=0.3, size=11, header_fill=INK, zebra=True, bold_first_col=True, aligns=None):
    nrows, ncols = len(rows), len(rows[0])
    gf = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(row_h * nrows))
    tbl = gf.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(nrows):
        tbl.rows[i].height = Inches(row_h)
        for j in range(ncols):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            val = rows[i][j]
            parts = val if isinstance(val, list) else [(val, {})]
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = (aligns[j] if aligns else PP_ALIGN.LEFT)
            for t, o in parts:
                r = p.add_run()
                r.text = t
                r.font.name = FONT
                r.font.size = Pt(o.get("size", size))
                r.font.bold = o.get("bold", i == 0 or (bold_first_col and j == 0))
                r.font.color.rgb = o.get("color", WHITE if i == 0 else INK)
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if i == 0 else (TINT if zebra and i % 2 == 0 else WHITE)
            _cell_borders(cell)
    return tbl


def _cell_borders(cell, color="DADDE5", width_pt=0.75):
    """Thin explicit borders, so every renderer draws the same table (no reliance on the table style)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        old = tcPr.find(qn(tag))
        if old is not None:
            tcPr.remove(old)
        ln = etree.Element(qn(tag), w=str(int(width_pt * 12700)), cap="flat", cmpd="sng", algn="ctr")
        fill = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(fill, qn("a:srgbClr"), val=color)
        etree.SubElement(ln, qn("a:prstDash"), val="solid")
        tcPr.insert(list(tcPr).index(tcPr.find(qn("a:solidFill"))) if tcPr.find(qn("a:solidFill")) is not None else len(tcPr), ln)


def stat(slide, x, y, w, big, label, color=RED, big_size=30, label_size=12, label_h=0.5):
    text(slide, x, y, w, 0.5, big, size=big_size, bold=True, color=color)
    text(slide, x, y + big_size / 72 + 0.06, w, label_h, label, size=label_size, color=SOFT)


# ---------------------------------------------------------------- 1. title
s = title_slide
text(s, 0.68, 2.82, 3.9, 0.6, "Dukaan Connect", size=34, bold=True, color=WHITE, name="Title")
text(s, 0.68, 3.42, 3.9, 0.4, "From 17.6 days to one sitting", size=20, color=RGBColor(0xFF, 0xC9, 0xC9))
text(s, 0.68, 3.86, 3.8, 0.7,
     "Dukaan Connect sells, verifies and installs small-business bundles on a phone, in the owner's own language.",
     size=13, color=RGBColor(0xE6, 0xE6, 0xEA))
text(s, 0.68, 4.72, 3.9, 0.55, [
    [("Working prototype: ", {"bold": True, "color": WHITE}), ("10 languages, 33 of 33 advisor scenarios, 12 of 12 KYC specimens, DPDP controls in code", {})],
    [("Track A: Project Udyam Digital. Alabhya, IIIT-Delhi", {"color": RGBColor(0xB8, 0xBC, 0xC8)})],
], size=10.5, color=RGBColor(0xE6, 0xE6, 0xEA), spacing=3)
s.notes_slide.notes_text_frame.text = (
    "Dukaan Connect takes a small-business owner from first message to a verified, paid, booked installation in one sitting, "
    "in their own language. Everything in this deck is built and running; the numbers come from the official data pack.")

# ---------------------------------------------------------------- 2. the problem
s = content_slide("7 in 100 leads become customers, after 17.6 days",
                  "Most leads leave before a quote; the ones who stay wait almost three weeks and chase us three times",
                  DATA_SOURCE + " Days are averages for the 368 activated customers.",
                  "Lead to activation is 7.4%. Contact, assessment, quote and KYC take 12.9 of the 17.6 days; installation itself is 4.8. "
                  "Each activated customer called three times to ask about status, and acquisition cost Rs 15,053 per activation.")
cats = ["Lead", "Contacted, 68%", "Needs assessed, 58%", "Quote accepted, 44%", "KYC complete, 68%", "Activated, 63%"]
vals = [5000, 3406, 1974, 861, 588, 368]
bar_chart(s, 0.4, 1.62, 5.5, 3.2, cats, [("Leads", vals)], [[GREY] * 5 + [RED]], gap=38, cat_size=11, label_size=11)
text(s, 0.5, 4.86, 5.3, 0.22, "Leads reaching each stage; % is the share of the previous stage", size=9, color=FAINT)
x0 = 6.25
stat(s, x0, 1.66, 3.25, "17.6 days", "from lead to activation, on average")
segs = [("2.0", 2.0), ("3.0", 3.0), ("4.1", 4.1), ("3.8", 3.8), ("4.8", 4.8)]
scale = 3.2 / 17.7
cx = x0
for i, (lab, d) in enumerate(segs):
    seg = box(s, cx, 2.62, d * scale - 0.03, 0.3, fill=RED if i < 4 else GREY, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    tf = seg.text_frame
    tf.margin_left = tf.margin_right = 0
    tf.text = lab
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size, p.runs[0].font.bold, p.runs[0].font.color.rgb, p.runs[0].font.name = Pt(10), True, WHITE, FONT
    cx += d * scale
text(s, x0, 2.98, 3.25, 0.42, [[("Contact, assess, quote, KYC: ", {"bold": True, "color": RED}), ("12.9 days before installation (4.8) begins", {})]], size=11, color=SOFT)
stat(s, x0, 3.55, 1.15, "3.0", "chase calls per customer", big_size=26, label_size=11, label_h=0.5)
stat(s, x0 + 1.3, 3.55, 1.95, "Rs 15,053", "acquisition cost per activation", big_size=26, label_size=11, label_h=0.5)

# ---------------------------------------------------------------- 3. why leads are lost
s = content_slide("Two-thirds of lost leads are lost to the process",
                  "Every red bar is a step our journey removes; only the grey ones are about price, rivals or timing",
                  DATA_SOURCE + " Drop reasons of the 4,632 leads that did not activate.",
                  "3,109 of 4,632 drops have a process cause. The top three, unreachable after three attempts, no time for a visit and visit "
                  "not scheduled, all depend on a salesperson reaching the owner. A self-serve, WhatsApp-first journey needs neither.")
reasons = [("Unreachable after 3 attempts", 805, 1), ("No time for a visit", 531, 1), ("Not interested on first call", 470, 0),
           ("Price too high", 414, 0), ("Locked in with current provider", 325, 0), ("Wrong or invalid number", 319, 1),
           ("Visit not scheduled by sales", 296, 1), ("Only wanted a mobile plan", 280, 1), ("Competitor offered cheaper", 207, 0),
           ("Quote too complex", 206, 1), ("Quote took too long", 179, 1), ("Decided to wait", 107, 0),
           ("Installation delayed over 21 days", 98, 1), ("Missing GST or Udyam document", 94, 1), ("Paperwork too long", 79, 1),
           ("Signatory not available", 53, 1), ("Cancelled before install", 53, 1), ("Document details did not match", 47, 1),
           ("Site not feasible for fibre", 41, 1), ("First payment failed", 28, 1)]
bar_chart(s, 3.25, 1.6, 6.35, 3.5, [r[0] for r in reasons],
          [("Process", [r[1] if r[2] else 0 for r in reasons]), ("Market", [0 if r[2] else r[1] for r in reasons])],
          [RED, GREY], fmt='#,##0;;;', gap=28, overlap=100, label_size=9, cat_size=9)
text(s, 0.5, 1.72, 2.6, 0.7, "67%", size=44, bold=True, color=RED)
text(s, 0.5, 2.45, 2.55, 0.8, "of drops (3,109 of 4,632) have a process cause a digital journey can fix", size=13, color=INK)
box(s, 0.5, 3.42, 0.16, 0.16, fill=RED, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.75, 3.38, 2.35, 0.3, "Process: we remove it", size=11, color=INK)
box(s, 0.5, 3.74, 0.16, 0.16, fill=GREY, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.75, 3.7, 2.35, 0.3, "Market: price, rivals, timing", size=11, color=INK)
text(s, 0.5, 4.12, 2.6, 0.85, "The top three need a salesperson to reach the owner. The journey needs neither a call nor a visit.",
     size=11, color=SOFT)

# ---------------------------------------------------------------- 4. segments and bundles
s = content_slide("Start where digital pays back fastest",
                  "Offices and micro retail first; multi-site and factories follow on an assisted path",
                  "Segments: smb_leads.csv (synthetic). Bundles: our rules engine on product_catalogue.csv, 24-month price, before 18% GST.",
                  "Professional offices convert at 11.1% and pay back in 1.6 months, so they go fully self-serve first. Micro retail is 54% of leads "
                  "but takes 8 months to pay back through field sales; at Rs 300 to 500 a digital lead and 8% activation it pays back in about "
                  "1.5 to 2.5 months. Multi-site and manufacturers pay back in under a month even with a salesperson, so the advisor builds their "
                  "quote and field sales close.")
R = PP_ALIGN.RIGHT
rows = [["Segment", "Leads", "Activation", "Avg bundle", "Cost to acquire", "Payback", "6-mo churn", "Launch"],
        ["Micro retail and services", "54%", "4.1%", "Rs 2,505", "Rs 20,007", [("8.0 months", {"color": RED, "bold": True})], "22.7%", "Wave 1, via WhatsApp"],
        ["Professional offices", "25%", "11.1%", "Rs 6,796", "Rs 10,695", "1.6 months", "13.8%", "Wave 1, self-serve"],
        ["Small multi-site", "15%", "11.0%", "Rs 31,233", "Rs 15,614", "0.5 months", "10.8%", "Wave 2, assisted"],
        ["Small manufacturers", "6%", "12.8%", "Rs 19,980", "Rs 15,324", "0.8 months", "8.1%", "Wave 2, assisted"]]
table(s, 0.5, 1.66, 9.0, rows, [1.85, 0.6, 0.9, 0.95, 1.2, 0.95, 0.95, 1.6], row_h=0.29, size=10,
      aligns=[PP_ALIGN.LEFT, R, R, R, R, R, R, PP_ALIGN.LEFT])
bundles = [("Dukaan Starter", "Kirana, 3 staff", "Rs 2,196", "Biz Fibre 100, 2 postpaid lines, Cloud POS. Add guest Wi-Fi, CCTV, website", "Setup Rs 2,500 over 12 months"),
           ("Clinic and Office Pro", "Clinic, 5 staff", "Rs 4,618", "Biz Fibre 300, 3 postpaid lines, 5 email seats, 1 TB backup, endpoint security", "No setup fee"),
           ("Multi-site One", "4 stores, 15 staff", "Rs 23,779", "Per store: Biz Fibre 300, failover, SD-WAN, POS. Plus CCTV and 4 lines", "Setup Rs 45,000"),
           ("Factory Connect", "Factory, 25 staff", "Rs 18,198", "Leased Line 20, managed firewall, 10 machine IoT kits, 25 email seats", "Setup Rs 44,000")]
bw, gap = 2.1, 0.2
for i, (name, who, price, what, setup) in enumerate(bundles):
    bx = 0.5 + i * (bw + gap)
    box(s, bx, 3.38, bw, 1.62, fill=TINT, radius=0.06)
    text(s, bx + 0.14, 3.45, bw - 0.28, 0.28, name, size=12, bold=True)
    text(s, bx + 0.14, 3.69, bw - 0.28, 0.25, who, size=10, color=SOFT)
    text(s, bx + 0.14, 3.92, bw - 0.28, 0.32, [[(price, {"size": 16, "bold": True, "color": RED}), (" a month", {"size": 10, "color": SOFT})]])
    text(s, bx + 0.14, 4.24, bw - 0.28, 0.5, what, size=9.5, color=INK)
    text(s, bx + 0.14, 4.76, bw - 0.28, 0.22, setup, size=9, color=SOFT)

# ---------------------------------------------------------------- 5. the journey
s = content_slide("One sitting on a phone, in the owner's language",
                  "About 12 minutes from first message to booked install, consent and UPI included",
                  "Screens: the working prototype, specimen applicant K09 (Kaveri Insurance Advisors, Visakhapatnam). Drop counts: smb_leads.csv.",
                  "The owner types or speaks in Telugu; the advisor reads the GSTIN and fills in the business. The quote is one monthly price with "
                  "add-ons ticked on or off. KYC checks the registries first and reads four photos on our own servers. The tracker dates every "
                  "product and sends WhatsApp updates, which matters: customers who chased five times churned 27.9%, against 5.9% after one call.")
phones = [("1_advisor_te.png", "Advisor, 4 min", "Chat or voice in 10 languages; the GSTIN fills in the business.", "Removes: no time for a visit (531), visit not scheduled (296)"),
          ("2_quote.png", "Quote, 2 min", "One monthly price; add-ons tick on and off; 12 or 24 months.", "Removes: quote too slow (179) or too complex (206)"),
          ("4b_kyc_top.png", "Smart KYC, 4 min", "Registry first, then four photos read on our servers.", "Removes: paperwork too long (79), missing documents (94)"),
          ("6_tracker.png", "Tracker, until live", "Every product dated; updates on WhatsApp, no calls.", "Chased 5 times: 27.9% churn. Once: 5.9%")]
cw = 2.3
ph_h = 2.28
ph_w = ph_h * 780 / 1688
for i, (f, head, what, removes) in enumerate(phones):
    cx = 0.5 + i * cw
    px = cx + (cw - 0.2 - ph_w) / 2
    box(s, px - 0.05, 1.6, ph_w + 0.1, ph_h + 0.1, fill=INK, radius=0.09)
    picture(s, SHOTS / f, px, 1.65, h=ph_h, alt=f"{head} screen of the prototype")
    text(s, cx, 4.02, cw - 0.2, 0.24, [[(f"{i + 1}  ", {"color": RED}), (head, {})]], size=11.5, bold=True)
    text(s, cx, 4.26, cw - 0.2, 0.34, what, size=9.5, color=SOFT)
    text(s, cx, 4.6, cw - 0.2, 0.34, removes, size=9.5, color=RED, bold=True)

# ---------------------------------------------------------------- 6. advisor
s = content_slide("An advisor that cannot mis-sell",
                  "The language model talks and explains; a rules engine picks every product and price",
                  "Mis-selling: activated customers in smb_leads.csv against catalogue rules. Scenarios: /api/judge/scenarios.",
                  "We answer the rule-based or RAG question with both. The model handles free text and voice in any of ten languages and explains "
                  "the result. The engine walks the catalogue as a graph of needs, products, dependencies and eligibility. A guard blocks any "
                  "reply that names a product or a rupee amount the engine did not produce. Last quarter 56 customers were sold something the "
                  "catalogue forbids; the engine makes that zero, and runs without any model key at all.")
steps = [("Owner", "\"Insurance agency in Vizag, 25 staff, we need email\", typed or spoken in Telugu", WHITE, INK),
         ("Language model", "Understands, asks what is missing, explains. Sees masked text only", TINT, INK),
         ("Rules engine", "Catalogue graph: eligibility, dependencies, quantities, price. Names the rule behind every exclusion", TINT, INK),
         ("Guard", "Every product and rupee in the reply must match the engine, or the engine's own wording is sent", RED, WHITE)]
y = 1.66
for i, (head, body, fill, fg) in enumerate(steps):
    b = box(s, 0.5, y, 5.2, 0.66, fill=fill, line=RULE if fill == WHITE else None, radius=0.12)
    text(s, 0.68, y + 0.08, 1.55, 0.5, head, size=12, bold=True, color=fg, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.25, y + 0.07, 3.33, 0.54, body, size=10, color=fg if fill == RED else SOFT, anchor=MSO_ANCHOR.MIDDLE)
    if i < len(steps) - 1:
        arrow(s, 3.1, y + 0.66, 3.1, y + 0.84)
    y += 0.84
text(s, 3.22, 3.17, 1.2, 0.18, "calls as tools", size=9, color=FAINT)
stat(s, 6.1, 1.62, 3.4, "56 of 368", "customers last quarter (15%) bought a product the catalogue forbids for them")
text(s, 6.1, 2.62, 3.4, 1.0, [
    "Biz Fibre 1G in tier-2 cities: 24",
    "GST-only products without an active GSTIN: 22",
    "Static IP without fibre: 9",
    "Below the minimum headcount: 8"], size=10, color=INK, spacing=2)
stat(s, 6.1, 3.62, 3.4, "33 of 33", "judge-style scenarios pass, tampered carts included. Zero eligibility violations, with or without an LLM", color=GREEN, label_h=0.7)

# ---------------------------------------------------------------- 7. KYC
s = content_slide("KYC in minutes, private by design",
                  "Registries first, photos only corroborate; every problem comes with a fix the owner can do",
                  "Specimens: the 12 applicants in kyc_documents/ through the prototype's OCR. GSTIN status: smb_leads.csv.",
                  "Lookups verify the business in seconds; DigiLocker can supply the Udyam certificate. Photos pass a quality gate, are read on our "
                  "own servers, and a checksum repairs misread GSTIN characters without ever changing a digit. All 12 specimen applicants come out "
                  "right: six planted defects caught, six clean applicants passed, no false rejections. Consent per purpose, tokens instead of raw "
                  "identifiers and per-record encryption are covered in the one-page privacy note.")
ksteps = [("Registry lookup", "GSTIN and Udyam status: Active, Cancelled or Suspended"),
          ("Photo quality gate", "Blur and tilt; tilted photos are straightened"),
          ("OCR on our servers", "GSTIN checksum repairs misreads, never a digit"),
          ("Cross-document checks", "Legal name, address, bill from the last 90 days"),
          ("Signatory check", "SIM swap in the last 72 hours, then a decision")]
y = 1.68
for i, (head, body) in enumerate(ksteps):
    c = box(s, 0.5, y, 0.36, 0.36, fill=RED, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.text = str(i + 1)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    r = tf.paragraphs[0].runs[0]
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(12), True, WHITE, FONT
    text(s, 1.0, y - 0.02, 4.1, 0.25, head, size=12, bold=True)
    text(s, 1.0, y + 0.21, 4.1, 0.25, body, size=10, color=SOFT)
    y += 0.56
text(s, 5.55, 1.62, 3.95, 0.3, "12 of 12 specimen applicants correct", size=14, bold=True)
mx, my, cwm, chm = 6.95, 2.25, 1.25, 0.62
text(s, mx, my - 0.27, cwm, 0.25, "Flagged", size=10, bold=True, color=SOFT, align=PP_ALIGN.CENTER)
text(s, mx + cwm + 0.06, my - 0.27, cwm, 0.25, "Passed", size=10, bold=True, color=SOFT, align=PP_ALIGN.CENTER)
for r_i, (rlab, cells) in enumerate([("Planted defect", [("6", RED, WHITE), ("0", TINT, INK)]), ("Clean", [("0", TINT, INK), ("6", GREEN, WHITE)])]):
    yy = my + r_i * (chm + 0.06)
    text(s, 5.55, yy, 1.3, chm, rlab, size=10, bold=True, color=SOFT, anchor=MSO_ANCHOR.MIDDLE)
    for c_i, (v, fill, fg) in enumerate(cells):
        b = box(s, mx + c_i * (cwm + 0.06), yy, cwm, chm, fill=fill, radius=0.08)
        tf = b.text_frame
        tf.text = v
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        rr = tf.paragraphs[0].runs[0]
        rr.font.size, rr.font.bold, rr.font.color.rgb, rr.font.name = Pt(22), True, fg, FONT
text(s, 5.55, 3.7, 3.95, 0.75,
     "Caught: cancelled GSTIN (K01), blurred photo (K04), missing Udyam (K05), tampered GSTIN (K06), name mismatch (K07), "
     "257-day-old bill (K11). Last quarter, 22 activated customers held a cancelled or suspended GSTIN.", size=9.5, color=SOFT)
chips = [("consent", "Consent per purpose"), ("token", "Tokens, not raw IDs"), ("lock", "AES-256-GCM per record"), ("shred", "30-day photo shredding")]
for i, (ic, lab) in enumerate(chips):
    cx = 0.5 + i * 2.27
    icon(s, ic, cx, 4.56, d=0.36)
    text(s, cx + 0.44, 4.56, 1.78, 0.36, lab, size=10, bold=True, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 8. partners
s = content_slide("Partners earn more from digital, not less",
                  "Digital activations cost a fifth as much; partners keep their commission",
                  "Cost: acquisition_cost_inr by lead source over activations, smb_leads.csv. Score: logistic regression, 5-fold CV.",
                  "WhatsApp and referral activations cost about Rs 4,000, field sales over Rs 24,000. Partners are not cut out: they run the same app "
                  "under their partner code and earn the same commission on digital closes in their pin codes. The back-office ranks the leads the "
                  "advisor could not close by a propensity score; the top 30% hold 56% of all activations, and 1,293 dropped leads sit in that band.")
ch_cats = ["Field sales", "Channel partner", "Website form", "Inbound call", "Referral", "WhatsApp"]
ch_vals = [24335, 20851, 6352, 5113, 4099, 4026]
bar_chart(s, 0.4, 1.62, 4.6, 3.1, ch_cats, [("Cost", ch_vals)], [[GREY, GREY, RED, RED, RED, RED]], fmt='"Rs "#,##0', gap=40, cat_size=11, label_size=11)
text(s, 0.5, 4.72, 4.4, 0.3, "Cost per activation by lead source. Blended: Rs 15,053", size=9, color=FAINT)
roles = [("assist", "Assist mode", "Partners run the same app for a customer under their partner code. A digital close in their pin codes earns the same commission."),
         ("callback", "Callback queue", "Stalled leads ranked by propensity (AUC 0.71) with the reason each stopped: 1,293 dropped leads in the top 30%. Calls go through a masked number."),
         ("field", "Field sales where it pays", "Multi-site and manufacturers, at Rs 20,000 to 31,000 a month, plus the exceptions: failed KYC, site surveys, installation.")]
y = 1.66
for ic, head, body in roles:
    icon(s, ic, 5.3, y, d=0.48)
    text(s, 5.95, y - 0.02, 3.55, 0.28, head, size=13, bold=True)
    text(s, 5.95, y + 0.27, 3.55, 0.75, body, size=10.5, color=SOFT)
    y += 1.1

# ---------------------------------------------------------------- 9. economics
s = content_slide("Twice the conversion at a quarter of the cost",
                  "Conservative case 12.6%, target 15%: from fixing the process causes behind two-thirds of drops",
                  "Model: recovery share per drop reason through later stages, at 60% for the conservative case; Rs 400 a digital lead.",
                  "For each drop reason we assume the share a digital journey recovers, for example 60% of 'quote took too long', 40% of 'no time "
                  "for a visit', 5% of 'price too high' and none of 'locked in'. At 60% of those rates, conversion reaches 12.6%: 630 activations a "
                  "quarter instead of 368. The 264 extra customers are worth about Rs 3.9 crore of first-year contract value. At Rs 400 per digital "
                  "lead, cost per activation is Rs 3,175 at 12.6% and Rs 2,667 at 15%.")
bar_chart(s, 0.4, 1.66, 3.6, 2.35, ["Today", "Conservative", "Target"], [("Conversion", [0.074, 0.126, 0.15])],
          [[GREY, RED, RED]], fmt='0.0%', gap=55, horizontal=False, cat_size=11, label_size=13)
text(s, 0.5, 4.02, 3.5, 0.25, "Lead-to-activation conversion", size=9, color=FAINT)
stat(s, 0.5, 4.27, 1.7, "+264", "activations a quarter", big_size=22, label_size=10, label_h=0.3)
stat(s, 2.2, 4.27, 1.9, "Rs 3.9 crore", "first-year contract value", big_size=22, label_size=10, label_h=0.3)
rows = [["Success metric", "Baseline", "6-month target"],
        ["Lead-to-activation conversion", "7.4%", [("15%", {"bold": True, "color": RED})]],
        ["Days from lead to activation", "17.6", [("7 or fewer", {"bold": True, "color": RED})]],
        ["Cost per activation", "Rs 15,053", [("under Rs 4,000", {"bold": True, "color": RED})]],
        ["Status-chase calls per customer", "3.0", [("0.5 or fewer", {"bold": True, "color": RED})]],
        ["6-month churn", "15.2%", [("10% or less", {"bold": True, "color": RED})]],
        [[("Guardrail: ", {"bold": True}), ("eligibility violations", {"bold": False})], "15.2%", [("0", {"bold": True, "color": GREEN})]],
        [[("Guardrail: ", {"bold": True}), ("genuine applicants rejected at KYC", {"bold": False})], "n/a", [("under 2%", {"bold": True, "color": GREEN})]]]
table(s, 4.4, 1.66, 5.1, rows, [2.75, 1.05, 1.3], row_h=0.38, size=10.5, bold_first_col=False,
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT])

# ---------------------------------------------------------------- 10. rollout and risks
s = content_slide("Pilot in 4 cities for 3 months, then scale",
                  "Measured against a control group, with the five metrics and two guardrails as the scorecard",
                  "Pilot cities: the two tier-1 and two tier-2 cities with the most leads in smb_leads.csv.",
                  "We ask for a three-month pilot in Delhi, Mumbai, Vadodara and Kochi, with leads split between the digital journey and the current "
                  "process. If the scorecard holds, all tier-1 cities and ten languages follow by month six, and the assisted path for multi-site "
                  "businesses and manufacturers by month twelve. Each top risk has a control already built into the prototype.")
phases = [("Months 0 to 3", "Pilot: Delhi, Mumbai, Vadodara, Kochi. Leads split against a control group"),
          ("Months 3 to 6", "All tier-1 cities, 10 languages, WhatsApp at scale, partner assist live"),
          ("Months 6 to 12", "Assisted path for multi-site and manufacturers; tier-2 cities")]
pw = 2.9
for i, (when, what) in enumerate(phases):
    px = 0.5 + i * (pw + 0.15)
    b = box(s, px, 1.66, pw, 0.98, fill=RED if i == 0 else TINT, radius=0.08)
    fg = WHITE if i == 0 else INK
    text(s, px + 0.16, 1.74, pw - 0.32, 0.28, when, size=12, bold=True, color=fg)
    text(s, px + 0.16, 2.03, pw - 0.32, 0.56, what, size=10, color=WHITE if i == 0 else SOFT)
    if i < 2:
        arrow(s, px + pw + 0.01, 2.15, px + pw + 0.14, 2.15, color=FAINT)
risks = [("ai", "AI misquotes", "Prices come only from the rules engine; a guard checks every rupee"),
         ("fraud", "KYC fraud", "Registry status, checksum, SIM swap, cross-document match, human review"),
         ("partner", "Partner conflict", "Same commission on digital closes in a partner's pin codes"),
         ("install", "Installation capacity", "Slot booking at checkout; AirFiber where fibre is slow"),
         ("literacy", "Low digital literacy", "Voice, 10 languages, partner assist on the same app"),
         ("regulation", "Regulation", "DPDP controls built in; DoT KYC rules for business SIMs followed")]
for i, (ic, head, body) in enumerate(risks):
    col, row = i % 3, i // 3
    rx, ry = 0.5 + col * 3.05, 2.88 + row * 1.0
    icon(s, ic, rx, ry, d=0.4)
    text(s, rx + 0.52, ry - 0.02, 2.4, 0.26, head, size=11.5, bold=True)
    text(s, rx + 0.52, ry + 0.24, 2.4, 0.62, body, size=9.5, color=SOFT)
text(s, 0.5, 4.74, 9.0, 0.3, [[("The ask: ", {"color": RED}), ("a 3-month, 4-city pilot with a control group, run on the prototype that works today", {})]],
     size=12, bold=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
BG_PATH.unlink()
print("saved", OUT, len(prs.slides), "slides")
