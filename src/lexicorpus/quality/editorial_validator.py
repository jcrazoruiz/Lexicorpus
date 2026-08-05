from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from lexicorpus.quality.anomaly_detector import (
    AnomalyReport,
)


@dataclass(slots=True)
class EditorialValidationResult:
    status: str
    score: int
    approved: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EditorialValidator:
    def __init__(
        self,
        thresholds: dict[str, Any],
        scoring: dict[str, Any],
        rules: dict[str, Any] | None = None,
    ) -> None:
        self.thresholds = thresholds
        self.rules = rules or {}

        self.initial_score = int(
            scoring.get("initial_score", 100)
        )

        self.penalties = dict(
            scoring.get("penalties", {})
        )

        penalty_overrides = self.rules.get(
            "penalty_overrides",
            {},
        )

        self.penalties.update(
            penalty_overrides
        )

        self.accepted_score = int(
            scoring.get("accepted_score", 90)
        )

        self.accepted_with_warnings_score = int(
            scoring.get(
                "accepted_with_warnings_score",
                80,
            )
        )

        self.manual_review_score = int(
            scoring.get(
                "manual_review_score",
                65,
            )
        )

    def validate(
        self,
        report: AnomalyReport,
    ) -> EditorialValidationResult:
        score = self.initial_score

        errors: list[str] = []
        warnings: list[str] = []
        observations: list[str] = []

        minimum_words = int(
            self.thresholds.get(
                "minimum_words",
                1000,
            )
        )

        minimum_characters = int(
            self.thresholds.get(
                "minimum_characters",
                5000,
            )
        )

        if report.word_count < minimum_words:
            errors.append(
                f"El documento tiene "
                f"{report.word_count} palabras; "
                f"se requieren al menos "
                f"{minimum_words}."
            )

        if (
            report.character_count
            < minimum_characters
        ):
            errors.append(
                f"El documento tiene "
                f"{report.character_count} caracteres; "
                f"se requieren al menos "
                f"{minimum_characters}."
            )

        for anomaly in report.anomalies:
            penalty = int(
                self.penalties.get(
                    anomaly.code,
                    0,
                )
            )

            score -= penalty

            formatted_message = (
                f"{anomaly.code}: "
                f"{anomaly.message}"
            )

            severity = anomaly.severity.upper()

            if severity == "ERROR":
                errors.append(formatted_message)
            elif severity == "WARNING":
                warnings.append(formatted_message)
            else:
                observations.append(
                    formatted_message
                )

        score = max(0, min(100, score))

        if errors:
            status = "REJECTED"
            approved = False

        elif score >= self.accepted_score:
            if warnings:
                status = "APPROVED_WITH_WARNINGS"
            else:
                status = "APPROVED"

            approved = True

        elif (
            score
            >= self.accepted_with_warnings_score
        ):
            status = "APPROVED_WITH_WARNINGS"
            approved = True

        elif score >= self.manual_review_score:
            status = "MANUAL_REVIEW"
            approved = False

        else:
            status = "REJECTED"
            approved = False

        return EditorialValidationResult(
            status=status,
            score=score,
            approved=approved,
            errors=errors,
            warnings=warnings,
            observations=observations,
        )