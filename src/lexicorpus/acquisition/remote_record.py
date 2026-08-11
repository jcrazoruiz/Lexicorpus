from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RemoteRecord:
    identifier: str
    source_code: str

    oai_datestamp: str | None = None

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    language: str | None = None
    resource_type: str | None = None
    publication_date: str | None = None

    identifiers: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    rights: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)

    article_url: str | None = None
    pdf_url: str | None = None
    local_path: str | None = None

    acquisition_status: str = "DISCOVERED"
    rejection_reason: str | None = None

    additional_metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)