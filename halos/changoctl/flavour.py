"""Atmospheric action templates for changoctl.

Hardcoded, deterministic, no LLM calls. Each item has 3-5 action strings
that get wrapped in asterisks and randomly selected at consumption time.
"""

import random


TEMPLATES: dict[str, list[str]] = {
    "espresso": [
        "Pulls a double shot from the machine",
        "Sips synthetic espresso and opens a terminal",
        "Fires up the espresso machine, watches the crema settle",
        "Knocks back a cortado without looking up from the logs",
        "Cradles a tiny cup of black gold, steam curling upward",
    ],
    "lagavulin": [
        "Pours a neat Lagavulin 16",
        "Swirls the glass and stares at the deploy logs",
        "Uncorks the Lagavulin, lets the peat fill the room",
        "Pours two fingers of Islay courage into a heavy glass",
        "Raises a glass of liquid smoke to the dying cluster",
    ],
    "stimpacks": [
        "Cracks a stimpack and rolls up the sleeves",
        "Jabs a stimpack into the forearm",
        "Cracks a stimpack and pulls up the terminal",
        "Slams a stimpack, pupils dilating to match the screen refresh rate",
    ],
    "nos": [
        "Cracks a NOS and watches the cluster burn",
        "Shotguns a NOS, wipes the screen clean",
        "Pops a NOS, the caffeine hitting like a kubectl rollout restart",
        "Crushes a NOS can and drops it in the recycling with extreme prejudice",
    ],
}


def random_action(item: str) -> str:
    """Return a random atmospheric action for the given item, wrapped in asterisks."""
    template = random.choice(TEMPLATES[item])
    return f"*{template}*"
