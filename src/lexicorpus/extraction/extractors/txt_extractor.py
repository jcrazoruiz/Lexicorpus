from pathlib import Path

from lexicorpus.extraction.base_extractor import BaseExtractor


class TxtExtractor(BaseExtractor):
    def __init__(self, encodings: list[str] | None = None) -> None:
        self.encodings = encodings or [
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin-1",
        ]

    def extract(self, file_path: Path) -> str:
        errors: list[str] = []

        for encoding in self.encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError as exc:
                errors.append(f"{encoding}: {exc}")

        attempted = ", ".join(self.encodings)
        raise UnicodeError(
            f"No fue posible decodificar {file_path.name}. "
            f"Codificaciones intentadas: {attempted}"
        )