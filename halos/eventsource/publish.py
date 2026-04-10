"""Synchronous NATS event publisher for CLI tools.

Fire-and-forget: connects, publishes, disconnects. Never raises —
CLI tools must not block or fail on event publishing errors.

Usage:
    from halos.eventsource.publish import fire_event
    fire_event("track.zazen.logged", {"domain": "zazen", ...})
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .core import Event


def fire_event(
    event_type: str,
    payload: dict[str, Any],
    source: str | None = None,
) -> bool:
    """Publish a single event to NATS. Returns True on success.

    Requires NATS_PASS in the environment. If missing, returns False
    immediately (local dev without NATS access).

    Safe to call from both sync and async contexts (e.g. Hermes tools).
    """
    nats_pass = os.environ.get("NATS_PASS")
    if not nats_pass:
        return False

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    try:
        if loop is None:
            return asyncio.run(_async_publish(event_type, payload, source))
        else:
            # Inside an existing event loop (e.g. Hermes gateway) —
            # run in a thread to avoid asyncio.run() nesting error.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _async_publish(event_type, payload, source))
                return future.result(timeout=10)
    except Exception:
        return False


async def _async_publish(
    event_type: str,
    payload: dict[str, Any],
    source: str | None,
) -> bool:
    import nats as nats_client

    nats_url = os.environ.get(
        "NATS_URL", "nats://nats.halo-fleet.svc.cluster.local:4222"
    )
    nats_user = os.environ.get("NATS_USER", "advisor")
    nats_pass = os.environ.get("NATS_PASS", "")
    src = source or os.environ.get("ADVISOR_NAME", "local")

    event = Event.create(type=event_type, source=src, payload=payload)
    subject = f"halo.{event.type}"

    nc = await nats_client.connect(
        nats_url, user=nats_user, password=nats_pass
    )
    try:
        js = nc.jetstream()
        await js.publish(
            subject,
            event.to_json().encode(),
            headers={"Nats-Msg-Id": event.id},
        )
        return True
    finally:
        await nc.close()
