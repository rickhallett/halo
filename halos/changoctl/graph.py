"""Neo4j graph adapter for changoctl — dual-write to Beachhead.

Fire-and-forget: all push operations swallow exceptions silently.
If neo4j is not installed, the module degrades gracefully.
sync_all is the recovery path — idempotent replay from SQLite.
"""

from pathlib import Path
from typing import Optional

from halos.common.log import hlog

try:
    import neo4j as _neo4j
except ImportError:
    _neo4j = None

_driver_cache = None


def _get_driver():
    """Lazy-init and cache the neo4j driver."""
    global _driver_cache
    if _neo4j is None:
        raise ImportError("neo4j package not installed")
    if _driver_cache is None:
        from .config import BEACHHEAD_URI, BEACHHEAD_USER, BEACHHEAD_PASS
        _driver_cache = _neo4j.GraphDatabase.driver(
            BEACHHEAD_URI, auth=(BEACHHEAD_USER, BEACHHEAD_PASS)
        )
    return _driver_cache


def is_available() -> bool:
    """Check if Beachhead is reachable."""
    try:
        driver = _get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def push_consumption(item: str, mood: str, session_id: str, timestamp: str) -> None:
    """Project a consumption event into the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (i:Item {name: $item})
                MERGE (m:Mood {name: $mood})
                MERGE (s:Session {id: $session_id})
                SET s.timestamp = $timestamp
                MERGE (i)-[:CONSUMED_DURING {timestamp: $timestamp}]->(s)
                MERGE (s)-[:MOOD_WAS]->(m)
                MERGE (i)-[:PAIRS_WITH]->(m)
            """, item=item, mood=mood, session_id=session_id, timestamp=timestamp)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "consumption", "error": str(e),
        })


def push_quote(text: str, category: str, quote_id: int) -> None:
    """Project a quote into the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (q:Quote {id: $quote_id})
                SET q.text = $text, q.category = $category
                MERGE (m:Mood {name: $category})
                MERGE (q)-[:TAGGED]->(m)
            """, text=text, category=category, quote_id=quote_id)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "quote", "error": str(e),
        })


def push_restock(item: str, new_stock: int) -> None:
    """Update item stock in the graph."""
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("""
                MERGE (i:Item {name: $item})
                SET i.stock = $new_stock
            """, item=item, new_stock=new_stock)
    except Exception as e:
        hlog("changoctl", "warning", "graph_push_failed", {
            "operation": "restock", "error": str(e),
        })


def sync_all(db_path: Optional[Path] = None) -> dict:
    """Full idempotent replay from SQLite into Beachhead.

    Raises ImportError if neo4j is not installed.
    Raises Exception if Beachhead is unreachable.
    """
    from . import store

    try:
        driver = _get_driver()
    except ImportError:
        raise ImportError("neo4j package not installed")
    consumption_logs = store.list_consumption_history(db_path=db_path)
    quotes = store.list_quotes(db_path=db_path)
    inventory = store.get_inventory(db_path=db_path)

    with driver.session() as session:
        # Sync inventory
        for item in inventory:
            session.run("""
                MERGE (i:Item {name: $name})
                SET i.stock = $stock
            """, name=item["item"], stock=item["stock"])

        # Sync consumption logs
        for log in consumption_logs:
            session.run("""
                MERGE (i:Item {name: $item})
                MERGE (s:Session {id: $session_id})
                SET s.timestamp = $timestamp
                MERGE (i)-[:CONSUMED_DURING {timestamp: $timestamp}]->(s)
            """, item=log["item"],
                session_id=str(log["id"]),
                timestamp=log["timestamp"])

            if log.get("mood"):
                session.run("""
                    MERGE (m:Mood {name: $mood})
                    MERGE (s:Session {id: $session_id})
                    MERGE (s)-[:MOOD_WAS]->(m)
                    MERGE (i:Item {name: $item})
                    MERGE (i)-[:PAIRS_WITH]->(m)
                """, mood=log["mood"],
                    session_id=str(log["id"]),
                    item=log["item"])

        # Sync quotes
        for q in quotes:
            session.run("""
                MERGE (quote:Quote {id: $id})
                SET quote.text = $text, quote.category = $category
                MERGE (m:Mood {name: $category})
                MERGE (quote)-[:TAGGED]->(m)
            """, id=q["id"], text=q["text"], category=q["category"])

    hlog("changoctl", "info", "sync_complete", {
        "consumption_count": len(consumption_logs),
        "quote_count": len(quotes),
    })

    return {
        "consumption_count": len(consumption_logs),
        "quote_count": len(quotes),
        "inventory_count": len(inventory),
    }
