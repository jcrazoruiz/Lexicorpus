from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .enums import DocumentStatus


@dataclass(slots=True)
class Document:
    source_code: str
    original_path: Path
    document_id: str = field(default_factory=lambda: str(uuid4()))
    status: DocumentStatus = DocumentStatus.DISCOVERED

    original_filename: str = ""
    extension: str = ""
    original_sha256: str | None = None

    extracted_path: Path | None = None
    cleaned_path: Path | None = None
    normalized_path: Path | None = None
    canonical_path: Path | None = None

    extracted_sha256: str | None = None
    canonical_sha256: str | None = None

    title: str | None = None
    author: str | None = None
    language: str = "es"
    thematic_domain: str | None = None
    document_type: str | None = None
    corpus_version: str = "1.0"

    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0

    validation_passed: bool = False
    rejection_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        self.original_path = self.original_path.resolve()
        self.original_filename = self.original_path.name
        self.extension = self.original_path.suffix.lower()

    def change_status(self, status: DocumentStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, reason: str) -> None:
        self.validation_passed = False
        self.rejection_reason = reason
        self.change_status(DocumentStatus.REJECTED)