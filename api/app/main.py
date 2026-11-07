"""Accel Business · Udyam Digital API. One stateless container: API under /api, the phone app at /."""
from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .advisor.llm import get_llm
from .backoffice import propensity
from .config import get_settings
from .data_store import store
from .db import SessionLocal, engine
from .engine.graph import NEED_LABELS
from .kyc import service as kyc
from .network.telco import fibre_feasible
from .orders.events import bus
from .privacy import redact
from .privacy.retention import purge
from .routers import advisor, approvals, backoffice, care, judge, orders, voice, whatsapp
from .security import check_rate, production_problems

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
redact.install()
log = logging.getLogger("app")
VERSION = "1.0.0"


async def retention_loop():
    while True:
        await asyncio.sleep(3600)
        try:
            db = SessionLocal()
            log.info("retention: %s", purge(db))
        except Exception as e:  # noqa: BLE001
            log.warning("retention failed: %s", e)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    problems = production_problems()
    if problems:  # production refuses to start on demo settings
        raise RuntimeError("unsafe production config: " + "; ".join(problems))
    bus.bind(asyncio.get_running_loop())
    engine()
    store()
    propensity.warm()
    threading.Thread(target=kyc.warm_cache, daemon=True).start()
    task = asyncio.create_task(retention_loop())
    yield
    task.cancel()


app = FastAPI(title="Accel Business · Udyam Digital", version=VERSION, lifespan=lifespan,
              description="Digital-first acquisition and onboarding for small businesses (Airtel SYNC, Enterprise Track A).")
st = get_settings()
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in st.cors_origins.split(",")], allow_methods=["*"], allow_headers=["*"])


CSP = ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' data: https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
       "base-uri 'self'; form-action 'self'; object-src 'none'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    ok, retry = check_rate(request)
    if not ok:
        return JSONResponse({"detail": "Too many requests. Please wait a moment."}, status_code=429, headers={"Retry-After": str(retry)})
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    if st.environment == "prod":
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    else:
        resp.headers.setdefault("Content-Security-Policy", CSP)
    return resp


for r in (advisor.router, orders.router, care.router, approvals.router, backoffice.router, judge.router, whatsapp.router, voice.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    llm = get_llm()
    return {"status": "ok", "version": VERSION, "llm": {"provider": llm.provider, "model": llm.model} if llm else None,
            "judge_mode": st.judge_mode, "products": len(store().products), "region": "asia-south1 (Mumbai) when deployed on Cloud Run"}


@app.get("/api/catalogue")
def catalogue():
    return {"products": [p.__dict__ | {"tiers": sorted(p.tiers)} for p in store().products.values()], "needs": NEED_LABELS}


@app.get("/api/cities")
def cities():
    """Cities and tiers from the leads data (the synthetic PINs aren't real, so tier comes from the city)."""
    from .advisor.extract import EXTRA_TIERS
    known = {**EXTRA_TIERS, **store().city_tier}
    return {"cities": [{"city": c, "tier": known[c]} for c in sorted(known)]}


@app.get("/api/serviceability/{pincode}")
def serviceability(pincode: str):
    f = fibre_feasible(pincode)
    return {"pincode": pincode, "fibre": f, "airfiber": True, "message": "Fibre available" if f else "Fibre not yet; AirFiber is plug-and-play in 2 days"}


@app.exception_handler(PermissionError)
async def perm(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=403)


# ---- the phone app (built React SPA) --------------------------------------------------
dist: Path = st.web_dist
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = dist / path
        if path and f.is_file() and dist in f.resolve().parents:
            return FileResponse(f)
        return FileResponse(dist / "index.html")
