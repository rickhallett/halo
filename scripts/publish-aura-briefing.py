#!/usr/bin/env python3
"""Publish Aura Client 001 status briefing to the Halostream.

Fires client.briefing.published events — projected into every advisor's
briefing_notes table for roundtable-wide awareness.

Usage:
    NATS_PASS=xxx uv run python scripts/publish-aura-briefing.py

Requires NATS_PASS in environment (cluster access).
"""

from halos.eventsource.publish import fire_event

BRIEFINGS = [
    {
        "client_slug": "aura",
        "title": "Client 001 (Aura) — Pilot Terminated",
        "classification": "roundtable",
        "body": (
            "Aura has formally disengaged from the Halo pilot as of 2026-04-11. "
            "She confirmed she is going her own way: less AI, more human, organic patterns. "
            "Zoom Pro gives her auto-transcription at $20/mo; she will build her own corpus "
            "slowly. She acknowledged the process helped her realise she needs less AI, not more. "
            "Pilot fee was split: £100 retained for the strategic clarity delivered, £100 refunded. "
            "No further energy will be spent on this account. Aura is a closed client."
        ),
    },
    {
        "client_slug": "aura",
        "title": "SoundsRight — Reusable IP, Ready for Client 002",
        "classification": "roundtable",
        "body": (
            "The SoundsRight voice-fidelity pipeline (github.com/rickhallett/soundsright) "
            "was built during the Aura engagement but is fully client-agnostic and multi-tenant. "
            "Architecture: FastAPI + Celery + Postgres/pgvector + Redis. Corpus ingestion, "
            "LLM-driven style analysis, dynamic rubric derivation, pgvector-powered generation, "
            "LLM-as-judge + human scoring, preference pair feedback loop. 25 tests passing. "
            "This is reusable IP for the next client who needs voice-faithful content generation. "
            "Do not associate it with Aura going forward."
        ),
    },
    {
        "client_slug": "aura",
        "title": "halo-aura Namespace — Decommission When Convenient",
        "classification": "roundtable",
        "body": (
            "The halo-aura K8s namespace on Ryzen k3s is still running (Dao Assistant gateway pod). "
            "It can be torn down at convenience — no active user, no SLA. Low priority cleanup. "
            "If any advisor is asked about Aura: pilot concluded, learnings captured, moved on. "
            "Do not suggest re-engagement or reference her as an active client."
        ),
    },
]


def main():
    published = 0
    for b in BRIEFINGS:
        ok = fire_event(
            "client.briefing.published",
            payload=b,
            source="chango",
        )
        status = "ok" if ok else "SKIPPED (no NATS_PASS)"
        print(f"  [{status}] {b['title']}")
        if ok:
            published += 1

    print(f"\n{published}/{len(BRIEFINGS)} briefings published to Halostream.")
    if published == 0:
        print("Set NATS_PASS to publish. Events will be consumed on next advisor restart.")


if __name__ == "__main__":
    main()
