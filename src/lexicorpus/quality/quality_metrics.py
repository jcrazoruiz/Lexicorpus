import re
from dataclasses import dataclass


WORD_PATTERN = re.compile(
    r"[^\W\d_]+(?:['’\-][^\W\d_]+)*",
    flags=re.UNICODE,
)


@dataclass(frozen=True, slots=True)
class TextMetrics:
    character_count: int
    word_count: int
    paragraph_count: int
    line_count: int


def calculate_metrics(text: str) -> TextMetrics:
    paragraphs = [
        paragraph
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    return TextMetrics(
        character_count=len(text),
        word_count=len(WORD_PATTERN.findall(text)),
        paragraph_count=len(paragraphs),
        line_count=len(lines),
    )