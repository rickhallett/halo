"""Study and work accountability tracker.

Domains registered:
  study-neetcode — DS & algorithms (neetcode.io)
  study-crafters — systems programming (codecrafters.io)
  study-source  — reading source code, language deep-dives, self-assessment
  project       — portfolio/project work (ThePit, Halo, client work, etc.)

Each targets daily consistency. Streak logic same as zazen.
"""

from halos.trackctl.registry import register

register(
    name="study-neetcode",
    description="DS & algorithms — neetcode.io (1hr/day target)",
    target=0,
)

register(
    name="study-crafters",
    description="Systems programming — codecrafters.io (1hr/day target)",
    target=0,
)

register(
    name="study-source",
    description="Source code reading, language deep-dives, self-assessment",
    target=0,
)

register(
    name="project",
    description="Portfolio and project work — ThePit, Halo, client builds, eBay ops",
    target=0,
)
