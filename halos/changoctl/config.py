"""changoctl configuration and path resolution."""

import os
from halos.common.paths import store_dir

DB_PATH = store_dir() / "changoctl.db"

BEACHHEAD_URI = os.environ.get("BEACHHEAD_URI", "bolt://localhost:7687")
BEACHHEAD_USER = os.environ.get("BEACHHEAD_USER", "neo4j")
BEACHHEAD_PASS = os.environ.get("BEACHHEAD_PASS", "neo4j")

VALID_ITEMS = ("espresso", "lagavulin", "stimpacks", "nos")
VALID_MOODS = ("grind", "locked-in", "burnt-out", "fire")
VALID_CATEGORIES = ("sardonic", "strategic", "lethal", "philosophical")

MOOD_ITEM_MAP = {
    "grind": "espresso",
    "locked-in": "stimpacks",
    "burnt-out": "lagavulin",
    "fire": "nos",
}

MOOD_CATEGORY_MAP = {
    "grind": "strategic",
    "locked-in": "lethal",
    "burnt-out": "philosophical",
    "fire": "sardonic",
}
