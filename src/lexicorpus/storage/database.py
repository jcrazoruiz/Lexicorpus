import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS source (
    source_code TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    acquisition_method TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS document (
    document_id TEXT PRIMARY KEY,
    source_code TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    original_path TEXT NOT NULL,
    extension TEXT NOT NULL,
    original_sha256 TEXT NOT NULL,
    canonical_sha256 TEXT,
    status TEXT NOT NULL,
    title TEXT,
    author TEXT,
    language TEXT,
    thematic_domain TEXT,
    document_type TEXT,
    corpus_version TEXT,
    word_count INTEGER NOT NULL DEFAULT 0,
    character_count INTEGER NOT NULL DEFAULT 0,
    paragraph_count INTEGER NOT NULL DEFAULT 0,
    validation_passed INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    canonical_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_code)
        REFERENCES source(source_code)
);

CREATE UNIQUE INDEX IF NOT EXISTS
ux_document_original_sha256
ON document(original_sha256);

CREATE INDEX IF NOT EXISTS
ix_document_source_status
ON document(source_code, status);

CREATE TABLE IF NOT EXISTS lexicorpus_result (
    id_result INTEGER PRIMARY KEY AUTOINCREMENT,
    source_code TEXT NOT NULL,
    lexicorpus_size INTEGER NOT NULL,
    vocabulary_available INTEGER NOT NULL,
    selected_terms INTEGER NOT NULL,
    token_start INTEGER NOT NULL,
    token_end INTEGER NOT NULL,
    total_occurrences INTEGER NOT NULL,
    covered_occurrences INTEGER NOT NULL,
    outside_occurrences INTEGER NOT NULL,
    coverage_percentage REAL NOT NULL,
    csv_path TEXT NOT NULL,
    generated_at TEXT NOT NULL,

    UNIQUE (
        source_code,
        lexicorpus_size
    )
);

CREATE INDEX IF NOT EXISTS
ix_lexicorpus_result_source_size
ON lexicorpus_result(
    source_code,
    lexicorpus_size
);

CREATE TABLE IF NOT EXISTS lexicorpus_cross_coverage (
    id_result INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_source TEXT NOT NULL,
    evaluated_source TEXT NOT NULL,
    lexicorpus_size INTEGER NOT NULL,
    total_occurrences INTEGER NOT NULL,
    covered_occurrences INTEGER NOT NULL,
    outside_occurrences INTEGER NOT NULL,
    coverage_percentage REAL NOT NULL,
    generated_at TEXT NOT NULL,

    UNIQUE (
        origin_source,
        evaluated_source,
        lexicorpus_size
    )
);

CREATE INDEX IF NOT EXISTS
ix_lexicorpus_cross_coverage
ON lexicorpus_cross_coverage(
    origin_source,
    evaluated_source,
    lexicorpus_size
);
"""


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(SCHEMA)
            connection.commit()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection