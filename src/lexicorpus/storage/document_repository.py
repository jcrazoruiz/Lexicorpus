import sqlite3

from lexicorpus.domain.document import Document


class DocumentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def register_source(
        self,
        source_code: str,
        source_name: str,
        acquisition_method: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO source (
                source_code,
                source_name,
                acquisition_method,
                enabled
            )
            VALUES (?, ?, ?, 1)
            ON CONFLICT(source_code) DO UPDATE SET
                source_name = excluded.source_name,
                acquisition_method = excluded.acquisition_method,
                enabled = 1
            """,
            (
                source_code,
                source_name,
                acquisition_method,
            ),
        )
        self.connection.commit()

    def exists_by_original_hash(self, sha256: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM document
            WHERE original_sha256 = ?
            LIMIT 1
            """,
            (sha256,),
        ).fetchone()

        return row is not None

    def save(self, document: Document) -> None:
        self.connection.execute(
            """
            INSERT INTO document (
                document_id,
                source_code,
                original_filename,
                original_path,
                extension,
                original_sha256,
                canonical_sha256,
                status,
                title,
                author,
                language,
                thematic_domain,
                document_type,
                corpus_version,
                word_count,
                character_count,
                paragraph_count,
                validation_passed,
                rejection_reason,
                canonical_path,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(document_id) DO UPDATE SET
                canonical_sha256 = excluded.canonical_sha256,
                status = excluded.status,
                title = excluded.title,
                author = excluded.author,
                language = excluded.language,
                thematic_domain = excluded.thematic_domain,
                document_type = excluded.document_type,
                corpus_version = excluded.corpus_version,
                word_count = excluded.word_count,
                character_count = excluded.character_count,
                paragraph_count = excluded.paragraph_count,
                validation_passed = excluded.validation_passed,
                rejection_reason = excluded.rejection_reason,
                canonical_path = excluded.canonical_path,
                updated_at = excluded.updated_at
            """,
            (
                document.document_id,
                document.source_code,
                document.original_filename,
                str(document.original_path),
                document.extension,
                document.original_sha256,
                document.canonical_sha256,
                document.status.value,
                document.title,
                document.author,
                document.language,
                document.thematic_domain,
                document.document_type,
                document.corpus_version,
                document.word_count,
                document.character_count,
                document.paragraph_count,
                int(document.validation_passed),
                document.rejection_reason,
                (
                    str(document.canonical_path)
                    if document.canonical_path
                    else None
                ),
                document.created_at.isoformat(),
                document.updated_at.isoformat(),
            ),
        )
        self.connection.commit()