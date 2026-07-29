import re
import unicodedata


class TextNormalizer:
    MULTIPLE_SPACES_PATTERN = re.compile(r"[^\S\n]+")
    TRAILING_SPACES_PATTERN = re.compile(r"[ \t]+\n")
    MULTIPLE_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFC", text)

        normalized = (
            normalized
            .replace("\u00A0", " ")
            .replace("\u2007", " ")
            .replace("\u202F", " ")
        )

        normalized = self.TRAILING_SPACES_PATTERN.sub(
            "\n",
            normalized,
        )
        normalized = self.MULTIPLE_SPACES_PATTERN.sub(
            " ",
            normalized,
        )
        normalized = self.MULTIPLE_BLANK_LINES_PATTERN.sub(
            "\n\n",
            normalized,
        )

        return normalized.strip() + "\n"