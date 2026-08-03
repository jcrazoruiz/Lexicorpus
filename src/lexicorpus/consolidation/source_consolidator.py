from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SourceConsolidator:
    def __init__(
        self,
        project_root: Path,
        corpus_version: str,
    ) -> None:
        self.project_root = project_root.resolve()
        self.corpus_version = corpus_version

        self.version_directory = (
            self.project_root
            / "corpus"
            / "versions"
            / corpus_version
        )

    def consolidate(
        self,
        source_code: str,
        documents: list[sqlite3.Row],
    ) -> dict[str, Any]:
        if not documents:
            raise ValueError(
                "No existen documentos aprobados "
                "para consolidar."
            )

        documents_directory = (
            self.version_directory
            / "documents"
            / source_code
        )

        metadata_directory = (
            self.version_directory
            / "metadata"
        )

        if documents_directory.exists():
            shutil.rmtree(documents_directory)

        documents_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata_path = (
            metadata_directory
            / f"{source_code}.jsonl"
        )

        consolidated_documents: list[dict[str, Any]] = []

        with metadata_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as metadata_file:
            for row in documents:
                source_path = Path(row["canonical_path"])

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"No existe el archivo canónico: "
                        f"{source_path}"
                    )

                destination_name = (
                    f"{row['document_id']}.txt"
                )

                destination_path = (
                    documents_directory
                    / destination_name
                )

                shutil.copy2(
                    source_path,
                    destination_path,
                )

                metadata = {
                    "document_id": row["document_id"],
                    "source_code": row["source_code"],
                    "original_filename": (
                        row["original_filename"]
                    ),
                    "title": row["title"],
                    "author": row["author"],
                    "language": row["language"],
                    "thematic_domain": (
                        row["thematic_domain"]
                    ),
                    "document_type": (
                        row["document_type"]
                    ),
                    "lexicorpus_version": row["lexicorpus_version"],
                    "quality_profile": row["audit_profile"],
                    "quality_profile_version": row["profile_version"],
                    "corpus_version": (
                        self.corpus_version
                    ),
                    "word_count": row["word_count"],
                    "character_count": (
                        row["character_count"]
                    ),
                    "paragraph_count": (
                        row["paragraph_count"]
                    ),
                    "original_sha256": (
                        row["original_sha256"]
                    ),
                    "canonical_sha256": (
                        row["canonical_sha256"]
                    ),
                    "editorial_status": (
                        row["editorial_status"]
                    ),
                    "editorial_score": (
                        row["editorial_score"]
                    ),
                    "audited_at": row["audited_at"],
                    "corpus_path": str(
                        destination_path.relative_to(
                            self.version_directory
                        )
                    ),
                }

                metadata_file.write(
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                consolidated_documents.append(metadata)

        statistics = self._build_statistics(
            source_code,
            consolidated_documents,
        )

        statistics_path = (
            self.version_directory
            / f"statistics_{source_code}.json"
        )

        self._write_json(
            statistics_path,
            statistics,
        )

        profiles_used = sorted(
            {
                (
                    document["quality_profile"],
                    document["quality_profile_version"],
                )
                for document in consolidated_documents
            }
        )

        profiles_used = [
            {
                "code": code,
                "version": version,
            }
            for code, version in profiles_used
        ]

        source_manifest = {
            "corpus_name": "LexiCorpus",
            "corpus_version": self.corpus_version,
            "source_code": source_code,
            "generated_at": (
                datetime.now(timezone.utc).isoformat()
            ),
            "document_count": len(
                consolidated_documents
            ),
            "profiles_used": profiles_used,
            "metadata_file": str(
                metadata_path.relative_to(
                    self.version_directory
                )
            ),
            "statistics_file": str(
                statistics_path.relative_to(
                    self.version_directory
                )
            ),
            "documents_directory": str(
                documents_directory.relative_to(
                    self.version_directory
                )
            ),
            "documents": consolidated_documents,
        }

        source_manifest["manifest_sha256"] = (
            self._calculate_manifest_hash(
                source_manifest
            )
        )

        manifest_path = (
            self.version_directory
            / f"manifest_{source_code}.json"
        )

        self._write_json(
            manifest_path,
            source_manifest,
        )

        return {
            "manifest_path": manifest_path,
            "metadata_path": metadata_path,
            "statistics_path": statistics_path,
            "statistics": statistics,
        }

    @staticmethod
    def _build_statistics(
        source_code: str,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_words = sum(
            document["word_count"]
            for document in documents
        )

        total_characters = sum(
            document["character_count"]
            for document in documents
        )

        total_paragraphs = sum(
            document["paragraph_count"]
            for document in documents
        )

        average_score = (
            sum(
                document["editorial_score"]
                for document in documents
            )
            / len(documents)
        )

        by_document_type: dict[str, int] = {}

        for document in documents:
            document_type = (
                document["document_type"]
                or "sin_clasificar"
            )

            by_document_type[document_type] = (
                by_document_type.get(
                    document_type,
                    0,
                )
                + 1
            )

        return {
            "source_code": source_code,
            "document_count": len(documents),
            "total_words": total_words,
            "total_characters": total_characters,
            "total_paragraphs": total_paragraphs,
            "average_editorial_score": round(
                average_score,
                2,
            ),
            "document_types": by_document_type,
        }

    @staticmethod
    def _calculate_manifest_hash(
        manifest: dict[str, Any],
    ) -> str:
        serialized = json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _write_json(
        output_path: Path,
        content: dict[str, Any],
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                content,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )