"""Tests for changoctl graph adapter — Neo4j dual-write and sync.

All tests mock the neo4j driver. No real Neo4j required.
"""

import pytest
from unittest.mock import patch, MagicMock

from halos.changoctl.graph import is_available, push_consumption, push_quote, push_restock


class TestGraphAvailability:
    def test_available_when_driver_connects(self):
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            assert is_available() is True

    def test_unavailable_when_no_neo4j(self):
        with patch("halos.changoctl.graph._neo4j", None):
            assert is_available() is False

    def test_unavailable_when_connection_fails(self):
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("refused")
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            assert is_available() is False


class TestPushOperations:
    def test_push_consumption_succeeds(self):
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            push_consumption("espresso", "grind", "sess-1", "2026-04-10T00:00:00Z")
        mock_session.run.assert_called()

    def test_push_consumption_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            push_consumption("espresso", "grind", "sess-1", "2026-04-10T00:00:00Z")

    def test_push_quote_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            push_quote("Test line.", "sardonic", 1)

    def test_push_restock_degrades_silently(self):
        with patch("halos.changoctl.graph._get_driver", side_effect=Exception("down")):
            push_restock("lagavulin", 5)


class TestSync:
    def test_sync_all_with_data(self, tmp_path):
        from halos.changoctl.store import restock, consume, add_quote
        from halos.changoctl.graph import sync_all

        tmp_db = tmp_path / "test.db"
        restock("espresso", quantity=2, db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        add_quote("Test.", category="sardonic", db_path=tmp_db)

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("halos.changoctl.graph._get_driver", return_value=mock_driver):
            result = sync_all(db_path=tmp_db)

        assert result["consumption_count"] == 1
        assert result["quote_count"] == 1
        assert mock_session.run.call_count > 0

    def test_sync_all_no_neo4j(self, tmp_path):
        from halos.changoctl.graph import sync_all

        with patch("halos.changoctl.graph._neo4j", None):
            with pytest.raises(ImportError, match="neo4j"):
                sync_all(db_path=tmp_path / "test.db")
