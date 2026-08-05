from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EDITORIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS editorial_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    lexicorpus_version TEXT NOT NULL,
    audit_profile TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    document_type TEXT,
    editorial_status TEXT NOT NULL,
    editorial_score INTEGER NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    anomaly_report_json TEXT NOT NULL,
    validation_result_json TEXT NOT NULL,
    report_path TEXT,
    audited_at TEXT NOT NULL,

    FOREIGN KEY (document_id)
        REFERENCES document(document_id)
);
"""

EDITORIAL_INDEXES = """
CREATE INDEX IF NOT EXISTS
ix_editorial_audit_document
ON editorial_audit(document_id);

CREATE INDEX IF NOT EXISTS
ix_editorial_audit_version
ON editorial_audit(lexicorpus_version);

CREATE INDEX IF NOT EXISTS
ix_editorial_audit_profile
ON editorial_audit(audit_profile);
"""

class EditorialRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.executescript(
            EDITORIAL_SCHEMA
        )

        self._ensure_column(
            "lexicorpus_version",
            "TEXT NOT NULL DEFAULT '1.0'",
        )

        self._ensure_column(
            "profile_version",
            "TEXT NOT NULL DEFAULT '1.0'",
        )

        self._ensure_column(
            "document_type",
            "TEXT",
        )

        self.connection.executescript(
            EDITORIAL_INDEXES
        )

        self.connection.commit()

    def save_audit(
        self,
        document_id: str,
        lexicorpus_version: str,
        audit_profile: str,
        profile_version: str,
        document_type: str | None,
        editorial_status: str,
        editorial_score: int,
        approved: bool,
        anomaly_report: dict[str, Any],
        validation_result: dict[str, Any],
        report_path: Path,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO editorial_audit (
                document_id,
                lexicorpus_version,
                audit_profile,
                profile_version,
                document_type,
                editorial_status,
                editorial_score,
                approved,
                anomaly_report_json,
                validation_result_json,
                report_path,
                audited_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                lexicorpus_version,
                audit_profile,
                profile_version,
                document_type,
                editorial_status,
                editorial_score,
                int(approved),
                json.dumps(
                    anomaly_report,
                    ensure_ascii=False,
                ),
                json.dumps(
                    validation_result,
                    ensure_ascii=False,
                ),
                str(report_path),
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        self.connection.commit()

    def get_latest_approved_documents(
        self,
        source_code: str,
        lexicorpus_version: str,
    ) -> list[sqlite3.Row]:
        return self.connection.execute(
            """
            WITH LatestAudit AS (
                SELECT
                    ea.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY ea.document_id
                        ORDER BY ea.audit_id DESC
                    ) AS rn
                FROM editorial_audit ea
                WHERE ea.lexicorpus_version = ?
            )
            SELECT
                d.document_id,
                d.source_code,
                d.original_filename,
                d.original_sha256,
                d.canonical_sha256,
                d.title,
                d.author,
                d.language,
                d.thematic_domain,
                d.document_type,
                d.corpus_version,
                d.word_count,
                d.character_count,
                d.paragraph_count,
                d.canonical_path,
                la.lexicorpus_version,
                la.audit_profile,
                la.profile_version,
                la.editorial_status,
                la.editorial_score,
                la.audited_at
            FROM document d
            INNER JOIN LatestAudit la
                ON la.document_id = d.document_id
            AND la.rn = 1
            WHERE d.source_code = ?
            AND d.status = 'CANONICAL'
            AND la.approved = 1
            ORDER BY d.title
            """,
            (
                lexicorpus_version,
                source_code,
            ),
        ).fetchall()

    def _ensure_column(
        self,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = self.connection.execute(
            "PRAGMA table_info(editorial_audit)"
        ).fetchall()

        existing_columns = {
            column[1]
            for column in columns
        }

        if column_name in existing_columns:
            return

        self.connection.execute(
            f"""
            ALTER TABLE editorial_audit
            ADD COLUMN {column_name}
            {column_definition}
            """
        )