"""Rubric YAML loader and weighted score computation."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Criterion:
    name: str
    weight: int
    description: str
    scale: tuple[int, int]


@dataclass
class Rubric:
    name: str
    version: int
    description: str
    criteria: list[Criterion]
    verdict_thresholds: dict[str, float]

    def compute_overall(self, scores: dict[str, int]) -> float:
        """Compute weighted average score from per-criterion scores.

        Args:
            scores: Dict mapping criterion name to integer score.

        Returns:
            Weighted average as float, rounded to 1 decimal.
        """
        total_weight = sum(c.weight for c in self.criteria)
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for c in self.criteria:
            score = scores.get(c.name, 0)
            # Clamp to scale
            score = max(c.scale[0], min(c.scale[1], score))
            weighted_sum += score * c.weight

        return round(weighted_sum / total_weight, 1)

    def score_to_verdict(self, overall: float) -> str:
        """Map an overall score to a verdict string."""
        # Sort thresholds descending
        for verdict, threshold in sorted(
            self.verdict_thresholds.items(), key=lambda x: x[1], reverse=True
        ):
            if overall >= threshold:
                return verdict
        return "SKIP"

    def criteria_prompt(self) -> str:
        """Format criteria for inclusion in LLM prompt."""
        lines = []
        for c in self.criteria:
            lines.append(
                f"- **{c.name}** (weight: {c.weight}, scale: {c.scale[0]}-{c.scale[1]}): "
                f"{c.description}"
            )
        return "\n".join(lines)


def load_rubric(path: Path) -> Rubric:
    """Load a rubric from a YAML file."""
    raw = yaml.safe_load(path.read_text())

    criteria = []
    for name, spec in raw.get("criteria", {}).items():
        criteria.append(Criterion(
            name=name,
            weight=spec.get("weight", 1),
            description=spec.get("description", ""),
            scale=tuple(spec.get("scale", [1, 5])),
        ))

    thresholds = raw.get("verdict_thresholds", {
        "REQUIRED": 4.0,
        "WATCH": 3.0,
        "SKIM": 2.0,
    })

    return Rubric(
        name=raw.get("name", "unnamed"),
        version=raw.get("version", 1),
        description=raw.get("description", ""),
        criteria=criteria,
        verdict_thresholds=thresholds,
    )
