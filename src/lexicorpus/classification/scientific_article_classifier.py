from __future__ import annotations

import json
from pathlib import Path

from lexicorpus.classification.base_classifier import (
    BaseClassifier,
)
from lexicorpus.domain.document import Document

class ScientificArticleClassifier(BaseClassifier):
    def __init__(
        self,
        acquisition_metadata_path: Path,
    ) -> None:
        self.records_by_local_path = self._load_records(
            acquisition_metadata_path
        )

    def classify(
        self,
        document: Document,
    ) -> None:
        document.language = "es"
        document.thematic_domain = "cientifico"
        document.document_type = "articulo_cientifico"

        record = self.records_by_local_path.get(
            str(document.original_path.resolve())
        )

        if record is None:
            document.title = document.original_path.stem
            document.metadata["classification_warning"] = (
                "No se encontró el registro de adquisición."
            )
            return

        document.title = (
            record.get("title")
            or document.original_path.stem
        )

        authors = record.get("authors") or []

        document.author = (
            "; ".join(authors)
            if authors
            else None
        )

        document.metadata.update(
            {
                "remote_identifier": record.get(
                    "identifier"
                ),
                "article_url": record.get(
                    "article_url"
                ),
                "pdf_url": record.get(
                    "pdf_url"
                ),
                "publication_date": record.get(
                    "publication_date"
                ),
                "subjects": record.get(
                    "subjects",
                    [],
                ),
                "rights": record.get(
                    "rights",
                    [],
                ),
            }
        )

    @staticmethod
    def _load_records(
        metadata_path: Path,
    ) -> dict[str, dict]:
        records: dict[str, dict] = {}

        if not metadata_path.exists():
            raise FileNotFoundError(
                f"No existe el archivo de metadatos: "
                f"{metadata_path}"
            )

        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as metadata_file:
            for line in metadata_file:
                if not line.strip():
                    continue

                record = json.loads(line)

                if (
                    record.get("acquisition_status")
                    != "DOWNLOADED"
                ):
                    continue

                local_path = record.get("local_path")

                if not local_path:
                    continue

                normalized_path = str(
                    Path(local_path).resolve()
                )

                records[normalized_path] = record

        return records