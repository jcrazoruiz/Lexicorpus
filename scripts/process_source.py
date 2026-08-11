from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datetime import datetime
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.acquisition.local_connector import (
    LocalConnector,
)
from lexicorpus.cleaning.canonical_cleaner import (
    CanonicalCleaner,
)
from lexicorpus.cleaning.cleaner import DocumentCleaner
from lexicorpus.config.source_registry import (
    SOURCE_REGISTRY,
)
from lexicorpus.extraction.extractor_factory import (
    ExtractorFactory,
)
from lexicorpus.normalization.normalizer import (
    TextNormalizer,
)
from lexicorpus.pipeline.pipeline import DocumentPipeline
from lexicorpus.storage.database import Database
from lexicorpus.storage.document_repository import (
    DocumentRepository,
)
from lexicorpus.storage.file_repository import FileRepository
from lexicorpus.validation.validator import (
    DocumentValidator,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Procesa una fuente documental mediante "
            "el pipeline común de LexiCorpus."
        )
    )

    parser.add_argument(
        "--source",
        required=True,
        choices=sorted(SOURCE_REGISTRY.keys()),
        help="Fuente documental que se desea procesar.",
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help=(
            "Número máximo de documentos nuevos a procesar. "
            "Si se omite, procesa todos los disponibles."
        ),
    )

    return parser.parse_args()

def format_elapsed_time(
    elapsed_seconds: float,
) -> str:
    total_seconds = int(elapsed_seconds)

    hours, remainder = divmod(
        total_seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )

def main(
    source_code: str,
    maximum_documents_to_process: int | None = None,
) -> int:
    source = SOURCE_REGISTRY[source_code]

    database = Database(
        PROJECT_ROOT
        / "metadata"
        / "database"
        / "lexicorpus.db"
    )

    database.initialize()

    with database.connect() as connection:
        repository = DocumentRepository(connection)

        repository.register_source(
            source_code=source.code,
            source_name=source.name,
            acquisition_method=source.acquisition_method,
        )

        connector = LocalConnector(
            source_code=source.code,
            input_directory=(
                PROJECT_ROOT
                / source.raw_directory
            ),
            supported_extensions=(
                source.supported_extensions
            ),
        )

        classifier = source.classifier_factory(
            PROJECT_ROOT
        )

        pipeline = DocumentPipeline(
            connector=connector,
            extractor_factory=ExtractorFactory(),
            cleaner=DocumentCleaner(),
            normalizer=TextNormalizer(),
            canonical_cleaner=CanonicalCleaner(),
            classifier=classifier,
            validator=DocumentValidator(),
            file_repository=FileRepository(
                PROJECT_ROOT
            ),
            document_repository=repository,
            maximum_documents_to_process=(
                maximum_documents_to_process
            ),
        )

        started_at = datetime.now()
        timer_start = perf_counter()

        results = pipeline.run()

        elapsed_seconds = (
            perf_counter() - timer_start
        )

        finished_at = datetime.now()

        elapsed_formatted = format_elapsed_time(
            elapsed_seconds
        )

    print("\nResultado del procesamiento")
    print("-" * 80)

    for document in results:
        print(
            f"{document.original_filename:<40} "
            f"{document.status.value:<12} "
            f"{document.word_count:>10} palabras"
        )

        if document.rejection_reason:
            print(
                f"  Motivo: "
                f"{document.rejection_reason}"
            )

    accepted = sum(
        document.status.value == "CANONICAL"
        for document in results
    )

    rejected = len(results) - accepted

    print("-" * 80)
    print(f"Fuente: {source.name}")
    print(f"Documentos nuevos procesados: {len(results)}")
    print(f"Canónicos: {accepted}")
    print(
        f"Rechazados o con error: {rejected}"
    )
    print(
        "Inicio              : "
        f"{started_at:%Y-%m-%d %H:%M:%S}"
    )

    print(
        "Finalización        : "
        f"{finished_at:%Y-%m-%d %H:%M:%S}"
    )

    print(
        "Tiempo transcurrido : "
        f"{elapsed_formatted}"
    )

    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    args = parse_arguments()

    raise SystemExit(
        main(
            source_code=args.source,
            maximum_documents_to_process=(
                args.max_documents
            ),
        )
    )