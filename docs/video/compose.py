"""Composes the demo video from the captured shots: python docs/video/compose.py

Each shot becomes a 1920x1080 frame (phone or desktop screen, step bar, title, caption). Frames are
grouped into scenes, each scene is encoded once with a running clock, and the scenes are joined
without re-encoding. Also writes captions.srt with the same text and timings.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
FRAMES = HERE / "frames"
BUILD = HERE / "build"
FONTS = HERE / "fonts"
OUT = HERE / "udyam-digital-demo.mp4"
W, H, FPS = 1920, 1080, 30

BG, BG_RULE, MARGIN = (18, 21, 43), (27, 32, 62), (120, 22, 40)
WHITE, TEXT, SOFT, DIM = (255, 255, 255), (228, 231, 240), (154, 160, 184), (92, 98, 128)
RED, HALDI, LEAF = (200, 16, 46), (242, 169, 0), (61, 190, 127)
STEPS = ["Advisor", "Quote", "Consent", "KYC", "Pay", "Track"]


def font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Baloo2-{weight}.ttf"), size)


def wrap(draw, text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def paragraph(draw, xy, text, f, width, fill, line_h):
    x, y = xy
    for ln in wrap(draw, text, f, width):
        draw.text((x, y), ln, font=f, fill=fill)
        y += line_h
    return y


def background():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for y in range(60, H, 54):  # faint ledger rules, the app's khata motif
        d.line([(0, y), (W, y)], fill=BG_RULE, width=1)
    return im


def rounded(img: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), mask)
    return out


def chrome(im, d, desktop=False):
    d.text((60, H - 62), "Dukaan Connect", font=font(700, 26), fill=WHITE)
    d.text((60 + d.textlength("Dukaan Connect", font=font(700, 26)) + 14, H - 62), "Working prototype",
           font=font(500, 26), fill=SOFT)
    d.text((W - 60, 34), "demo clock", font=font(500, 22), fill=SOFT, anchor="ra")


def step_bar(d, x, y, active):
    f = font(700, 26)
    for i, name in enumerate(STEPS):
        w = d.textlength(name, font=f) + 36
        if i == active:
            d.rounded_rectangle([x, y, x + w, y + 46], 23, fill=RED)
            d.text((x + 18, y + 7), name, font=f, fill=WHITE)
        else:
            col = SOFT if active is not None and i < active else DIM
            d.rounded_rectangle([x, y, x + w, y + 46], 23, outline=col, width=2)
            d.text((x + 18, y + 7), name, font=f, fill=col)
        x += w + 12


def phone_frame(s):
    im = background()
    d = ImageDraw.Draw(im)
    shot = Image.open(SHOTS / f"{s['img']}.jpg").convert("RGB")
    ph_h = 930
    ph_w = round(shot.width * ph_h / shot.height)
    shot = shot.resize((ph_w, ph_h), Image.LANCZOS)
    px, py = 250, (H - ph_h) // 2 - 14
    d.rounded_rectangle([px - 14, py - 14, px + ph_w + 14, py + ph_h + 14], 52, fill=(6, 7, 14), outline=(64, 70, 104), width=2)
    im.paste(rounded(shot, 40), (px, py), rounded(shot, 40))
    x0, width = px + ph_w + 140, W - (px + ph_w + 140) - 90
    step_bar(d, x0, 120, s.get("step"))
    y = 250
    if s.get("title"):
        d.text((x0, y), s["title"], font=font(800, 66), fill=WHITE)
        y += 104
    y = paragraph(d, (x0, y), s.get("caption", ""), font(500, 42), width, TEXT, 58)
    if s.get("note"):
        paragraph(d, (x0, 860), s["note"], font(500, 27), width, SOFT, 38)
    chrome(im, d)
    return im


def desk_frame(s):
    im = background()
    d = ImageDraw.Draw(im)
    shot = Image.open(SHOTS / f"{s['img']}.jpg").convert("RGB")
    sw, sh = 1424, 801
    shot = shot.resize((sw, sh), Image.LANCZOS)
    sx, sy = (W - sw) // 2, 196
    d.rounded_rectangle([sx - 2, sy - 2, sx + sw + 2, sy + sh + 2], 16, outline=(64, 70, 104), width=2)
    im.paste(rounded(shot, 14), (sx, sy), rounded(shot, 14))
    d.text((sx, 40), s["title"], font=font(800, 52), fill=WHITE)
    paragraph(d, (sx, 108), s.get("caption", ""), font(500, 32), sw - 120, TEXT, 40)
    d.text((W - 60, H - 62), "Dukaan Connect, partner and judge views", font=font(500, 24), fill=SOFT, anchor="ra")
    d.text((W - 60, 34), "demo clock", font=font(500, 22), fill=SOFT, anchor="ra")
    return im


def card_frame(s):
    im = background()
    d = ImageDraw.Draw(im)
    d.line([(150, 0), (150, H)], fill=MARGIN, width=3)  # the khata's red margin
    x, width = 230, 1480
    y = 210
    if s.get("kicker"):
        d.text((x, y), s["kicker"], font=font(700, 34), fill=HALDI)
        y += 76
    for big in s.get("big", []):
        y = paragraph(d, (x, y), big, font(800, 84), width, WHITE, 100) + 10
    y += 26
    for line in s.get("lines", []):
        y = paragraph(d, (x, y), line, font(500, 44), width, TEXT, 60) + 16
    if s.get("grid"):
        gy = y + 10
        for i, (num, label) in enumerate(s["grid"]):
            gx = x + (i % 2) * 760
            yy = gy + (i // 2) * 170
            d.text((gx, yy), num, font=font(800, 62), fill=LEAF if i in (1, 2) else HALDI)
            paragraph(d, (gx, yy + 78), label, font(500, 32), 700, TEXT, 40)
    if s.get("foot"):
        paragraph(d, (x, H - 150), s["foot"], font(500, 28), width, SOFT, 38)
    return im


# ------------------------------------------------------------------ the script
K09 = "Specimen applicant K09: Kaveri Insurance Advisors, Visakhapatnam. Official synthetic data."
SCENES = [
    ("open", [
        dict(kind="card", dur=5.5, kicker="Dukaan Connect, April to June 2026", big=["7 in 100 small-business leads became customers."],
             lines=["They waited 17.6 days, and called three times to ask where their order was."]),
        dict(kind="card", dur=5.0, kicker="Dukaan Connect, April to June 2026", big=["7 in 100 small-business leads became customers."],
             lines=["They waited 17.6 days, and called three times to ask where their order was.",
                    "Watch Anita, who runs an insurance agency in Visakhapatnam, do it in one sitting, on her phone."]),
    ]),
    ("advisor", [
        dict(img="home_en", dur=3.0, step=0, title="Her language", caption="Anita opens Dukaan Connect on her phone. Ten Indian languages; she picks Telugu.", note=K09),
        dict(img="home_te", dur=2.5, step=0, title="Her language", caption="Anita opens Dukaan Connect on her phone. Ten Indian languages; she picks Telugu.", note=K09),
        dict(img="adv_greet", dur=2.5, step=0, title="Advisor", caption="She describes her business as she would to a person. Voice works too; here she types."),
        *[dict(img=f"adv_type1_{i}", dur=0.3, step=0, title="Advisor", caption="She describes her business as she would to a person. Voice works too; here she types.") for i in range(1, 7)],
        dict(img="adv_wait1", dur=0.6, step=0, title="Advisor", caption="She describes her business as she would to a person. Voice works too; here she types."),
        dict(img="adv_ask_gstin", dur=5.0, step=0, title="Advisor",
             caption="Understood: insurance agency, 25 staff, Visakhapatnam, 1 Gbps internet and email. One question left: her GSTIN."),
        *[dict(img=f"adv_type2_{i}", dur=0.35, step=0, title="Advisor",
               caption="Understood: insurance agency, 25 staff, Visakhapatnam, 1 Gbps internet and email. One question left: her GSTIN.") for i in range(1, 4)],
        dict(img="adv_reco_top", dur=6.0, step=0, title="Advisor",
             caption="One registry lookup fills in the business. Then one bundle, with a reason for every product, in Telugu."),
        dict(img="adv_reco_end", dur=5.0, step=0, title="Advisor",
             caption="Clinic & Office Pro, Rs 8,758 a month. She asked for 1 Gbps; Biz Fibre 1G is sold only in tier-1 cities, so she gets Biz Fibre 300."),
        dict(img="adv_why", dur=8.0, step=0, title="Why this?",
             caption="What was understood, what the rules engine chose, and the rule behind every refusal. The AI talks; it never picks a product or a price."),
    ]),
    ("quote", [
        dict(img="quote_top", dur=4.5, step=1, title="Quote", caption="One monthly price, on a ledger she already knows how to read. Every line says why it is there."),
        dict(img="quote_addons", dur=2.5, step=1, title="Quote", caption="Add-ons tick on and off."),
        dict(img="quote_failover_on", dur=3.5, step=1, title="Quote", caption="She adds backup internet. The price updates at once, re-priced on the server."),
        dict(img="quote_24", dur=4.0, step=1, title="Quote", caption="A 24-month contract brings it down to Rs 8,607 a month, plus GST."),
        *[dict(img=f"quote_phone_{i}", dur=0.6, step=1, title="Quote", caption="Her mobile number, for updates. Then: place order.") for i in (1, 2)],
    ]),
    ("consent", [
        dict(img="consent_te", dur=3.5, step=2, title="Consent", caption="Before any KYC: a notice in her language, with one switch per purpose."),
        dict(img="lang_menu", dur=2.0, step=2, title="Consent", caption="Every screen works in all ten languages. Switching to English for the judges."),
        dict(img="consent_en", dur=4.0, step=2, title="Consent", caption="Verifying and installing are needed. Order updates and offers are optional, and offers start off."),
        dict(img="consent_updates_on", dur=3.5, step=2, title="Consent", caption="She allows order updates. Each choice is recorded with its notice version and can be withdrawn in one tap.",
             note="DPDP Act 2023 and DPDP Rules 2025"),
    ]),
    ("kyc", [
        dict(img="kyc_top", dur=3.0, step=3, title="Smart KYC", caption="Registries first. The photos only confirm what the registries say."),
        *[dict(img=f"kyc_gstin_{i}", dur=0.5, step=3, title="Smart KYC", caption="Registries first. The photos only confirm what the registries say.") for i in (1, 2)],
        dict(img="kyc_registry", dur=3.5, step=3, title="Smart KYC", caption="The GSTIN checks out against the registry: Kaveri Insurance Advisors, Proprietorship, Active."),
        dict(img="kyc_reading", dur=3.0, step=3, title="Smart KYC", caption="Four document photos, read by OCR on our own servers. For the demo, the official specimen photos of applicant K09."),
        dict(img="kyc_docs_1", dur=3.5, step=3, title="Smart KYC", caption="Each document is read and matched: names, address, dates. Identifiers stay masked on screen."),
        dict(img="kyc_docs_2", dur=2.5, step=3, title="Smart KYC", caption="Each document is read and matched: names, address, dates. Identifiers stay masked on screen."),
        dict(img="kyc_verified", dur=6.0, step=3, title="Verified",
             caption="14 checks passed: GSTIN checksum and registry status, legal name, a bill from the last 90 days, the signatory's SIM-swap check."),
        dict(img="k11_fix", dur=6.5, step=3, title="When something is wrong",
             caption="Another applicant, Trinity Bake House: the electricity bill is 257 days old. She gets a fix she can do alone, not a rejection.",
             note="Specimen applicant K11, Ludhiana"),
        dict(img="k11_bill", dur=3.5, step=3, title="When something is wrong", caption="Only that one photo needs retaking; everything else stays verified.",
             note="Specimen applicant K11, Ludhiana"),
    ]),
    ("pay_track", [
        dict(img="pay_top", dur=2.5, step=4, title="Pay and book", caption="Back to Anita. The first month by UPI Autopay."),
        *[dict(img=f"pay_upi_{i}", dur=0.5, step=4, title="Pay and book", caption="Back to Anita. The first month by UPI Autopay.") for i in (1, 2)],
        dict(img="pay_paid", dur=2.5, step=4, title="Pay and book", caption="Paid. The mandate covers each month's bill from now on."),
        dict(img="pay_slot", dur=2.5, step=4, title="Pay and book", caption="She picks an installation slot that suits her."),
        dict(img="track_progress", dur=5.5, step=5, title="Tracker",
             caption="Cloud services go live at once; fibre is dated from the catalogue's install times. Customers who chased five times churned at 27.9%."),
        dict(img="track_live", dur=4.0, step=5, title="Tracker", caption="When the engineer finishes, a WhatsApp message: everything is live. No calls needed."),
        dict(img="track_data", dur=4.0, step=5, title="Her data", caption="From the same screen she can withdraw any consent, or download or erase her data."),
    ]),
    ("partner", [
        dict(kind="desk", img="partner_queue", dur=6.5, title="Partner desk",
             caption="Leads the journey did not close, ranked by a propensity score (AUC 0.71), with why each stalled and the next action."),
        dict(kind="desk", img="partner_call", dur=3.5, title="Partner desk", caption="Calls go through a masked number: partners never see the customer's phone."),
        dict(kind="desk", img="partner_reviews", dur=3.5, title="Partner desk", caption="KYC exceptions land here. Trinity Bake House is already fixing her own bill."),
        dict(kind="desk", img="partner_metrics", dur=4.5, title="Partner desk", caption="Every pilot metric against last quarter's baseline, computed from the data."),
    ]),
    ("judge", [
        dict(kind="desk", img="judge_scenarios", dur=5.5, title="Judge console",
             caption="28 rules-engine scenarios, run live: tier-only products, staff and site minimums, cancelled GSTINs, dependencies, budgets."),
        dict(kind="desk", img="judge_kyc", dur=6.5, title="Judge console",
             caption="All 12 specimen applicants through the real OCR: six planted defects caught, six clean applicants passed, no false rejections."),
    ]),
    ("close", [
        dict(kind="card", dur=11.0, kicker="Dukaan Connect", big=["One sitting on a phone, in the owner's language."],
             grid=[("~12 minutes", "designed journey, against 17.6 days today"), ("28 of 28", "advisor scenarios pass, with or without an LLM"),
                   ("12 of 12", "KYC specimens correct, 0 false rejections"), ("15%", "conversion target, under Rs 4,000 per activation")],
             foot="Code, live link and business case are on the submission page. Dukaan Connect is our product prototype; all data is the official synthetic pack."),
    ]),
]
CLOCK = {"advisor", "quote", "consent", "kyc", "pay_track", "partner", "judge"}


def render_frames():
    FRAMES.mkdir(exist_ok=True)
    n = 0
    for _, shots in SCENES:
        for s in shots:
            kind = s.get("kind", "phone")
            im = {"phone": phone_frame, "desk": desk_frame, "card": card_frame}[kind](s)
            s["frame"] = FRAMES / f"{n:03d}.jpg"
            im.save(s["frame"], quality=93)
            n += 1
    return n


def encode_scene(i, name, shots, start, first, last):
    lst = BUILD / f"{i:02d}_{name}.txt"
    lines = []
    for s in shots:
        lines += [f"file '{s['frame']}'", f"duration {s['dur']:.3f}"]
    lines.append(f"file '{shots[-1]['frame']}'")
    lst.write_text("\n".join(lines) + "\n")
    dur = sum(s["dur"] for s in shots)
    vf = [f"fps={FPS}", "format=yuv420p"]
    if name in CLOCK:
        fontfile = str(FONTS / "Baloo2-700.ttf")
        clock = (f"drawtext=fontfile={fontfile}:fontsize=46:fontcolor=white:x=w-tw-60:y=62:"
                 f"text='%{{eif\\:floor((t+{start:.3f})/60)\\:d}}\\:%{{eif\\:mod(floor(t+{start:.3f})\\,60)\\:d\\:2}}'")
        vf.append(clock)
    if first:
        vf.append("fade=t=in:st=0:d=0.6")
    if last:
        vf.append(f"fade=t=out:st={dur - 0.8:.3f}:d=0.8")
    tmp = BUILD / f"{i:02d}_{name}.part.mp4"
    final = BUILD / f"{i:02d}_{name}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", ",".join(vf),
           "-t", f"{dur:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(tmp)]
    subprocess.run(cmd, check=True)
    os.replace(tmp, final)
    return final, dur


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt():
    cues, t = [], 0.0
    for _, shots in SCENES:
        for s in shots:
            text = s.get("caption") or " ".join(s.get("big", []) + s.get("lines", []))
            if cues and cues[-1][2] == text:
                cues[-1][1] = t + s["dur"]
            else:
                cues.append([t, t + s["dur"], text])
            t += s["dur"]
    out = [f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues, 1)]
    (HERE / "captions.srt").write_text("\n".join(out), encoding="utf-8")
    return t


def main():
    BUILD.mkdir(exist_ok=True)
    n = render_frames()
    files, start = [], 0.0
    clock_start = None
    for i, (name, shots) in enumerate(SCENES):
        if name in CLOCK and clock_start is None:
            clock_start = start
        f, dur = encode_scene(i, name, shots, start - (clock_start or 0.0), i == 0, i == len(SCENES) - 1)
        files.append(f)
        start += dur
    total = write_srt()
    joined = BUILD / "joined.mp4"
    (BUILD / "concat.txt").write_text("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(BUILD / "concat.txt"), "-c", "copy", str(joined)], check=True)
    tmp = OUT.with_suffix(".part.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
    os.replace(tmp, OUT)
    print(f"{n} frames, {len(files)} scenes, {total:.1f} s ->", OUT)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "frames":
        render_frames()
        print("frames only")
    else:
        main()
