#!/usr/bin/env python3
"""CLI for publishing events to the Halostream via NATS.

Connects to NATS inside a fleet pod over SSH + kubectl exec.
Local NATS is cluster-internal only — this is the external publish path.

Usage:
    halo-emit <event_type> [--source SOURCE] [key=value ...]

Examples:
    halo-emit draper.observation.correction subject="drift pattern" severity=high
    halo-emit track.zazen.logged domain=zazen duration_mins=30
    halo-emit system.note message="deployment complete" --source hightower

Requires: SSH access to ryzen32, running NATS pod in halo-fleet namespace.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys


RYZEN_HOST = "ryzen32"
NAMESPACE = "halo-fleet"
NATS_SECRET = "nats-auth"
NATS_SECRET_KEY = "ADVISOR_PASS"


def _pick_pod(ns: str) -> str | None:
    """Find a running advisor pod to exec into."""
    result = subprocess.run(
        [
            "ssh", "-o", "ConnectTimeout=8", RYZEN_HOST,
            f"sudo kubectl get pods -n {ns} --no-headers "
            f"-l app.kubernetes.io/component=advisor "
            f"-o jsonpath='{{.items[0].metadata.name}}'"
        ],
        capture_output=True, text=True, timeout=15,
    )
    pod = result.stdout.strip().strip("'")
    if pod and result.returncode == 0:
        return pod

    # Fallback: grab first advisor pod by name
    result = subprocess.run(
        [
            "ssh", "-o", "ConnectTimeout=8", RYZEN_HOST,
            f"sudo kubectl get pods -n {ns} --no-headers"
        ],
        capture_output=True, text=True, timeout=15,
    )
    for line in result.stdout.splitlines():
        parts = line.split()
        if parts and parts[0].startswith("advisor-") and "Running" in line:
            return parts[0]
    return None


def _publish(pod: str, event_type: str, source: str, payload: dict) -> tuple[bool, str]:
    """Publish event via kubectl exec into a fleet pod."""
    payload_json = json.dumps(payload)
    python_code = f"""
import asyncio, json, os
async def pub():
    import nats as nc
    conn = await nc.connect(
        'nats://nats.halo-fleet.svc.cluster.local:4222',
        user='advisor',
        password=os.environ.get('NATS_PASS', ''),
    )
    js = conn.jetstream()
    from halos.eventsource.core import Event
    e = Event.create(
        type={event_type!r},
        source={source!r},
        payload=json.loads({payload_json!r}),
    )
    ack = await js.publish(
        f'halo.{{e.type}}',
        e.to_json().encode(),
        headers={{'Nats-Msg-Id': e.id}},
    )
    print(f'stream={{ack.stream}} seq={{ack.seq}}')
    await conn.close()
asyncio.run(pub())
"""
    result = subprocess.run(
        [
            "ssh", "-o", "ConnectTimeout=8", RYZEN_HOST,
            f"sudo kubectl exec -n {NAMESPACE} {pod} -- python3 -c {shlex.quote(python_code)}"
        ],
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout.strip()
    if result.returncode == 0 and "seq=" in output:
        return True, output
    return False, result.stderr.strip() or output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish events to the Halostream (NATS via fleet pod)",
        epilog="Payload fields as key=value pairs. Values are auto-parsed as JSON if possible.",
    )
    parser.add_argument("event_type", help="Event type (e.g. draper.interview.feedback)")
    parser.add_argument("--source", default="local", help="Event source (default: local)")
    parser.add_argument("--pod", default=None, help="Target pod name (auto-detected if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Print event without publishing")
    parser.add_argument("fields", nargs="*", help="Payload fields as key=value pairs")

    args = parser.parse_args()

    # Parse payload from key=value pairs
    payload: dict = {}
    for field in args.fields:
        if "=" not in field:
            print(f"error: field must be key=value, got: {field}", file=sys.stderr)
            return 1
        key, _, value = field.partition("=")
        # Try JSON parse for structured values (arrays, objects, numbers, bools)
        try:
            payload[key] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            payload[key] = value

    if args.dry_run:
        print(f"type:    {args.event_type}")
        print(f"source:  {args.source}")
        print(f"payload: {json.dumps(payload, indent=2)}")
        return 0

    # Find a pod
    pod = args.pod
    if not pod:
        print("finding fleet pod...", end=" ", flush=True)
        pod = _pick_pod(NAMESPACE)
        if not pod:
            print("FAILED", file=sys.stderr)
            print("error: no running advisor pod found in halo-fleet", file=sys.stderr)
            return 1
        print(pod)

    # Publish
    ok, output = _publish(pod, args.event_type, args.source, payload)
    if ok:
        print(f"published: {output}")
        return 0
    else:
        print(f"error: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
