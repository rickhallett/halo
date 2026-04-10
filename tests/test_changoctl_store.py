"""Tests for changoctl SQLite store."""

import pytest

from halos.changoctl.store import (
    get_inventory,
    restock,
    consume,
    _connect,
)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestInventory:
    def test_seed_on_connect(self, tmp_db):
        """First connect seeds all four items at stock 0."""
        conn = _connect(tmp_db)
        rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
        conn.close()
        items = [dict(r)["item"] for r in rows]
        assert items == ["espresso", "lagavulin", "nos", "stimpacks"]
        for r in rows:
            assert dict(r)["stock"] == 0

    def test_get_inventory(self, tmp_db):
        inv = get_inventory(db_path=tmp_db)
        assert len(inv) == 4
        assert all(i["stock"] == 0 for i in inv)

    def test_restock_default(self, tmp_db):
        result = restock("espresso", db_path=tmp_db)
        assert result["stock"] == 1
        assert result["item"] == "espresso"

    def test_restock_quantity(self, tmp_db):
        result = restock("lagavulin", quantity=6, db_path=tmp_db)
        assert result["stock"] == 6

    def test_restock_accumulates(self, tmp_db):
        restock("nos", quantity=3, db_path=tmp_db)
        result = restock("nos", quantity=2, db_path=tmp_db)
        assert result["stock"] == 5

    def test_restock_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            restock("bourbon", db_path=tmp_db)

    def test_consume_decrements(self, tmp_db):
        restock("stimpacks", quantity=3, db_path=tmp_db)
        result = consume("stimpacks", mood="locked-in", db_path=tmp_db)
        assert result["stock"] == 2
        assert result["log_entry"]["item"] == "stimpacks"
        assert result["log_entry"]["mood"] == "locked-in"
        assert result["log_entry"]["quantity"] == 1

    def test_consume_out_of_stock(self, tmp_db):
        """Out of stock: logs at quantity 0, stock stays 0."""
        result = consume("espresso", mood="grind", db_path=tmp_db)
        assert result["stock"] == 0
        assert result["log_entry"]["quantity"] == 0
        assert result["out_of_stock"] is True

    def test_consume_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            consume("bourbon", db_path=tmp_db)
