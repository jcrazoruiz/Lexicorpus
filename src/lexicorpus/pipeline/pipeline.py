from collections.abc import Callable
from pathlib import Path

from lexicorpus.acquisition.base_connector import BaseConnector
from lexicorpus.classification.base_classifier import (
    BaseClassifier,
)
from lexicorpus.cleaning.canonical_cleaner import (
    CanonicalCleaner,
)
from lexicorpus.cleaning.cleaner import DocumentCleaner
from lexicorpus.domain.document import Document
from lexicorpus.domain.enums import DocumentStatus
from lexicorpus.extraction.extractor_factory import ExtractorFactory
from lexicorpus.normalization.normalizer import TextNormalizer
from lexicorpus.quality.quality_metrics import calculate_metrics
from lexicorpus.registration.hash_service import HashService
from lexicorpus.storage.document_repository import (
    DocumentRepository,
)
from lexicorpus.storage.file_repository import FileRepository
from lexicorpus.validation.validator import DocumentValidator


class DocumentPipeline:
    def __init__(
        self,
        connector: BaseConnector,
        extractor_factory: ExtractorFactory,
        cleaner: DocumentCleaner,
        normalizer: TextNormalizer,
        classifier: BaseClassifier,
        validator: DocumentValidator,
        file_repository: FileRepository,
        document_repository: DocumentRepository,
        canonical_cleaner: CanonicalCleaner,
        maximum_documents_to_process: int | None = None,
        progress_callback: (
            Callable[[int, Document], None] | None
        ) = None,
    ) -> None:
        self.connector = connector
        self.extractor_factory = extractor_factory
        self.cleaner = cleaner
        self.normalizer = normalizer
        self.classifier = classifier
        self.validator = validator
        self.file_repository = file_repository
        self.document_repository = document_repository
        self.canonical_cleaner = canonical_cleaner
        self.maximum_documents_to_process = (
            maximum_documents_to_process
        )
        self.progress_callback = progress_callback

    def run(self) -> list[Document]:
        results: list[Document] = []
        new_documents_count = 0

        for document in self.connector.discover():

            # Calcular la huella antes de decidir
            # si el documento debe procesarse.
            document.original_sha256 = (
                HashService.sha256_file(
                    document.original_path
                )
            )

            # Si ya está registrado, se ignora y
            # continuamos buscando otro documento nuevo.
            if self.document_repository.exists_by_original_hash(
                document.original_sha256
            ):
                continue

            # El límite se aplica solamente
            # sobre documentos nuevos.
            if (
                self.maximum_documents_to_process
                and new_documents_count
                >= self.maximum_documents_to_process
            ):
                break

            new_documents_count += 1

            try:
                self._process(document)

            except Exception as exc:
                document.reject(
                    f"{type(exc).__name__}: {exc}"
                )

                self.document_repository.save(
                    document
                )

            results.append(document)

            if self.progress_callback:
                self.progress_callback(
                    new_documents_count,
                    document,
                )

        return results

    def _process(self, document: Document) -> None:
        # La huella original ya fue calculada y validada
        # en run() antes de iniciar el procesamiento.

        document.change_status(
            DocumentStatus.REGISTERED
        )
        self.document_repository.save(
            document
        )

        extractor = self.extractor_factory.get(
            document.extension
        )

        extracted_text = extractor.extract(
            document.original_path
        )

        document.extracted_path = (
            self.file_repository.write_stage_text(
                stage_directory="extracted",
                source_code=document.source_code,
                document_id=document.document_id,
                text=extracted_text,
            )
        )

        document.extracted_sha256 = (
            HashService.sha256_text(
                extracted_text
            )
        )

        document.change_status(
            DocumentStatus.EXTRACTED
        )

        self.document_repository.save(
            document
        )

        cleaned_text = self.cleaner.clean(
            extracted_text
        )

        document.cleaned_path = (
            self.file_repository.write_stage_text(
                stage_directory="cleaned",
                source_code=document.source_code,
                document_id=document.document_id,
                text=cleaned_text,
            )
        )

        document.change_status(
            DocumentStatus.CLEANED
        )

        self.document_repository.save(
            document
        )

        normalized_text = (
            self.normalizer.normalize(
                cleaned_text
            )
        )

        document.normalized_path = (
            self.file_repository.write_stage_text(
                stage_directory="normalized",
                source_code=document.source_code,
                document_id=document.document_id,
                text=normalized_text,
            )
        )

        document.change_status(
            DocumentStatus.NORMALIZED
        )

        canonical_text = (
            self.canonical_cleaner.clean(
                normalized_text
            )
        )

        self.classifier.classify(
            document
        )

        document.change_status(
            DocumentStatus.CLASSIFIED
        )

        metrics = calculate_metrics(
            canonical_text
        )

        document.character_count = (
            metrics.character_count
        )

        document.word_count = (
            metrics.word_count
        )

        document.paragraph_count = (
            metrics.paragraph_count
        )

        validation = self.validator.validate(
            canonical_text,
            document.word_count,
        )

        if not validation.accepted:
            document.reject(
                "; ".join(
                    validation.errors
                )
            )

            self.document_repository.save(
                document
            )

            return

        document.validation_passed = True

        document.change_status(
            DocumentStatus.VALIDATED
        )

        document.canonical_path = (
            self.file_repository.write_stage_text(
                stage_directory="canonical",
                source_code=document.source_code,
                document_id=document.document_id,
                text=canonical_text,
            )
        )

        document.canonical_sha256 = (
            HashService.sha256_text(
                canonical_text
            )
        )

        document.change_status(
            DocumentStatus.CANONICAL
        )

        self.document_repository.save(
            document
        )