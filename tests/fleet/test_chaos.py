"""Tier 3: Chaos Engineering — Dodging Bullets.

A system isn't bulletproof until you shoot at it. These tests
deliberately destroy infrastructure and verify recovery.

Every test here is destructive. They kill pods, wipe state, and
stress concurrency. Run on-demand, not in CI.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid

import pytest

from .conftest import (
    EXPECTED_ADVISORS,
    FLEET_NS,
    INFRA_NS,
    _kubectl,
    _kubectl_exec,
    _kubectl_exec_python,
    _kubectl_json,
)

pytestmark = [pytest.mark.fleet, pytest.mark.tier3, pytest.mark.chaos, pytest.mark.slow]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PUBLISH_SCRIPT = """
import asyncio, os, json, time, uuid

async def publish():
    import nats
    nc = await nats.connect(
        os.environ['NATS_URL'],
        user=os.environ['NATS_USER'],
        password=os.environ['NATS_PASS'],
    )
    js = nc.jetstream()
    event = {{
        'id': '{event_id}',
        'type': '{event_type}',
        'version': 1,
        'source': 'chaos-test',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'correlation_id': '',
        'payload': {payload_json}
    }}
    ack = await js.publish('halo.{event_type}', json.dumps(event).encode())
    print(f'seq={{ack.seq}}')
    await nc.close()

asyncio.run(publish())
"""

CHECK_TRACK_SCRIPT = """
import sqlite3
db = sqlite3.connect('/opt/data/store/projection.db')
rows = db.execute(
    "SELECT * FROM track_entries WHERE source_event_id = ?",
    ('{event_id}',)
).fetchall()
print(len(rows))
db.close()
"""

CHECK_PROCESSED_SCRIPT = """
import sqlite3
db = sqlite3.connect('/opt/data/store/projection.db')
rows = db.execute(
    "SELECT COUNT(*) FROM _processed_events WHERE event_id = ?",
    ('{event_id}',)
).fetchone()
print(rows[0])
db.close()
"""

CONCURRENT_PUBLISH_SCRIPT = """
import asyncio, os, json, time

async def publish():
    import nats
    nc = await nats.connect(
        os.environ['NATS_URL'],
        user=os.environ['NATS_USER'],
        password=os.environ['NATS_PASS'],
    )
    js = nc.jetstream()

    results = []
    for i in range({count}):
        event_id = '{batch_id}-' + str(i)
        event = {{
            'id': event_id,
            'type': 'track.movement.logged',
            'version': 1,
            'source': '{source}',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'correlation_id': '',
            'payload': {{
                'domain': 'movement',
                'duration_mins': 1,
                'entry_id': abs(hash(event_id)) % 1_000_000_000,
                'notes': 'concurrent test'
            }}
        }}
        ack = await js.publish('halo.track.movement.logged', json.dumps(event).encode())
        results.append(ack.seq)

    print(f'published={{len(results)}}')
    await nc.close()

asyncio.run(publish())
"""


def _get_pod_name(label_prefix: str, namespace: str = FLEET_NS) -> str | None:
    """Get the name of a running pod by label prefix."""
    pods = _kubectl_json("get", "pods", namespace=namespace)
    for p in pods["items"]:
        name = p["metadata"]["name"]
        if name.startswith(label_prefix) and p["status"]["phase"] == "Running":
            ready = all(
                cs.get("ready", False)
                for cs in p["status"].get("containerStatuses", [])
            )
            if ready:
                return name
    return None


def _wait_for_pod(label_prefix: str, namespace: str = FLEET_NS, timeout: float = 90.0) -> str:
    """Wait for a pod matching the prefix to be Running and Ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        name = _get_pod_name(label_prefix, namespace)
        if name:
            return name
        time.sleep(2)
    raise TimeoutError(f"No ready pod matching '{label_prefix}' in {namespace} within {timeout}s")


