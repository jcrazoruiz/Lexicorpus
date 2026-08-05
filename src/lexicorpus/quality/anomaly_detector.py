from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any


CONTROL_CHARACTER_PATTERN = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
)

PAGE_MARKER_PATTERN = re.compile(
    r"\[\[PÁGINA\s+\d+\]\]",
    flags=re.IGNORECASE,
)

HYPHENATED_LINE_BREAK_PATTERN = re.compile(
    r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+-\n"
)

WORD_PATTERN = re.compile(
    r"[^\W\d_]+(?:['’\-][^\W\d_]+)*",
    flags=re.UNICODE,
)

SYMBOL_PATTERN = re.compile(
    r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ.,;:¿?¡!()«»“”\"'’—–\-]"
)


@dataclass(slots=True)
class Anomaly:
    code: str
    severity: str
    message: str
    count: int = 0
    ratio: float | None = None
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnomalyReport:
    character_count: int
    word_count: int
    line_count: int
    non_empty_line_count: int

    replacement_character_count: int
    null_character_count: int
    control_character_count: int
    page_marker_count: int
    hyphenated_line_break_count: int

    symbol_ratio: float
    numeric_line_ratio: float
    repeated_line_ratio: float
    uppercase_line_ratio: float
    short_line_ratio: float
    long_line_count: int

    anomalies: list[Anomaly] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["anomalies"] = [
            anomaly.to_dict()
            for anomaly in self.anomalies
        ]
        return data


