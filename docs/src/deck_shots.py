"""Phone-sized screenshots of the K09 journey (Kaveri Insurance Advisors, Visakhapatnam) for the deck.

Run against a local server: python docs/src/deck_shots.py [base_url]
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[1] / "screens" / "deck"
OUT.mkdir(parents=True, exist_ok=True)
TE_MSG = "విశాఖపట్నంలో మా ఇన్సూరెన్స్ ఏజెన్సీ ఉంది, 25 మంది ఉద్యోగులు. ఇంటర్నెట్, ఈమెయిల్ కావాలి."
GSTIN = "37LDYXK0296F1ZB"


async def to_english(pg):
    await pg.get_by_role("button", name="Change language").click()
    await pg.get_by_role("button", name="English", exact=True).click()
    await pg.wait_for_timeout(300)


async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg = await ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        await pg.goto(BASE + "/advisor?lang=te")
        await pg.wait_for_timeout(800)
        box = pg.get_by_role("textbox").first
        await box.fill(TE_MSG)
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1200)
        for answer in (GSTIN, "లేదు", "లేదు"):
            if await pg.get_by_role("button", name="నా కొటేషన్ చూడండి").count():
                break
            await box.fill(answer)
            await pg.keyboard.press("Enter")
            await pg.wait_for_timeout(1200)
        await pg.screenshot(path=str(OUT / "1_advisor_te.png"))

        await pg.get_by_role("button", name="నా కొటేషన్ చూడండి").click()
        await pg.wait_for_timeout(1500)
        await to_english(pg)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(OUT / "2_quote.png"))

        await pg.get_by_placeholder("98XXXXXXXX").fill("9876543210")
        await pg.get_by_role("button", name="Place order").click()
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(OUT / "3_consent.png"))
        await pg.get_by_role("button", name="Agree and continue").click()
        await pg.wait_for_timeout(1500)

        await pg.get_by_text("Demo: use a specimen applicant").click()
        await pg.get_by_role("button", name="K09", exact=True).click()
        await pg.wait_for_timeout(9000)
        verify = pg.get_by_role("button", name="Verify now")
        if await verify.count() and await verify.is_enabled():
            await verify.click()
            await pg.wait_for_timeout(9000)
        stamp = pg.get_by_text("Verified", exact=True).last
        await stamp.scroll_into_view_if_needed()
        await pg.evaluate("window.scrollBy(0, 220)")
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(OUT / "4_kyc_verified.png"))
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=str(OUT / "4b_kyc_top.png"))

        await pg.get_by_role("button", name="Continue").click()
        await pg.wait_for_timeout(1200)
        await pg.get_by_placeholder("name@bank").fill("anita@okaxis")
        await pg.get_by_role("button", name="Pay with UPI Autopay").click()
        await pg.wait_for_timeout(1500)
        slots = pg.locator("button[aria-pressed]")
        await slots.nth(1).click()
        await pg.wait_for_timeout(200)
        n = await slots.count()
        await slots.nth(n - 2).click()
        await pg.screenshot(path=str(OUT / "5_pay.png"))
        await pg.get_by_role("button", name="Book this slot").click()
        try:
            await pg.wait_for_url("**/track/**", timeout=8000)
            await pg.wait_for_timeout(1800)
            await pg.screenshot(path=str(OUT / "6_tracker.png"))
            await pg.get_by_role("button", name="Demo: complete next step").click(timeout=8000)
            await pg.wait_for_timeout(1500)
            await pg.evaluate("window.scrollTo(0, 0)")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=str(OUT / "7_tracker_live.png"))
        except Exception as err:  # keep a picture of what went wrong
            await pg.screenshot(path=str(OUT / "debug_track.png"), full_page=True)
            print("tracker step failed:", pg.url, str(err)[:200])
        print("errors:", errors or "none")
        await br.close()


asyncio.run(main())
