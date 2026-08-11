from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


WORD_PATTERN = re.compile(
    r"(?<![\wáéíóúüñ])"
    r"[a-záéíóúüñ]{2,}"
    r"(?![\wáéíóúüñ])",
    flags=re.IGNORECASE,
)


@dataclass(slots=True)
class LexicalFrequency:
    word: str
    absolute_frequency: int
    document_frequency: int


class LexicalFrequencyAnalyzer:

    def analyze(
        self,
        document_paths: list[Path],
    ) -> list[LexicalFrequency]:

        frequencies: Counter[str] = Counter()
        document_frequencies: Counter[str] = Counter()

        for document_path in document_paths:
            text = document_path.read_text(
                encoding="utf-8"
            )

            words = self._tokenize(text)

            frequencies.update(words)

            document_frequencies.update(
                set(words)
            )

        results = [
            LexicalFrequency(
                word=word,
                absolute_frequency=frequency,
                document_frequency=(
                    document_frequencies[word]
                ),
            )
            for word, frequency in frequencies.items()
        ]

        results.sort(
            key=lambda item: (
                -item.absolute_frequency,
                item.word,
            )
        )

        return results

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:

        normalized_text = text.lower()

        return WORD_PATTERN.findall(
            normalized_text
        )