"""Event bus for the real-time tracker.

Every fulfilment step is an event row (durable) and a published message (live).
  * Postgres (cloud): the message is a NOTIFY sent inside the same transaction as the
    event row, so Postgres delivers it only if the row commits. Every instance LISTENs,
    so any instance can serve any tracker stream: no Redis needed.
  * SQLite (local): messages are queued on the session and published after commit.
  * Optional Redis (REDIS_URL) still relays between instances when Postgres isn't used.
  * A tracker that reconnects reloads the order (the event rows), so nothing is lost.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from collections import defaultdict

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ..config import get_settings

log = logging.getLogger("app.events")
INSTANCE = uuid.uuid4().hex[:12]
QUEUE_MAX = 200
CHANNEL = "order_events"


def _pg_dsn() -> str | None:
    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "postgresql":
        return None
    return url.set(drivername="postgresql").render_as_string(hide_password=False)  # psycopg wants a plain libpq URL


class Bus:
    def __init__(self):
        self.subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self.loop: asyncio.AbstractEventLoop | None = None
        self.pg = _pg_dsn()
        self.redis = None
        self._listener: threading.Thread | None = None
        url = get_settings().redis_url
        if url and not self.pg:
            try:  # pragma: no cover - optional dependency
                import redis

                self.redis = redis.Redis.from_url(url)
            except Exception as e:  # noqa: BLE001
                log.warning("redis unavailable, using in-process bus: %s", e)

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        if self._listener:
            return
        target = self._listen_pg if self.pg else (self._relay_redis if self.redis else None)
        if target:  # pragma: no cover - needs a server
            self._listener = threading.Thread(target=target, daemon=True)
            self._listener.start()

    def _listen_pg(self) -> None:  # pragma: no cover - needs Postgres
        import psycopg
        while True:
            try:
                with psycopg.connect(self.pg, autocommit=True) as conn:
                    conn.execute(f"LISTEN {CHANNEL}")
                    log.info("tracker bus listening on Postgres")
                    for n in conn.notifies():
                        body = json.loads(n.payload)
                        self._local(body["order"], body["event"])
            except Exception as e:  # noqa: BLE001
                log.warning("Postgres listener reconnecting: %s", e)
                time.sleep(2)

    def _relay_redis(self) -> None:  # pragma: no cover
        ps = self.redis.pubsub(ignore_subscribe_messages=True)
        ps.psubscribe("order:*")
        for msg in ps.listen():
            try:
                body = json.loads(msg["data"])
                if body.get("_from") != INSTANCE:
                    self._local(body["_order"], body["event"])
            except Exception as e:  # noqa: BLE001
                log.warning("relay skipped a message: %s", e)

    def publish(self, order_id: str, event_: dict) -> None:
        if self.redis:  # pragma: no cover
            try:
                self.redis.publish(f"order:{order_id}", json.dumps({"_from": INSTANCE, "_order": order_id, "event": event_}, default=str))
            except Exception as e:  # noqa: BLE001
                log.warning("redis publish failed: %s", e)
        self._local(order_id, event_)

    def _local(self, order_id: str, event_: dict) -> None:
        for q in list(self.subs.get(order_id, ())):
            if q.qsize() >= QUEUE_MAX:  # a stalled tracker never grows memory without bound
                continue
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(q.put_nowait, event_)
            else:
                q.put_nowait(event_)

    def subscribe(self, order_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subs[order_id].add(q)
        return q

    def unsubscribe(self, order_id: str, q: asyncio.Queue) -> None:
        self.subs[order_id].discard(q)


bus = Bus()


def after_commit(db: Session, order_id: str, event_: dict) -> None:
    """Announce an event once this session commits, and only then."""
    if bus.pg:  # NOTIFY is transactional: Postgres sends it at commit, to every instance
        db.execute(text("SELECT pg_notify(:c, :p)"), {"c": CHANNEL, "p": json.dumps({"order": order_id, "event": event_}, default=str)})
        return
    db.info.setdefault("pending_events", []).append((order_id, event_))


@event.listens_for(Session, "after_commit")
def _flush_events(db: Session) -> None:
    for order_id, ev in db.info.pop("pending_events", []):
        bus.publish(order_id, ev)


@event.listens_for(Session, "after_rollback")
def _drop_events(db: Session) -> None:
    db.info.pop("pending_events", None)
