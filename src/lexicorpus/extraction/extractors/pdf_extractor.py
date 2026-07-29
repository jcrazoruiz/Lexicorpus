from pathlib import Path

from pypdf import PdfReader

from lexicorpus.extraction.base_extractor import BaseExtractor


class PdfExtractor(BaseExtractor):
    def extract(self, file_path: Path) -> str:
        reader = PdfReader(file_path)

        extracted_pages: list[str] = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            if page_text.strip():
                extracted_pages.append(
                    f"\n\n[[PÁGINA {page_number}]]\n\n"
                    f"{page_text}"
                )

        text = "".join(extracted_pages).strip()

        if not text:
            raise ValueError(
                f"El PDF {file_path.name} no produjo texto. "
                "Puede tratarse de un documento escaneado que requiera OCR."
            )

        return text