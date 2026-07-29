from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from lexicorpus.acquisition.local_connector import LocalConnector
from lexicorpus.classification.literary_metadata import (
    LiteraryMetadataClassifier,
)
from lexicorpus.cleaning.cleaner import DocumentCleaner
from lexicorpus.extraction.extractor_factory import ExtractorFactory
from lexicorpus.normalization.normalizer import TextNormalizer
from lexicorpus.pipeline.pipeline import DocumentPipeline
from lexicorpus.storage.database import Database
from lexicorpus.storage.document_repository import (
    DocumentRepository,
)
from lexicorpus.storage.file_repository import FileRepository
from lexicorpus.validation.validator import DocumentValidator


def main() -> int:
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
            source_code="literatura_clasica",
            source_name="Literatura clásica en español",
            acquisition_method="local_directory",
        )

        connector = LocalConnector(
            source_code="literatura_clasica",
            input_directory=(
                PROJECT_ROOT
                / "data"
                / "raw"
                / "literatura_clasica"
            ),
            supported_extensions={".pdf", ".txt"},
        )

        pipeline = DocumentPipeline(
            connector=connector,
            extractor_factory=ExtractorFactory(),
            cleaner=DocumentCleaner(),
            normalizer=TextNormalizer(),
            classifier=LiteraryMetadataClassifier(),
            validator=DocumentValidator(),
            file_repository=FileRepository(PROJECT_ROOT),
            document_repository=repository,
        )

        results = pipeline.run()

    print("\nResultado del procesamiento")
    print("-" * 72)

    for document in results:
        print(
            f"{document.original_filename:<35} "
            f"{document.status.value:<12} "
            f"{document.word_count:>10} palabras"
        )

        if document.rejection_reason:
            print(
                f"  Motivo: {document.rejection_reason}"
            )

    accepted = sum(
        document.status.value == "CANONICAL"
        for document in results
    )

    rejected = len(results) - accepted

    print("-" * 72)
    print(f"Canónicos: {accepted}")
    print(f"Rechazados o con error: {rejected}")

    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())