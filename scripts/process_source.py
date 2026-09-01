from __future__ import annotations

import argparse
import sys

from datetime import datetime
from pathlib import Path
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
from lexicorpus.pipeline.pipeline import (
    DocumentPipeline,
)
from lexicorpus.storage.database import (
    Database,
)
from lexicorpus.storage.document_repository import (
    DocumentRepository,
)
from lexicorpus.storage.file_repository import (
    FileRepository,
)
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
        choices=sorted(
            SOURCE_REGISTRY.keys()
        ),
        help=(
            "Fuente documental que se desea procesar."
        ),
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help=(
            "Número máximo de documentos nuevos "
            "a procesar. Si se omite, procesa "
            "todos los disponibles."
        ),
    )

    return parser.parse_args()


def format_elapsed_time(
    elapsed_seconds: float,
) -> str:
    total_seconds = int(
        elapsed_seconds
    )

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


def build_validator(
    source_code: str,
) -> DocumentValidator:
    """
    Construye el validador documental de acuerdo
    con las características de la fuente.

    Wikinoticias contiene noticias breves que son
    documentalmente válidas, por lo que utiliza
    umbrales menores que el perfil general.
    """

    if source_code == "wikinews_es":
        return DocumentValidator(
            minimum_characters=500,
            minimum_words=100,
        )

    return DocumentValidator()


def build_progress_reporter(
    total_documents: int | None,
    timer_start: float,
):
    """
    Construye un callback que reporta el avance
    cada 10 % del procesamiento.

    El reporte incluye:
    - documentos procesados
    - documentos canónicos
    - documentos rechazados
    - tiempo transcurrido
    - velocidad promedio
    - tiempo estimado restante
    """

    if not total_documents:
        return None

    next_percentage = 10
    canonical_count = 0
    rejected_count = 0

    def report(
        processed: int,
        document,
    ) -> None:
        nonlocal next_percentage
        nonlocal canonical_count
        nonlocal rejected_count

        if document.status.value == "CANONICAL":
            canonical_count += 1
        else:
            rejected_count += 1

        percentage = (
            processed
            / total_documents
            * 100
        )

        if (
            percentage < next_percentage
            and processed < total_documents
        ):
            return

        elapsed_seconds = (
            perf_counter()
            - timer_start
        )

        documents_per_minute = (
            processed
            / elapsed_seconds
            * 60
            if elapsed_seconds > 0
            else 0
        )

        remaining_documents = max(
            total_documents - processed,
            0,
        )

        if documents_per_minute > 0:
            estimated_remaining_seconds = (
                remaining_documents
                / documents_per_minute
                * 60
            )
        else:
            estimated_remaining_seconds = 0

        shown_percentage = min(
            next_percentage,
            100,
        )

        print()
        print("=" * 70)

        print(
            f"[PROGRESO {shown_percentage}%]"
        )

        print(
            "Procesados   : "
            f"{processed:,} / "
            f"{total_documents:,}"
        )

        print(
            "CANONICAL    : "
            f"{canonical_count:,}"
        )

        print(
            "REJECTED     : "
            f"{rejected_count:,}"
        )

        print(
            "Transcurrido : "
            f"{format_elapsed_time(elapsed_seconds)}"
        )

        print(
            "Ritmo        : "
            f"{documents_per_minute:.2f} "
            "documentos/min"
        )

        print(
            "ETA restante : "
            f"{format_elapsed_time(
                estimated_remaining_seconds
            )}"
        )

        print("=" * 70)

        while (
            next_percentage <= percentage
            and next_percentage < 100
        ):
            next_percentage += 10

    return report


def main(
    source_code: str,
    maximum_documents_to_process: int | None = None,
) -> int:
    source = SOURCE_REGISTRY[
        source_code
    ]

    database = Database(
        PROJECT_ROOT
        / "metadata"
        / "database"
        / "lexicorpus.db"
    )

    database.initialize()

    with database.connect() as connection:
        repository = DocumentRepository(
            connection
        )

        repository.register_source(
            source_code=source.code,
            source_name=source.name,
            acquisition_method=(
                source.acquisition_method
            ),
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

        classifier = (
            source.classifier_factory(
                PROJECT_ROOT
            )
        )

        validator = build_validator(
            source_code
        )

        started_at = datetime.now()
        timer_start = perf_counter()

        progress_reporter = (
            build_progress_reporter(
                total_documents=(
                    maximum_documents_to_process
                ),
                timer_start=timer_start,
            )
        )

        pipeline = DocumentPipeline(
            connector=connector,
            extractor_factory=(
                ExtractorFactory()
            ),
            cleaner=(
                DocumentCleaner()
            ),
            normalizer=(
                TextNormalizer()
            ),
            canonical_cleaner=(
                CanonicalCleaner()
            ),
            classifier=classifier,
            validator=validator,
            file_repository=(
                FileRepository(
                    PROJECT_ROOT
                )
            ),
            document_repository=(
                repository
            ),
            maximum_documents_to_process=(
                maximum_documents_to_process
            ),
            progress_callback=(
                progress_reporter
            ),
        )

        results = pipeline.run()

        elapsed_seconds = (
            perf_counter()
            - timer_start
        )

        finished_at = datetime.now()

        elapsed_formatted = (
            format_elapsed_time(
                elapsed_seconds
            )
        )

    print(
        "\nResultado del procesamiento"
    )

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
        document.status.value
        == "CANONICAL"
        for document in results
    )

    rejected = (
        len(results)
        - accepted
    )

    print("-" * 80)

    print(
        f"Fuente: "
        f"{source.name}"
    )

    print(
        "Documentos nuevos procesados: "
        f"{len(results)}"
    )

    print(
        f"Canónicos: "
        f"{accepted}"
    )

    print(
        "Rechazados o con error: "
        f"{rejected}"
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

    return (
        0
        if rejected == 0
        else 1
    )


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