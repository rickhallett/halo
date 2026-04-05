"""Integration tests for AdvisorEventLoop with a real NATS JetStream container.

These tests are marked slow and auto-skip when Docker is unavailable.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

import pytest

nats = pytest.importorskip("nats")

from halos.eventsource.consumer import AdvisorEventLoop
from halos.eventsource.core import Event, ProjectionHandler


pytestmark = pytest.mark.slow


def _docker_available() -> bool:
    if not shutil_which("docker"):
        return False
    proc = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextlib.contextmanager
def nats_container() -> str:
    """Run a disposable NATS JetStream container and yield its URL."""
    if not _docker_available():
        pytest.skip("Docker unavailable; skipping NATS integration test")

    port = _free_port()
    name = f"halo-test-nats-{uuid.uuid4().hex[:8]}"

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            f"127.0.0.1:{port}:4222",
            "nats:2.10-alpine",
            "--jetstream",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        yield f"nats://127.0.0.1:{port}"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


async def _wait_for_nats(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            nc = await nats.connect(url)
            await nc.close()
            return
        except Exception as e:  # pragma: no cover - startup retry loop
            last_error = e
            await asyncio.sleep(0.2)

    raise RuntimeError(f"NATS did not start in time: {last_error}")


class CounterHandler(ProjectionHandler):
    tables = ["counter"]

    def handles(self) -> list[str]:
        return ["test.counted"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS counter (
                event_id TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT OR IGNORE INTO counter (event_id, value) VALUES (?, ?)",
            (event.id, event.payload["value"]),
        )


async def _publish_event(js, event: Event) -> None:
    await js.publish(
        f"halo.{event.type}",
        event.to_json().encode(),
        headers={"Nats-Msg-Id": event.id},
    )


async def _await_condition(fn, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            if fn():
                return
        except RuntimeError as e:
            # Typical during startup if projection DB isn't open yet.
            last_error = e
        await asyncio.sleep(0.1)
    if last_error:
        raise TimeoutError(f"Condition not met before timeout: {last_error}")
    raise TimeoutError("Condition not met before timeout")


@pytest.mark.anyio
async def test_consumer_replays_from_start_when_projection_is_empty(tmp_path: Path):
    """If local checkpoint is empty, consumer should rebuild from stream start.

    This exercises the disposable pod contract: losing local projection must
    not lose historical events just because a durable consumer exists.
    """
    with nats_container() as nats_url:
        await _wait_for_nats(nats_url)
        nc = await nats.connect(nats_url)
        js = nc.jetstream()
        await js.add_stream(name="HALO", subjects=["halo.>"])

        # Publish initial history.
        e1 = Event.create("test.counted", "test", {"value": 1})
        e2 = Event.create("test.counted", "test", {"value": 2})
        await _publish_event(js, e1)
        await _publish_event(js, e2)

        db_path = tmp_path / "projection.db"

        # First run processes history and creates durable consumer state.
        loop1 = AdvisorEventLoop(
            advisor_name="musashi",
            nats_url=nats_url,
            nats_user=None,
            nats_pass=None,
            projection_path=db_path,
            handlers=[CounterHandler()],
            subscriptions=["halo.test.>"],
        )
        task1 = asyncio.create_task(loop1.start())
        await _await_condition(
            lambda: loop1.projection.db.execute("SELECT COUNT(*) AS c FROM counter").fetchone()["c"] == 2
        )
        await loop1.stop()
        task1.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task1

        # New event arrives while pod is down.
        e3 = Event.create("test.counted", "test", {"value": 3})
        await _publish_event(js, e3)

        # Simulate disposable storage loss (emptyDir restart): wipe projection DB.
        if db_path.exists():
            db_path.unlink()

        # Second run with same durable name must replay whole stream from start.
        loop2 = AdvisorEventLoop(
            advisor_name="musashi",
            nats_url=nats_url,
            nats_user=None,
            nats_pass=None,
            projection_path=db_path,
            handlers=[CounterHandler()],
            subscriptions=["halo.test.>"],
        )
        task2 = asyncio.create_task(loop2.start())

        await _await_condition(
            lambda: loop2.projection.db.execute("SELECT COUNT(*) AS c FROM counter").fetchone()["c"] == 3
        )

        values = [
            row["value"]
            for row in loop2.projection.db.execute("SELECT value FROM counter ORDER BY value").fetchall()
        ]
        assert values == [1, 2, 3]

        await loop2.stop()
        task2.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task2
        await nc.close()


@pytest.mark.anyio
async def test_consumer_applies_subject_filters(tmp_path: Path):
    """Consumer should only process subscribed subjects, not halo.> by default."""
    with nats_container() as nats_url:
        await _wait_for_nats(nats_url)
        nc = await nats.connect(nats_url)
        js = nc.jetstream()
        await js.add_stream(name="HALO", subjects=["halo.>"])

        # Publish included event first, excluded event second.
        # If consumer incorrectly subscribes to halo.>, checkpoint will advance to seq 2.
        included = Event.create("test.counted", "test", {"value": 7})
        excluded = Event.create("other.ignored", "test", {"value": 999})
        await _publish_event(js, included)
        await _publish_event(js, excluded)

        db_path = tmp_path / "projection-filters.db"
        loop = AdvisorEventLoop(
            advisor_name="seneca",
            nats_url=nats_url,
            nats_user=None,
            nats_pass=None,
            projection_path=db_path,
            handlers=[CounterHandler()],
            subscriptions=["halo.test.>"],
        )
        task = asyncio.create_task(loop.start())

        await _await_condition(
            lambda: loop.projection.db.execute("SELECT COUNT(*) AS c FROM counter").fetchone()["c"] == 1
        )

        checkpoint = loop.projection.last_checkpoint("seneca")
        # Included event is first in stream, excluded is second.
        assert checkpoint == 1

        await loop.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await nc.close()
