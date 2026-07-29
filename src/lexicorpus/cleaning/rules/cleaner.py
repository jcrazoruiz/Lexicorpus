import re


class DocumentCleaner:
    PAGE_MARKER_PATTERN = re.compile(
        r"\[\[PÁGINA\s+\d+\]\]",
        flags=re.IGNORECASE,
    )

    CONTROL_CHAR_PATTERN = re.compile(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
    )

    EXCESSIVE_SPACES_PATTERN = re.compile(r"[ \t]+")
    EXCESSIVE_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

    def clean(self, text: str) -> str:
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = self.PAGE_MARKER_PATTERN.sub("\n", cleaned)
        cleaned = self.CONTROL_CHAR_PATTERN.sub("", cleaned)
        cleaned = self.EXCESSIVE_SPACES_PATTERN.sub(" ", cleaned)

        lines = [
            line.strip()
            for line in cleaned.splitlines()
        ]

        cleaned = "\n".join(lines)
        cleaned = self.EXCESSIVE_BLANK_LINES_PATTERN.sub(
            "\n\n",
            cleaned,
        )

        return cleaned.strip()