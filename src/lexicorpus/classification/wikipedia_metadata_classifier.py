from __future__ import annotations

import json
from pathlib import Path

from lexicorpus.classification.base_classifier import (
    BaseClassifier,
)
from lexicorpus.domain.document import (
    Document,
)


class WikipediaMetadataClassifier(
    BaseClassifier
):
    """
    Enriquece documentos procedentes de Wikipedia
    en español utilizando los metadatos generados
    durante la extracción del dump oficial.
    """

    def __init__(
        self,
        acquisition_metadata_path: Path,
    ) -> None:
        self.records_by_local_path = (
            self._load_records(
                acquisition_metadata_path
            )
        )

    def classify(
        self,
        document: Document,
    ) -> None:

        document.language = "es"

        document.thematic_domain = (
            "general"
        )

        document.document_type = (
            "articulo_enciclopedico"
        )

        normalized_path = str(
            document
            .original_path
            .resolve()
        )

        record = (
            self.records_by_local_path.get(
                normalized_path
            )
        )

        if record is None:
            document.title = (
                document.original_path.stem
            )

            document.metadata[
                "classification_warning"
            ] = (
                "No se encontró el registro "
                "de adquisición de Wikipedia."
            )

            return

        document.title = (
            record.get("title")
            or document.original_path.stem
        )

        # Wikipedia no tiene autor individual
        # por artículo en este modelo.
        document.author = None

        document.metadata.update(
            {
                "remote_identifier": (
                    record.get(
                        "identifier"
                    )
                ),
                "page_id": (
                    record.get(
                        "page_id"
                    )
                ),
                "source_url": (
                    record.get(
                        "source_url"
                    )
                ),
                "snapshot_date": (
                    record.get(
                        "snapshot_date"
                    )
                ),
                "segment": (
                    record.get(
                        "segment"
                    )
                ),
                "original_wikitext_characters": (
                    record.get(
                        "original_wikitext_characters"
                    )
                ),
                "cleaned_characters": (
                    record.get(
                        "cleaned_characters"
                    )
                ),
                "wikitext_reduction_ratio": (
                    record.get(
                        "reduction_ratio"
                    )
                ),
            }
        )

    @staticmethod
    def _load_records(
        metadata_path: Path,
    ) -> dict[str, dict]:

        records: dict[
            str,
            dict,
        ] = {}

        if not metadata_path.exists():
            raise FileNotFoundError(
                "No existe el archivo "
                "de metadatos de Wikipedia: "
                f"{metadata_path}"
            )

        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as metadata_file:

            for line in metadata_file:

                if not line.strip():
                    continue

                record = json.loads(
                    line
                )

                if (
                    record.get(
                        "acquisition_status"
                    )
                    != "EXTRACTED"
                ):
                    continue

                local_path = (
                    record.get(
                        "local_path"
                    )
                )

                if not local_path:
                    continue

                normalized_path = str(
                    Path(
                        local_path
                    ).resolve()
                )

                records[
                    normalized_path
                ] = record

        return records