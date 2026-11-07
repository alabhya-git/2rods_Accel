"""Builds the K02R demo applicant: K02's clinic in a rented unit.

The official pack has no rented shop, so this writes two images into data/demo_extra/:
K02's electricity bill re-issued in the landlord's name, and a rent agreement naming the
landlord, the tenant and the same address. Run once; the images are committed.

    python api/scripts/make_rented_demo.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "demo_extra"
LANDLORD = "Sunita Banerjee"
TENANT = "Joseph Shah (Prop. Harmony Dental Care)"
ADDRESS = ("Shop/Unit 199, Station Road, Kolkata, West Be", "ngal - 347550")  # wrapped exactly as on K02's bill
PAPER, BAND, NAVY, INK, LABEL, RED = (252, 252, 248), (232, 234, 244), (24, 32, 64), (17, 17, 17), (34, 34, 34), (150, 30, 30)


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def bill() -> Image.Image:
    im = Image.open(ROOT / "data" / "kyc_documents" / "K02_address_proof.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle((512, 316, 1180, 364), fill=PAPER)  # the "Billed to" value
    d.text((520, 323), LANDLORD, font=font(False, 26), fill=INK)
    d.text((80, 1700), "Demo variant (Udyam Digital): the same bill, in the landlord's name.", font=font(False, 18), fill=RED)
    return im


def agreement() -> Image.Image:
    im = Image.new("RGB", (1240, 1754), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((40, 40, 1200, 190), fill=BAND)
    d.rectangle((40, 190, 1200, 1714), outline=(51, 51, 51), width=3)
    d.text((80, 72), "Specimen: Rent Agreement", font=font(True, 40), fill=NAVY)
    d.text((80, 134), "Leave and licence for business premises - synthetic demo document", font=font(False, 21), fill=(68, 68, 68))
    rows = [("Landlord", LANDLORD), ("Tenant", TENANT), ("Premises", ADDRESS[0]), ("", ADDRESS[1]),
            ("Agreement date", "2025-11-01"), ("Valid till", "2026-10-31"), ("Monthly rent (INR)", "18,000")]
    y = 250
    for label, value in rows:
        if label:
            d.text((90, y), label, font=font(True, 23), fill=LABEL)
        d.text((520, y), value, font=font(False, 25), fill=INK)
        y += 70
    d.text((80, 1660), "Udyam Digital demo document, not part of the official specimen pack. Fictional people and address.",
           font=font(False, 18), fill=RED)
    return im


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    bill().save(OUT / "K02R_address_proof.png")
    agreement().save(OUT / "K02R_rent_agreement.png")
    print("wrote", *sorted(p.name for p in OUT.glob("K02R_*.png")))