def _kill_pod(name: str, namespace: str = FLEET_NS) -> None:
    """Force-delete a pod (no grace period)."""
    _kubectl("delete", "pod", name, "--grace-period=0", "--force", namespace=namespace)


def _publish_event(pod: str, event_id: str, event_type: str, payload: dict) -> int:
    script = PUBLISH_SCRIPT.format(
        event_id=event_id,
        event_type=event_type,
        payload_json=json.dumps(payload),
    )
    result = _kubectl_exec_python(pod, script)
    return int(result.strip().split("=")[1])


def _check_projected(pod: str, event_id: str) -> bool:
    script = CHECK_TRACK_SCRIPT.format(event_id=event_id)
    try:
        result = _kubectl_exec_python(pod, script)
        return int(result.strip()) > 0
    except RuntimeError:
        return False


def _check_processed(pod: str, event_id: str) -> bool:
    script = CHECK_PROCESSED_SCRIPT.format(event_id=event_id)
    try:
        result = _kubectl_exec_python(pod, script)
        return int(result.strip()) > 0
    except RuntimeError:
        return False


def _wait_for_event(pod: str, event_id: str, check_fn, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if check_fn(pod, event_id):
                return True
        except RuntimeError:
            pass
        time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNATSPodMurder:
    """Kill NATS mid-stream. Verify recovery and zero message loss.

    The Agent Smith Protocol: if NATS goes down, Kubernetes restarts it.
    JetStream persists messages on disk. Consumers reconnect and resume
    from their checkpoint. No messages lost.
    """

    def test_nats_recovers_after_kill(self):
        """Kill NATS → restarts → consumers reconnect → events still flow."""
        # 1. Get a source pod and publish a pre-kill event
        source_pod = _wait_for_pod("advisor-musashi-")
        pre_event_id = f"chaos-pre-nats-{uuid.uuid4().hex[:8]}"
        _publish_event(
            source_pod, pre_event_id, "track.movement.logged",
            {"domain": "movement", "duration_mins": 1,
             "entry_id": int(uuid.uuid4().int % 1_000_000_000),
             "notes": "pre-nats-kill"},
        )

        # Verify it arrived
        draper_pod = _wait_for_pod("advisor-draper-")
        assert _wait_for_event(draper_pod, pre_event_id, _check_projected, timeout=10.0), \
            "Pre-kill event didn't arrive"

        # 2. Kill NATS
        nats_pod = _get_pod_name("nats-")
        assert nats_pod, "NATS pod not found"
        _kill_pod(nats_pod)

        # 3. Wait for NATS to restart
        time.sleep(5)
        new_nats = _wait_for_pod("nats-", timeout=60)
        assert new_nats != nats_pod, "NATS pod didn't restart (same name)"

        # 4. Wait for consumers to reconnect (they retry automatically)
        time.sleep(15)

        # 5. Publish a post-kill event
        # Source pod might need time to reconnect too
        source_pod = _wait_for_pod("advisor-musashi-")
        post_event_id = f"chaos-post-nats-{uuid.uuid4().hex[:8]}"

        retries = 5
        published = False
        for attempt in range(retries):
            try:
                _publish_event(
                    source_pod, post_event_id, "track.movement.logged",
                    {"domain": "movement", "duration_mins": 1,
                     "entry_id": int(uuid.uuid4().int % 1_000_000_000),
                     "notes": "post-nats-kill"},
                )
                published = True
                break
            except RuntimeError:
                time.sleep(5)

        assert published, "Could not publish event after NATS restart"

        # 6. Verify post-kill event arrives at a different advisor
        draper_pod = _wait_for_pod("advisor-draper-")
        found = _wait_for_event(draper_pod, post_event_id, _check_projected, timeout=30.0)
        assert found, (
            f"Post-kill event {post_event_id} not projected — "
            "NATS recovery or consumer reconnect failed"
        )


class TestAdvisorPodMurder:
    """Kill an advisor pod mid-operation. Verify it restarts and catches up.

    The consumer checkpoint ensures no events are lost across restarts.
    Events published while the pod was dead are replayed from the
    JetStream on reconnect.
    """

    def test_advisor_restarts_and_replays(self):
        # 1. Identify the victim
        victim_name = "gibson"
        victim_pod = _wait_for_pod(f"advisor-{victim_name}-")

        # 2. Get the pre-kill projection count
        pre_count = _kubectl_exec_python(
            victim_pod,
            "import sqlite3\n"
            "db = sqlite3.connect('/opt/data/store/projection.db')\n"
            "print(db.execute('SELECT COUNT(*) FROM _processed_events').fetchone()[0])\n"
            "db.close()",
        )
        pre_count = int(pre_count.strip())

        # 3. Kill the victim
        _kill_pod(victim_pod)

        # 4. While it's dead, publish an event from another advisor
        source_pod = _wait_for_pod("advisor-musashi-")
        orphan_event_id = f"chaos-orphan-{uuid.uuid4().hex[:8]}"
        _publish_event(
            source_pod, orphan_event_id, "track.zazen.logged",
            {"domain": "zazen", "duration_mins": 10,
             "entry_id": int(uuid.uuid4().int % 1_000_000_000),
             "notes": "published while gibson was dead"},
        )

        # 5. Wait for the victim to restart
        new_pod = _wait_for_pod(f"advisor-{victim_name}-", timeout=90)
        assert new_pod != victim_pod, "Pod didn't restart"

        # 6. Wait for the orphan event to appear in the new pod's projection
        found = _wait_for_event(new_pod, orphan_event_id, _check_processed, timeout=30.0)
        assert found, (
            f"Event {orphan_event_id} published during pod death was NOT "
            f"replayed after restart — consumer checkpoint is broken"
        )


class TestNFSServerRestart:
    """Kill the NFS server. Verify memory reads resume after restart."""

    def test_nfs_recovers_after_kill(self):
        """Kill NFS → restarts → advisor pods restart → reads resume → corpus intact.

        NFS kernel client holds stale filehandles after server restart (new pod IP).
        Recovery requires advisor pods to restart so kubelet remounts the NFS volume.
        This tests the full recovery chain, not just the server.
        """
        # 1. Record which advisor pod we're testing
        advisor_pod = _wait_for_pod("advisor-musashi-")

        # 2. Kill the NFS server
        nfs_pod = _get_pod_name("nfs-server-", namespace=INFRA_NS)
        assert nfs_pod, "NFS server pod not found"
        _kill_pod(nfs_pod, namespace=INFRA_NS)

        # 3. Wait for NFS to restart
        time.sleep(5)
        new_nfs = _wait_for_pod("nfs-server-", namespace=INFRA_NS, timeout=60)
        assert new_nfs, "NFS server didn't restart"
        time.sleep(15)  # Let NFS exports stabilise

        # 4. Restart the advisor pod (stale NFS handles need fresh mount)
        # The new pod's kubelet NFS mount may block until the server is fully ready.
        _kill_pod(advisor_pod)
        new_advisor = _wait_for_pod("advisor-musashi-", timeout=120)
        assert new_advisor != advisor_pod, "Advisor didn't restart"

        # 5. Verify reads work on the fresh pod
        deadline = time.time() + 45
        recovered = False
        while time.time() < deadline:
            try:
                after = _kubectl_exec(new_advisor, "head -1 /memory/INDEX.md")
                if "MEMORY INDEX" in after:
                    recovered = True
                    break
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            time.sleep(2)

        assert recovered, "NFS reads did not resume after server + advisor restart"

        # 6. Verify corpus is intact (not corrupted)
        count = _kubectl_exec(new_advisor, "ls /memory/notes/*.md | wc -l")
        assert int(count.strip()) > 100, "Memory corpus corrupted after NFS restart"


class TestMemctlAuthorityRestart:
    """Kill the memctl-authority pod. Verify NFS corpus survives."""

    def test_authority_restarts_with_corpus_intact(self):
        # Ensure NFS is healthy first (may be recovering from a prior test)
        _wait_for_pod("nfs-server-", namespace=INFRA_NS, timeout=60)
        time.sleep(10)

        # 1. Get the authority pod
        authority_pod = _wait_for_pod("memctl-authority-")

        # 2. Write a canary file (use longer timeout — NFS may be slow after recovery)
        canary = f"chaos-canary-{uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            ["kubectl", "exec", authority_pod, "-n", FLEET_NS,
             "-c", "authority", "--", "bash", "-c",
             f'echo "{canary}" > /memory/test-authority-canary.md'],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Canary write failed: {result.stderr}"

        # 3. Kill the authority
        _kill_pod(authority_pod)

        # 4. Wait for restart
        new_authority = _wait_for_pod("memctl-authority-", timeout=90)
        assert new_authority != authority_pod, "Authority didn't restart"

        # 5. Verify canary survived (NFS PVC persists across restarts)
        content = _kubectl_exec(
            new_authority,
            "cat /memory/test-authority-canary.md",
            container="authority",
        )
        assert content.strip() == canary, (
            f"Canary lost after restart: expected '{canary}', got '{content.strip()}'"
        )

        # 6. Verify full corpus intact
        count = _kubectl_exec(
            new_authority,
            "ls /memory/notes/*.md | wc -l",
            container="authority",
        )
        assert int(count.strip()) > 100, "Memory corpus lost after authority restart"

        # 7. Cleanup
        _kubectl_exec(
            new_authority,
            "rm -f /memory/test-authority-canary.md",
            container="authority",
        )


