from lexicorpus.extraction.base_extractor import BaseExtractor
from lexicorpus.extraction.extractors.pdf_extractor import PdfExtractor
from lexicorpus.extraction.extractors.txt_extractor import TxtExtractor


class ExtractorFactory:
    def __init__(self) -> None:
        self._extractors: dict[str, BaseExtractor] = {
            ".pdf": PdfExtractor(),
            ".txt": TxtExtractor(),
        }

    def register(
        self,
        extension: str,
        extractor: BaseExtractor,
    ) -> None:
        normalized_extension = extension.lower()

        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        self._extractors[normalized_extension] = extractor

    def get(self, extension: str) -> BaseExtractor:
        normalized_extension = extension.lower()

        try:
            return self._extractors[normalized_extension]
        except KeyError as exc:
            raise ValueError(
                f"No existe extractor para: {normalized_extension}"
            ) from exc