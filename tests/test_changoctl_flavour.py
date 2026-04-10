"""Tests for changoctl flavour — atmospheric action templates."""

from halos.changoctl.flavour import TEMPLATES, random_action
from halos.changoctl.config import VALID_ITEMS


class TestFlavour:
    def test_all_items_have_templates(self):
        for item in VALID_ITEMS:
            assert item in TEMPLATES, f"Missing templates for {item}"
            assert len(TEMPLATES[item]) >= 3, f"Need >= 3 templates for {item}"

    def test_templates_are_strings(self):
        for item, actions in TEMPLATES.items():
            for action in actions:
                assert isinstance(action, str)
                assert len(action) > 10

    def test_random_action_returns_string(self):
        action = random_action("espresso")
        assert isinstance(action, str)

    def test_random_action_formatted_with_asterisks(self):
        action = random_action("lagavulin")
        assert action.startswith("*")
        assert action.endswith("*")

    def test_random_action_invalid_item(self):
        import pytest
        with pytest.raises(KeyError):
            random_action("bourbon")