class TestConcurrentNATSPublish:
    """Seven advisors publish simultaneously. No interleaving, no loss.

    Verifies NATS JetStream handles concurrent writes from multiple
    publishers without message loss or corruption.
    """

    def test_concurrent_publish_no_loss(self):
        batch_id = f"chaos-concurrent-{uuid.uuid4().hex[:8]}"
        events_per_advisor = 5

        # 1. Get all advisor pods
        pods = {}
        for name in EXPECTED_ADVISORS:
            pod = _get_pod_name(f"advisor-{name}-")
            if pod:
                pods[name] = pod

        assert len(pods) >= 5, f"Need at least 5 advisors, got {len(pods)}"

        # 2. Publish from all advisors concurrently
        # Each advisor publishes events_per_advisor events
        import threading

        errors = {}

        def publish_from(advisor_name: str, pod_name: str):
            try:
                script = CONCURRENT_PUBLISH_SCRIPT.format(
                    count=events_per_advisor,
                    batch_id=f"{batch_id}-{advisor_name}",
                    source=advisor_name,
                )
                result = _kubectl_exec_python(pod_name, script)
                if f"published={events_per_advisor}" not in result:
                    errors[advisor_name] = f"unexpected output: {result}"
            except RuntimeError as e:
                errors[advisor_name] = str(e)

        threads = []
        for name, pod in pods.items():
            t = threading.Thread(target=publish_from, args=(name, pod))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=60)

        assert not errors, f"Publish errors: {errors}"

        # 3. Wait for events to propagate
        time.sleep(10)

        # 4. Verify ALL events arrived at a single advisor's projection
        check_pod = list(pods.values())[0]
        total_expected = events_per_advisor * len(pods)

        count_script = f"""
import sqlite3
db = sqlite3.connect('/opt/data/store/projection.db')
count = db.execute(
    "SELECT COUNT(*) FROM _processed_events WHERE event_id LIKE '{batch_id}-%'"
).fetchone()[0]
print(count)
db.close()
"""
        result = _kubectl_exec_python(check_pod, count_script)
        actual = int(result.strip())

        assert actual == total_expected, (
            f"Message loss detected: expected {total_expected} events, "
            f"got {actual} ({total_expected - actual} lost)"
        )