class AnomalyDetector:
    def __init__(
        self,
        thresholds: dict[str, Any],
        rules: dict[str, Any] | None = None,
    ) -> None:
        self.thresholds = thresholds
        self.rules = rules or {}

        self.disabled_anomalies = set(
            self.rules.get(
                "disabled_anomalies",
                [],
            )
        )

        self.severity_overrides = (
            self.rules.get(
                "severity_overrides",
                {},
            )
        )

    def analyze(self, text: str) -> AnomalyReport:
        lines = text.splitlines()

        non_empty_lines = [
            line.strip()
            for line in lines
            if line.strip()
        ]

        character_count = len(text)
        word_count = len(WORD_PATTERN.findall(text))

        replacement_character_count = text.count("\ufffd")
        null_character_count = text.count("\x00")

        control_characters = CONTROL_CHARACTER_PATTERN.findall(text)
        control_character_count = len(control_characters)

        page_marker_count = len(
            PAGE_MARKER_PATTERN.findall(text)
        )

        hyphenated_line_break_count = len(
            HYPHENATED_LINE_BREAK_PATTERN.findall(text)
        )

        symbol_count = len(SYMBOL_PATTERN.findall(text))
        symbol_ratio = self._safe_ratio(
            symbol_count,
            character_count,
        )

        numeric_lines = [
            line
            for line in non_empty_lines
            if self._is_numeric_line(line)
        ]

        numeric_line_ratio = self._safe_ratio(
            len(numeric_lines),
            len(non_empty_lines),
        )

        repeated_lines = self._find_repeated_lines(
            non_empty_lines
        )

        repeated_line_occurrences = sum(
            count
            for _, count in repeated_lines
        )

        repeated_line_ratio = self._safe_ratio(
            repeated_line_occurrences,
            len(non_empty_lines),
        )

        uppercase_lines = [
            line
            for line in non_empty_lines
            if self._is_uppercase_line(line)
        ]

        uppercase_line_ratio = self._safe_ratio(
            len(uppercase_lines),
            len(non_empty_lines),
        )

        short_lines = [
            line
            for line in non_empty_lines
            if 0 < len(line) <= 25
        ]

        short_line_ratio = self._safe_ratio(
            len(short_lines),
            len(non_empty_lines),
        )

        maximum_long_line_length = int(
            self.thresholds.get(
                "warning_long_line_length",
                400,
            )
        )

        long_lines = [
            line
            for line in non_empty_lines
            if len(line) > maximum_long_line_length
        ]

        report = AnomalyReport(
            character_count=character_count,
            word_count=word_count,
            line_count=len(lines),
            non_empty_line_count=len(non_empty_lines),
            replacement_character_count=(
                replacement_character_count
            ),
            null_character_count=null_character_count,
            control_character_count=control_character_count,
            page_marker_count=page_marker_count,
            hyphenated_line_break_count=(
                hyphenated_line_break_count
            ),
            symbol_ratio=symbol_ratio,
            numeric_line_ratio=numeric_line_ratio,
            repeated_line_ratio=repeated_line_ratio,
            uppercase_line_ratio=uppercase_line_ratio,
            short_line_ratio=short_line_ratio,
            long_line_count=len(long_lines),
        )

        self._build_anomalies(
            report=report,
            numeric_lines=numeric_lines,
            repeated_lines=repeated_lines,
            uppercase_lines=uppercase_lines,
            short_lines=short_lines,
            long_lines=long_lines,
        )

        self._apply_profile_rules(report)

        return report

    def _build_anomalies(
        self,
        report: AnomalyReport,
        numeric_lines: list[str],
        repeated_lines: list[tuple[str, int]],
        uppercase_lines: list[str],
        short_lines: list[str],
        long_lines: list[str],
    ) -> None:
        maximum_replacement = int(
            self.thresholds.get(
                "maximum_replacement_characters",
                0,
            )
        )

        if (
            report.replacement_character_count
            > maximum_replacement
        ):
            report.anomalies.append(
                Anomaly(
                    code="replacement_characters",
                    severity="ERROR",
                    message=(
                        "Se encontraron caracteres Unicode "
                        "de sustitución."
                    ),
                    count=report.replacement_character_count,
                )
            )

        maximum_null = int(
            self.thresholds.get(
                "maximum_null_characters",
                0,
            )
        )

        if report.null_character_count > maximum_null:
            report.anomalies.append(
                Anomaly(
                    code="null_characters",
                    severity="ERROR",
                    message=(
                        "Se encontraron caracteres nulos."
                    ),
                    count=report.null_character_count,
                )
            )

        maximum_controls = int(
            self.thresholds.get(
                "maximum_control_characters",
                0,
            )
        )

        if (
            report.control_character_count
            > maximum_controls
        ):
            report.anomalies.append(
                Anomaly(
                    code="control_characters",
                    severity="ERROR",
                    message=(
                        "Persisten caracteres de control."
                    ),
                    count=report.control_character_count,
                )
            )

        if report.page_marker_count > 0:
            report.anomalies.append(
                Anomaly(
                    code="page_markers",
                    severity="ERROR",
                    message=(
                        "Persisten marcas temporales de página."
                    ),
                    count=report.page_marker_count,
                )
            )

        maximum_symbol_ratio = float(
            self.thresholds.get(
                "maximum_symbol_ratio",
                0.03,
            )
        )

        if report.symbol_ratio > maximum_symbol_ratio:
            report.anomalies.append(
                Anomaly(
                    code="excessive_symbols",
                    severity="WARNING",
                    message=(
                        "La proporción de símbolos no "
                        "lingüísticos es elevada."
                    ),
                    ratio=report.symbol_ratio,
                )
            )

        maximum_numeric_ratio = float(
            self.thresholds.get(
                "maximum_numeric_line_ratio",
                0.03,
            )
        )

        if (
            report.numeric_line_ratio
            > maximum_numeric_ratio
        ):
            report.anomalies.append(
                Anomaly(
                    code="numeric_lines",
                    severity="WARNING",
                    message=(
                        "Existe una proporción elevada de "
                        "líneas numéricas."
                    ),
                    count=len(numeric_lines),
                    ratio=report.numeric_line_ratio,
                    examples=numeric_lines[:10],
                )
            )

        maximum_repeated_ratio = float(
            self.thresholds.get(
                "maximum_repeated_line_ratio",
                0.08,
            )
        )

        if (
            report.repeated_line_ratio
            > maximum_repeated_ratio
        ):
            report.anomalies.append(
                Anomaly(
                    code="repeated_lines",
                    severity="WARNING",
                    message=(
                        "Se detectó repetición excesiva de líneas."
                    ),
                    count=sum(
                        count
                        for _, count in repeated_lines
                    ),
                    ratio=report.repeated_line_ratio,
                    examples=[
                        f"{line} ({count} veces)"
                        for line, count
                        in repeated_lines[:10]
                    ],
                )
            )

        maximum_uppercase_ratio = float(
            self.thresholds.get(
                "maximum_uppercase_line_ratio",
                0.08,
            )
        )

        if (
            report.uppercase_line_ratio
            > maximum_uppercase_ratio
        ):
            report.anomalies.append(
                Anomaly(
                    code="uppercase_lines",
                    severity="WARNING",
                    message=(
                        "Existe una proporción elevada de "
                        "líneas en mayúsculas."
                    ),
                    count=len(uppercase_lines),
                    ratio=report.uppercase_line_ratio,
                    examples=uppercase_lines[:10],
                )
            )

        warning_hyphenated = int(
            self.thresholds.get(
                "warning_hyphenated_line_breaks",
                10,
            )
        )

        if (
            report.hyphenated_line_break_count
            > warning_hyphenated
        ):
            report.anomalies.append(
                Anomaly(
                    code="hyphenated_line_breaks",
                    severity="WARNING",
                    message=(
                        "Se detectaron posibles palabras "
                        "cortadas por salto de línea."
                    ),
                    count=(
                        report.hyphenated_line_break_count
                    ),
                )
            )

        warning_short_ratio = float(
            self.thresholds.get(
                "warning_short_line_ratio",
                0.65,
            )
        )

        if report.short_line_ratio > warning_short_ratio:
            report.anomalies.append(
                Anomaly(
                    code="excessive_short_lines",
                    severity="INFO",
                    message=(
                        "El documento contiene muchas líneas "
                        "cortas. Puede corresponder a teatro "
                        "o verso."
                    ),
                    count=len(short_lines),
                    ratio=report.short_line_ratio,
                    examples=short_lines[:10],
                )
            )

        if long_lines:
            report.anomalies.append(
                Anomaly(
                    code="excessive_long_lines",
                    severity="INFO",
                    message=(
                        "Se encontraron líneas excesivamente "
                        "largas."
                    ),
                    count=len(long_lines),
                    examples=[
                        line[:200]
                        for line in long_lines[:5]
                    ],
                )
            )

    def _apply_profile_rules(
        self,
        report: AnomalyReport,
    )  -> None:
        filtered_anomalies: list[Anomaly] = []

        for anomaly in report.anomalies:
            if anomaly.code in self.disabled_anomalies:
                continue

            overridden_severity = (
                self.severity_overrides.get(
                    anomaly.code
                )
            )

            if overridden_severity:
                anomaly.severity = str(
                    overridden_severity
                ).upper()

            filtered_anomalies.append(anomaly)

        report.anomalies = filtered_anomalies

    @staticmethod
    def _safe_ratio(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0

        return numerator / denominator

    @staticmethod
    def _is_numeric_line(line: str) -> bool:
        normalized = re.sub(r"[\s.,:;()\-–—]", "", line)
        return normalized.isdigit() and len(normalized) > 0

    @staticmethod
    def _is_uppercase_line(line: str) -> bool:
        letters = [
            character
            for character in line
            if character.isalpha()
        ]

        if len(letters) < 5:
            return False

        uppercase = sum(
            character.isupper()
            for character in letters
        )

        return uppercase / len(letters) >= 0.90

    @staticmethod
    def _find_repeated_lines(
        lines: list[str],
    ) -> list[tuple[str, int]]:
        normalized_lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in lines
            if len(line.strip()) >= 5
        ]

        counts = Counter(normalized_lines)

        repeated = [
            (line, count)
            for line, count in counts.items()
            if count >= 3
        ]

        return sorted(
            repeated,
            key=lambda item: item[1],
            reverse=True,
        )