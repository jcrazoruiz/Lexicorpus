from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.domain.document import Document
from lexicorpus.domain.enums import DocumentStatus
from lexicorpus.quality.quality_metrics import (
    calculate_metrics,
)
from lexicorpus.registration.hash_service import (
    HashService,
)
from lexicorpus.storage.database import Database
from lexicorpus.storage.document_repository import (
    DocumentRepository,
)


SOURCE_CODE = "scielo"
SOURCE_NAME = "SciELO México"
ACQUISITION_METHOD = "oai_pmh"

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / SOURCE_CODE
)

CANONICAL_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "canonical"
    / SOURCE_CODE
)

MASTER_MAPPING_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_recovery_master.jsonl"
)

ACQUISITION_METADATA_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "acquisition"
    / "scielo"
    / "scielo_acquisition.jsonl"
)

DATABASE_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "database"
    / "lexicorpus.db"
)


def load_jsonl(
    path: Path,
) -> list[dict]:
    records: list[dict] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line in input_file:
            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def build_acquisition_index() -> dict[str, dict]:
    records = load_jsonl(
        ACQUISITION_METADATA_PATH
    )

    index: dict[str, dict] = {}

    for record in records:
        local_path = record.get(
            "local_path"
        )

        if not local_path:
            continue

        filename = Path(
            local_path
        ).name

        index[filename] = record

    return index


def deterministic_recovery_id(
    raw_filename: str,
) -> str:
    """
    Los documentos que fallaron antes de generar
    EXTRACTED perdieron su UUID original.

    Se genera un UUID determinista para que una
    reconstrucción posterior produzca el mismo ID.
    """
    return str(
        uuid5(
            NAMESPACE_URL,
            f"lexicorpus:scielo:{raw_filename}",
        )
    )


def build_document(
    mapping_record: dict,
    acquisition_index: dict[str, dict],
) -> Document:
    raw_filename = mapping_record[
        "raw_filename"
    ]

    raw_path = (
        RAW_DIRECTORY
        / raw_filename
    )

    if not raw_path.exists():
        raise FileNotFoundError(
            f"No existe RAW: {raw_path}"
        )

    document_id = mapping_record.get(
        "document_id"
    )

    mapping_status = mapping_record.get(
        "status"
    )

    if not document_id:
        document_id = (
            deterministic_recovery_id(
                raw_filename
            )
        )

    document = Document(
        source_code=SOURCE_CODE,
        original_path=raw_path,
        document_id=document_id,
    )

    document.original_sha256 = (
        HashService.sha256_file(
            raw_path
        )
    )

    acquisition_record = (
        acquisition_index.get(
            raw_filename
        )
    )

    # Valores que aplicaba
    # ScientificArticleClassifier.
    document.language = "es"
    document.thematic_domain = (
        "cientifico"
    )
    document.document_type = (
        "articulo_cientifico"
    )

    # En v1.2 no existía una asignación
    # posterior explícita; se conserva el
    # valor por defecto del modelo Document.
    document.corpus_version = "1.0"

    if acquisition_record:
        document.title = (
            acquisition_record.get(
                "title"
            )
            or raw_path.stem
        )

        authors = (
            acquisition_record.get(
                "authors"
            )
            or []
        )

        document.author = (
            "; ".join(authors)
            if authors
            else None
        )

        document.metadata.update(
            {
                "remote_identifier": (
                    acquisition_record.get(
                        "identifier"
                    )
                ),
                "article_url": (
                    acquisition_record.get(
                        "article_url"
                    )
                ),
                "pdf_url": (
                    acquisition_record.get(
                        "pdf_url"
                    )
                ),
                "publication_date": (
                    acquisition_record.get(
                        "publication_date"
                    )
                ),
                "subjects": (
                    acquisition_record.get(
                        "subjects",
                        [],
                    )
                ),
                "rights": (
                    acquisition_record.get(
                        "rights",
                        [],
                    )
                ),
            }
        )

    else:
        document.title = raw_path.stem

        document.metadata[
            "classification_warning"
        ] = (
            "No se encontró el registro "
            "de adquisición durante la "
            "reconstrucción."
        )

    now = datetime.now(
        timezone.utc
    )

    document.created_at = now
    document.updated_at = now

    if mapping_status == "EXTRACTION_ERROR":
        document.status = (
            DocumentStatus.REJECTED
        )

        document.validation_passed = False

        document.rejection_reason = (
            mapping_record.get(
                "error"
            )
            or "Error durante extracción."
        )

        return document

    canonical_path = (
        CANONICAL_DIRECTORY
        / f"{document_id}.txt"
    )

    if canonical_path.exists():
        canonical_text = (
            canonical_path.read_text(
                encoding="utf-8"
            )
        )

        metrics = calculate_metrics(
            canonical_text
        )

        document.word_count = (
            metrics.word_count
        )
        document.character_count = (
            metrics.character_count
        )
        document.paragraph_count = (
            metrics.paragraph_count
        )

        document.canonical_path = (
            canonical_path
        )

        document.canonical_sha256 = (
            HashService.sha256_text(
                canonical_text
            )
        )

        document.validation_passed = True

        document.status = (
            DocumentStatus.CANONICAL
        )

    else:
        # Llegó a EXTRACTED pero no produjo
        # un documento CANONICAL.
        document.status = (
            DocumentStatus.REJECTED
        )

        document.validation_passed = False

        document.rejection_reason = (
            "Documento reconstruido sin "
            "archivo CANONICAL; rechazo "
            "ocurrido durante el pipeline "
            "original."
        )

    return document


def main() -> int:
    master_records = load_jsonl(
        MASTER_MAPPING_PATH
    )

    acquisition_index = (
        build_acquisition_index()
    )

    database = Database(
        DATABASE_PATH
    )

    database.initialize()

    canonical_count = 0
    rejected_count = 0
    recovered_id_count = 0

    with database.connect() as connection:
        repository = DocumentRepository(
            connection
        )

        repository.register_source(
            source_code=SOURCE_CODE,
            source_name=SOURCE_NAME,
            acquisition_method=(
                ACQUISITION_METHOD
            ),
        )

        for position, mapping_record in enumerate(
            master_records,
            start=1,
        ):
            if not mapping_record.get(
                "document_id"
            ):
                recovered_id_count += 1

            document = build_document(
                mapping_record,
                acquisition_index,
            )

            repository.save(
                document
            )

            if (
                document.status
                == DocumentStatus.CANONICAL
            ):
                canonical_count += 1
            else:
                rejected_count += 1

            if position % 500 == 0:
                print(
                    f"Registrados: "
                    f"{position:,}"
                )

    print("\nReconstrucción SciELO")
    print("-" * 72)

    print(
        f"Registros procesados : "
        f"{len(master_records):,}"
    )

    print(
        f"CANONICAL            : "
        f"{canonical_count:,}"
    )

    print(
        f"REJECTED             : "
        f"{rejected_count:,}"
    )

    print(
        f"IDs reconstruidos    : "
        f"{recovered_id_count:,}"
    )

    print(
        f"Base de datos        : "
        f"{DATABASE_PATH}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())