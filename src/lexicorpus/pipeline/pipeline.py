from pathlib import Path

from lexicorpus.acquisition.base_connector import BaseConnector
from lexicorpus.classification.literary_metadata import (
    LiteraryMetadataClassifier,
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
from lexicorpus.cleaning.canonical_cleaner import (
    CanonicalCleaner,
)


class DocumentPipeline:
    def __init__(
        self,
        connector: BaseConnector,
        extractor_factory: ExtractorFactory,
        cleaner: DocumentCleaner,
        normalizer: TextNormalizer,
        classifier: LiteraryMetadataClassifier,
        validator: DocumentValidator,
        file_repository: FileRepository,
        document_repository: DocumentRepository,
        canonical_cleaner: CanonicalCleaner,
    ) -> None:
        self.connector = connector
        self.extractor_factory = extractor_factory
        self.cleaner = cleaner
        self.normalizer = normalizer
        self.classifier = classifier
        self.validator = validator
        self.file_repository = file_repository
        self.document_repository = document_repository

    def run(self) -> list[Document]:
        results: list[Document] = []

        for document in self.connector.discover():
            try:
                self._process(document)
            except Exception as exc:
                document.reject(
                    f"{type(exc).__name__}: {exc}"
                )
                self.document_repository.save(document)

            results.append(document)

        return results

    def _process(self, document: Document) -> None:
        document.original_sha256 = HashService.sha256_file(
            document.original_path
        )

        if self.document_repository.exists_by_original_hash(
            document.original_sha256
        ):
            document.reject(
                "El archivo original ya está registrado."
            )
            return

        document.change_status(DocumentStatus.REGISTERED)
        self.document_repository.save(document)

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
        document.extracted_sha256 = HashService.sha256_text(
            extracted_text
        )
        document.change_status(DocumentStatus.EXTRACTED)
        self.document_repository.save(document)

        cleaned_text = self.cleaner.clean(extracted_text)
        document.cleaned_path = (
            self.file_repository.write_stage_text(
                stage_directory="cleaned",
                source_code=document.source_code,
                document_id=document.document_id,
                text=cleaned_text,
            )
        )
        document.change_status(DocumentStatus.CLEANED)
        self.document_repository.save(document)

        normalized_text = self.normalizer.normalize(
            cleaned_text
        )
        document.normalized_path = (
            self.file_repository.write_stage_text(
                stage_directory="normalized",
                source_code=document.source_code,
                document_id=document.document_id,
                text=normalized_text,
            )
        )
        document.change_status(DocumentStatus.NORMALIZED)

        canonical_text = self.canonical_cleaner.clean(
            normalized_text
        )

        self.classifier.classify(document)
        document.change_status(DocumentStatus.CLASSIFIED)

        metrics = calculate_metrics(canonical_text)
        document.character_count = metrics.character_count
        document.word_count = metrics.word_count
        document.paragraph_count = metrics.paragraph_count

        validation = self.validator.validate(
            canonical_text,
            document.word_count,
        )

        if not validation.accepted:
            document.reject("; ".join(validation.errors))
            self.document_repository.save(document)
            return

        document.validation_passed = True
        document.change_status(DocumentStatus.VALIDATED)

        document.canonical_path = (
            self.file_repository.write_stage_text(
                stage_directory="canonical",
                source_code=document.source_code,
                document_id=document.document_id,
                text=canonical_text,
            )
        )
        document.canonical_sha256 = HashService.sha256_text(
            canonical_text
        )
        document.change_status(DocumentStatus.CANONICAL)

        self.document_repository.save(document)