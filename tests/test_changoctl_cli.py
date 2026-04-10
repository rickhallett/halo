"""Tests for changoctl CLI — subcommand dispatch and output."""

import json
from unittest.mock import patch

import pytest

from halos.changoctl.cli import main as cli_main


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestCLI:
    @staticmethod
    def _patch_db(tmp_db):
        return patch("halos.changoctl.store.DB_PATH", tmp_db)

    def test_help_returns_zero(self):
        ret = cli_main([])
        assert ret == 0

    def test_status(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["status"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out

    def test_status_json(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["--json", "status"])
        assert ret == 0
        data = json.loads(capsys.readouterr().out)
        assert "inventory" in data

    def test_restock(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["restock", "espresso", "--quantity", "5"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out
        assert "5" in out

    def test_restock_invalid_item(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main(["restock", "bourbon"])
        assert ret == 1

    def test_consume(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "nos", "--quantity", "2"])
            ret = cli_main(["consume", "nos", "--mood", "fire"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "*" in out

    def test_sustain(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "lagavulin", "--quantity", "3"])
            ret = cli_main(["sustain", "--mood", "burnt-out"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "*" in out
        assert "lagavulin" in out

    def test_quote_add(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            ret = cli_main([
                "quote", "add", "The margins are everything.",
                "--category", "philosophical",
            ])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Added quote #1" in out

    def test_quote_list(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main([
                "quote", "add", "Line one.", "--category", "sardonic",
            ])
            ret = cli_main(["quote", "list"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Line one." in out

    def test_quote_random(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main([
                "quote", "add", "Ship it.", "--category", "lethal",
            ])
            ret = cli_main(["quote", "random"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Ship it." in out

    def test_history(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "espresso", "--quantity", "1"])
            cli_main(["consume", "espresso", "--mood", "grind"])
            ret = cli_main(["history"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "espresso" in out

    def test_history_json(self, tmp_db, capsys):
        with self._patch_db(tmp_db):
            cli_main(["restock", "espresso", "--quantity", "1"])
            cli_main(["consume", "espresso"])
            capsys.readouterr()  # drain setup output before JSON assertion
            ret = cli_main(["--json", "history"])
        assert ret == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) == 1
