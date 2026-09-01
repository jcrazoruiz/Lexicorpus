from __future__ import annotations

import json
from pathlib import Path

from lexicorpus.classification.base_classifier import (
    BaseClassifier,
)

from lexicorpus.domain.document import (
    Document,
)


class WikinewsMetadataClassifier(
    BaseClassifier
):
    """
    Enriquece documentos procedentes de Wikinoticias
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

        # -----------------------------------------------------
        # Clasificación general de la fuente
        # -----------------------------------------------------

        document.language = "es"

        document.thematic_domain = (
            "general"
        )

        document.document_type = (
            "articulo_prensa"
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

        # -----------------------------------------------------
        # Fallback si no existe registro de adquisición
        # -----------------------------------------------------

        if record is None:

            document.title = (
                document.original_path.stem
            )

            document.author = None

            document.metadata[
                "classification_warning"
            ] = (
                "No se encontró el registro "
                "de adquisición de Wikinoticias."
            )

            return

        # -----------------------------------------------------
        # Metadatos principales
        # -----------------------------------------------------

        document.title = (
            record.get(
                "title"
            )
            or document.original_path.stem
        )

        # Wikinoticias es una fuente colaborativa.
        # No asignamos autor individual en este modelo.
        document.author = None

        # -----------------------------------------------------
        # Metadatos adicionales
        # -----------------------------------------------------

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

                "dump_file": (
                    record.get(
                        "dump_file"
                    )
                ),

                "media_type": (
                    record.get(
                        "media_type"
                    )
                ),

                "publication_date": (
                    record.get(
                        "publication_date"
                    )
                ),

                "categories": (
                    record.get(
                        "categories",
                        [],
                    )
                ),

                "geographic_scope": (
                    record.get(
                        "geographic_scope",
                        [],
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
                "de metadatos de Wikinoticias: "
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