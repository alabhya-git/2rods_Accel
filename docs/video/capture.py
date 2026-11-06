"""Drives the running prototype and saves a JPEG for every state the demo video shows.

usage: python docs/video/capture.py [base_url]   (default http://127.0.0.1:8000)
Writes docs/video/shots/<name>.jpg. compose.py turns them into the video.
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent / "shots"
OUT.mkdir(parents=True, exist_ok=True)
TE_MSG = "విశాఖపట్నంలో మా ఇన్సూరెన్స్ ఏజెన్సీ ఉంది, 25 మంది ఉద్యోగులు. 1 Gbps ఇంటర్నెట్, ఈమెయిల్ కావాలి."
GSTIN = "37LDYXK0296F1ZB"
taken: list[str] = []


async def shot(pg, name, full=False):
    await pg.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=92, full_page=full)
    taken.append(name)


async def type_in(pg, locator, textval, name, steps=6):
    await locator.click()
    n = len(textval)
    for i in range(1, steps + 1):
        await locator.fill(textval[: round(n * i / steps)])
        await pg.wait_for_timeout(60)
        await shot(pg, f"{name}_{i}")


async def wait_idle(pg, ms=900):
    await pg.wait_for_load_state("networkidle")
    await pg.wait_for_timeout(ms)


async def to_english(pg):
    await pg.get_by_role("button", name="Change language").click()
    await pg.wait_for_timeout(250)
    await shot(pg, "lang_menu")
    await pg.get_by_role("button", name="English", exact=True).click()
    await pg.wait_for_timeout(400)


def k11_order() -> tuple[str, str]:
    """A second applicant (K11, Trinity Bake House, Ludhiana) whose electricity bill is 257 days old."""
    c = httpx.Client(base_url=BASE, timeout=60)
    o = c.post("/api/orders", json={"profile": {"segment": "multi", "business_type": "Bakery chain", "employees": 117, "sites": 3,
                                                "city": "Ludhiana", "city_tier": 2, "has_gstin": True},
                                    "items": {"P02": 3, "P07": 3, "P19": 3}, "phone": "9855512345", "specimen": "K11"}).json()
    c.post(f"/api/orders/{o['order_id']}/consent?key={o['access_key']}",
           json={"choices": {"kyc_verification": True, "service_delivery": True, "order_updates": True}})
    return o["order_id"], o["access_key"]


async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg = await ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        # ---- home and language
        await pg.goto(BASE + "/?lang=en")
        await wait_idle(pg)
        await shot(pg, "home_en")
        await pg.get_by_role("button", name="తెలుగు").click()
        await pg.wait_for_timeout(500)
        await shot(pg, "home_te")
        await pg.get_by_role("button", name="సలహాదారుతో ప్రారంభించండి").click()
        await wait_idle(pg)
        await shot(pg, "adv_greet")

        # ---- advisor in Telugu
        box = pg.get_by_role("textbox").first
        await type_in(pg, box, TE_MSG, "adv_type1")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(120)
        await shot(pg, "adv_wait1")
        await wait_idle(pg, 1200)
        await shot(pg, "adv_ask_gstin")
        await type_in(pg, box, GSTIN, "adv_type2", steps=3)
        await pg.keyboard.press("Enter")
        await wait_idle(pg, 1500)
        await shot(pg, "adv_reco_end")
        # scroll the conversation up to the start of the recommendation
        await pg.evaluate("""() => { const b = [...document.querySelectorAll('.bubble-ai')]; const el = b[b.length - 1]; el && el.scrollIntoView({block: 'start'}); }""")
        await pg.wait_for_timeout(500)
        await shot(pg, "adv_reco_top")
        await pg.get_by_role("button", name="ఇది ఎందుకు?").click()
        await pg.wait_for_timeout(600)
        await shot(pg, "adv_why")
        await pg.get_by_role("button", name="ఇది ఎందుకు?").click()
        await pg.wait_for_timeout(400)

        # ---- quote
        await pg.get_by_role("button", name="నా కొటేషన్ చూడండి").click()
        await wait_idle(pg, 1200)
        await shot(pg, "quote_top")
        tick = pg.get_by_role("checkbox", name="Backup 4G/5G Failover")
        await tick.scroll_into_view_if_needed()
        await pg.wait_for_timeout(300)
        await shot(pg, "quote_addons")
        await tick.click()
        await pg.wait_for_timeout(900)
        await shot(pg, "quote_failover_on")
        await pg.get_by_role("radio", name="24 నెలలు").click()
        await pg.wait_for_timeout(900)
        await shot(pg, "quote_24")
        phone = pg.get_by_placeholder("98XXXXXXXX")
        await phone.scroll_into_view_if_needed()
        await type_in(pg, phone, "9876543210", "quote_phone", steps=2)
        await pg.get_by_role("button", name="ఆర్డర్ చేయండి").click()
        await wait_idle(pg, 1200)

        # ---- consent (Telugu, then English for the judges)
        await shot(pg, "consent_te")
        await to_english(pg)
        await shot(pg, "consent_en")
        upd = pg.get_by_role("switch").nth(2)
        if await upd.count():
            await upd.scroll_into_view_if_needed()
            await upd.click()
            await pg.wait_for_timeout(400)
            await shot(pg, "consent_updates_on")
        await pg.get_by_role("button", name="Agree and continue").click()
        await wait_idle(pg, 1200)

        # ---- Smart KYC
        await shot(pg, "kyc_top")
        await type_in(pg, pg.locator("#gstin"), GSTIN, "kyc_gstin", steps=2)
        await pg.get_by_role("button", name="Check").click()
        await wait_idle(pg, 1200)
        await shot(pg, "kyc_registry")
        await pg.get_by_text("Demo: use a specimen applicant").click()
        await pg.get_by_role("button", name="K09", exact=True).click()
        await pg.wait_for_timeout(400)
        await shot(pg, "kyc_reading")
        await wait_idle(pg, 9000)
        await pg.evaluate("window.scrollTo(0, 260)")
        await pg.wait_for_timeout(400)
        await shot(pg, "kyc_docs_1")
        await pg.evaluate("window.scrollBy(0, 560)")
        await pg.wait_for_timeout(400)
        await shot(pg, "kyc_docs_2")
        verify = pg.get_by_role("button", name="Verify now")
        if await verify.count() and await verify.is_enabled():
            await verify.click()
            await wait_idle(pg, 6000)
        stamp = pg.get_by_text("Verified", exact=True).last
        await stamp.scroll_into_view_if_needed()
        summary = pg.get_by_text("checks passed")
        if await summary.count():
            await summary.first.click()
            await pg.wait_for_timeout(400)
        await stamp.scroll_into_view_if_needed()
        await pg.evaluate("window.scrollBy(0, 300)")
        await pg.wait_for_timeout(400)
        await shot(pg, "kyc_verified")
        k09_url = pg.url

        # ---- K11: the stale bill, with its fix
        oid, key = k11_order()
        await pg.goto(f"{BASE}/order/{oid}/kyc?key={key}")
        await wait_idle(pg)
        await pg.get_by_text("Demo: use a specimen applicant").click()
        await pg.get_by_role("button", name="K11", exact=True).click()
        await wait_idle(pg, 9000)
        verify = pg.get_by_role("button", name="Verify now")
        if await verify.count() and await verify.is_enabled():
            await verify.click()
            await wait_idle(pg, 6000)
        fix = pg.get_by_text("How to fix").first
        if await fix.count():
            await fix.scroll_into_view_if_needed()
            await pg.evaluate("window.scrollBy(0, 180)")
        await pg.wait_for_timeout(400)
        await shot(pg, "k11_fix")
        bill = pg.get_by_text("Electricity bill (last 90 days)").first
        await bill.scroll_into_view_if_needed()
        await pg.evaluate("window.scrollBy(0, -60)")
        await pg.wait_for_timeout(300)
        await shot(pg, "k11_bill")

        # ---- back to K09: pay, book, track
        await pg.goto(k09_url)
        await wait_idle(pg)
        await pg.get_by_role("button", name="Continue").click()
        await wait_idle(pg)
        await shot(pg, "pay_top")
        await type_in(pg, pg.get_by_placeholder("name@bank"), "anita@okaxis", "pay_upi", steps=2)
        await pg.get_by_role("button", name="Pay with UPI Autopay").click()
        await wait_idle(pg, 1200)
        await shot(pg, "pay_paid")
        slots = pg.locator("button[aria-pressed]")
        await slots.nth(1).click()
        await pg.wait_for_timeout(200)
        n = await slots.count()
        await slots.nth(n - 2).click()
        await pg.wait_for_timeout(300)
        await shot(pg, "pay_slot")
        await pg.get_by_role("button", name="Book this slot").click()
        await pg.wait_for_url("**/track/**")
        await wait_idle(pg, 1600)
        await shot(pg, "track_progress")
        for i in range(2):  # failover goes live, then the fibre: the order is complete
            await pg.get_by_role("button", name="Demo: complete next step").click()
            await pg.wait_for_timeout(1400)
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.wait_for_timeout(300)
        await shot(pg, "track_live")
        await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await pg.wait_for_timeout(500)
        await shot(pg, "track_data")

        # ---- desktop: partner desk and judge console
        d = await br.new_context(viewport={"width": 1440, "height": 810}, device_scale_factor=1.3333)
        dp = await d.new_page()
        dp.on("pageerror", lambda e: errors.append(str(e)))
        await dp.goto(BASE + "/partner")
        await wait_idle(dp)
        await dp.fill("input[type=password]", "accel-demo")
        await dp.keyboard.press("Enter")
        await wait_idle(dp, 2500)
        await shot(dp, "partner_queue")
        await dp.get_by_role("button", name="Call (masked)").first.click()
        await dp.wait_for_timeout(700)
        await shot(dp, "partner_call")
        for tab, name in (("Reviews", "partner_reviews"), ("Metrics", "partner_metrics")):
            b = dp.get_by_role("button", name=tab)
            if await b.count():
                await b.first.click()
                await wait_idle(dp, 900)
                await shot(dp, name)
        await dp.goto(BASE + "/judge")
        await wait_idle(dp)
        await dp.get_by_role("button", name="Run all").click()
        await wait_idle(dp, 1800)
        await shot(dp, "judge_scenarios")
        await dp.get_by_role("button", name="Run OCR and checks").click()
        await dp.wait_for_timeout(12000)
        await wait_idle(dp, 500)
        await dp.get_by_text("false rejections").wait_for(timeout=60000)
        await dp.get_by_role("heading", name="Smart KYC on the 12 specimen applicants").evaluate("el => el.scrollIntoView({block: 'start'})")
        await dp.evaluate("window.scrollBy(0, -24)")
        await dp.wait_for_timeout(400)
        await shot(dp, "judge_kyc")
        await br.close()
    (OUT / "manifest.json").write_text(json.dumps(taken, indent=1))
    print(len(taken), "shots; page errors:", errors or "none")


asyncio.run(main())
