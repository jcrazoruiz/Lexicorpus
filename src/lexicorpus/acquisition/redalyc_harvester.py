from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexicorpus.acquisition.redalyc_client import (
    RedalycClient,
)


@dataclass(slots=True)
class RedalycHarvestStatistics:
    inspected_journals: int = 0
    inspected_issues: int = 0
    inspected_articles: int = 0

    accepted_metadata: int = 0
    downloaded: int = 0

    rejected_language: int = 0
    rejected_without_pdf: int = 0

    download_errors: int = 0
    skipped_existing: int = 0


class RedalycHarvester:
    SOURCE_CODE = "redalyc"

    def __init__(
        self,
        project_root: Path,
        maximum_documents_to_download: int | None = None,
    ) -> None:
        self.project_root = (
            project_root.resolve()
        )

        self.maximum_documents_to_download = (
            maximum_documents_to_download
        )

        self.client = RedalycClient()

        self.raw_directory = (
            self.project_root
            / "data"
            / "raw"
            / self.SOURCE_CODE
        )

        self.metadata_directory = (
            self.project_root
            / "metadata"
            / "acquisition"
            / self.SOURCE_CODE
        )

        self.raw_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.metadata_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.metadata_path = (
            self.metadata_directory
            / "redalyc_acquisition.jsonl"
        )

        self.acquired_article_ids = (
            self._load_acquired_article_ids()
        )

    @staticmethod
    def _clean(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        if text.lower() == "null":
            return None

        return text

    @classmethod
    def _is_spanish(
        cls,
        article: dict[str, Any],
    ) -> bool:
        language = cls._clean(
            article.get(
                "idiomaArticulo"
            )
        )

        if not language:
            return False

        normalized = (
            language
            .lower()
            .strip()
        )

        return normalized in {
            "es",
            "esp",
            "español",
            "spanish",
        }

    def _load_acquired_article_ids(
        self,
    ) -> set[str]:
        acquired: set[str] = set()

        if not self.metadata_path.exists():
            return acquired

        with self.metadata_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            for line in input_file:
                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(
                        line
                    )

                except json.JSONDecodeError:
                    continue

                if (
                    record.get(
                        "acquisition_status"
                    )
                    != "DOWNLOADED"
                ):
                    continue

                article_id = self._clean(
                    record.get(
                        "article_id"
                    )
                )

                if not article_id:
                    continue

                pdf_path = (
                    self.raw_directory
                    / f"{article_id}.pdf"
                )

                if pdf_path.exists():
                    acquired.add(
                        article_id
                    )

        return acquired

    def _save_metadata(
        self,
        record: dict[str, Any],
    ) -> None:
        with self.metadata_path.open(
            "a",
            encoding="utf-8",
        ) as output_file:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def _build_metadata_record(
        self,
        *,
        article: dict[str, Any],
        journal_id: str,
        issue_id: str,
        pdf_url: str | None,
        local_path: Path | None,
        acquisition_status: str,
        rejection_reason: str | None,
    ) -> dict[str, Any]:
        article_id = self._clean(
            article.get(
                "cveArticulo"
            )
        )

        authors = self._clean(
            article.get(
                "autores"
            )
        )

        author_list = []

        if authors:
            author_list = [
                item.strip()
                for item in authors.split(",")
                if item.strip()
            ]

        return {
            "identifier": (
                f"redalyc:{article_id}"
                if article_id
                else None
            ),
            "source_code": (
                self.SOURCE_CODE
            ),
            "article_id": article_id,
            "journal_id": journal_id,
            "issue_id": issue_id,
            "title": self._clean(
                article.get(
                    "titulo"
                )
            ),
            "authors": author_list,
            "language": self._clean(
                article.get(
                    "idiomaArticulo"
                )
            ),
            "publication_year": (
                self._clean(
                    article.get(
                        "anioArticulo"
                    )
                )
            ),
            "journal_name": (
                self._clean(
                    article.get(
                        "nomRevista"
                    )
                )
            ),
            "pages": self._clean(
                article.get(
                    "paginas"
                )
            ),
            "doi": self._clean(
                article.get(
                    "doiTitulo"
                )
            ),
            "abstract": self._clean(
                article.get(
                    "resumen"
                )
            ),
            "keywords": self._clean(
                article.get(
                    "palabras"
                )
            ),
            "article_url": (
                (
                    f"https://www.redalyc.org/"
                    f"articulo.oa?id={article_id}"
                )
                if article_id
                else None
            ),
            "pdf_url": pdf_url,
            "local_path": (
                str(local_path)
                if local_path
                else None
            ),
            "acquisition_status": (
                acquisition_status
            ),
            "rejection_reason": (
                rejection_reason
            ),
        }

    def _download_article(
        self,
        *,
        article_id: str,
        pdf_url: str,
    ) -> Path:
        output_path = (
            self.raw_directory
            / f"{article_id}.pdf"
        )

        if output_path.exists():
            return output_path

        pdf_content = (
            self.client.download_pdf(
                pdf_url
            )
        )

        output_path.write_bytes(
            pdf_content
        )

        return output_path

    def run(
        self,
    ) -> RedalycHarvestStatistics:
        statistics = (
            RedalycHarvestStatistics()
        )

        for journal in (
            self.client.iter_journals()
        ):
            statistics.inspected_journals += 1

            if not journal.issues:
                continue

            for issue in journal.issues:
                statistics.inspected_issues += 1

                try:
                    article_ids = (
                        self.client
                        .get_issue_article_ids(
                            journal_id=(
                                journal.journal_id
                            ),
                            issue_id=(
                                issue.issue_id
                            ),
                        )
                    )

                except Exception:
                    statistics.download_errors += 1
                    continue

                for article_id in article_ids:

                    # Si ya tenemos evidencia consistente
                    # de adquisición previa, lo saltamos.
                    if (
                        article_id
                        in self.acquired_article_ids
                    ):
                        statistics.skipped_existing += 1
                        continue

                    # El límite aplica solo a documentos
                    # nuevos descargados en esta ejecución.
                    if (
                        self.maximum_documents_to_download
                        is not None
                        and statistics.downloaded
                        >= self.maximum_documents_to_download
                    ):
                        return statistics

                    statistics.inspected_articles += 1

                    try:
                        article = (
                            self.client.get_article(
                                article_id
                            )
                        )

                    except Exception as exc:
                        statistics.download_errors += 1

                        self._save_metadata(
                            {
                                "identifier": (
                                    f"redalyc:{article_id}"
                                ),
                                "source_code": (
                                    self.SOURCE_CODE
                                ),
                                "article_id": (
                                    article_id
                                ),
                                "journal_id": (
                                    journal.journal_id
                                ),
                                "issue_id": (
                                    issue.issue_id
                                ),
                                "acquisition_status": (
                                    "ARTICLE_METADATA_ERROR"
                                ),
                                "rejection_reason": (
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                            }
                        )

                        continue

                    if not self._is_spanish(
                        article
                    ):
                        statistics.rejected_language += 1

                        self._save_metadata(
                            self._build_metadata_record(
                                article=article,
                                journal_id=(
                                    journal.journal_id
                                ),
                                issue_id=(
                                    issue.issue_id
                                ),
                                pdf_url=None,
                                local_path=None,
                                acquisition_status=(
                                    "REJECTED_LANGUAGE"
                                ),
                                rejection_reason=(
                                    "Idioma no aceptado: "
                                    f"{article.get('idiomaArticulo')}"
                                ),
                            )
                        )

                        continue

                    statistics.accepted_metadata += 1

                    try:
                        pdf_url = (
                            self.client.get_pdf_url(
                                article
                            )
                        )

                    except Exception as exc:
                        statistics.download_errors += 1

                        self._save_metadata(
                            self._build_metadata_record(
                                article=article,
                                journal_id=(
                                    journal.journal_id
                                ),
                                issue_id=(
                                    issue.issue_id
                                ),
                                pdf_url=None,
                                local_path=None,
                                acquisition_status=(
                                    "PDF_RESOLUTION_ERROR"
                                ),
                                rejection_reason=(
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                            )
                        )

                        continue

                    if not pdf_url:
                        statistics.rejected_without_pdf += 1

                        self._save_metadata(
                            self._build_metadata_record(
                                article=article,
                                journal_id=(
                                    journal.journal_id
                                ),
                                issue_id=(
                                    issue.issue_id
                                ),
                                pdf_url=None,
                                local_path=None,
                                acquisition_status=(
                                    "REJECTED_NO_PDF"
                                ),
                                rejection_reason=(
                                    "No fue posible resolver "
                                    "la URL del PDF."
                                ),
                            )
                        )

                        continue

                    try:
                        local_path = (
                            self._download_article(
                                article_id=(
                                    article_id
                                ),
                                pdf_url=pdf_url,
                            )
                        )

                    except Exception as exc:
                        statistics.download_errors += 1

                        self._save_metadata(
                            self._build_metadata_record(
                                article=article,
                                journal_id=(
                                    journal.journal_id
                                ),
                                issue_id=(
                                    issue.issue_id
                                ),
                                pdf_url=pdf_url,
                                local_path=None,
                                acquisition_status=(
                                    "DOWNLOAD_ERROR"
                                ),
                                rejection_reason=(
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                            )
                        )

                        continue

                    statistics.downloaded += 1

                    self.acquired_article_ids.add(
                        article_id
                    )

                    self._save_metadata(
                        self._build_metadata_record(
                            article=article,
                            journal_id=(
                                journal.journal_id
                            ),
                            issue_id=(
                                issue.issue_id
                            ),
                            pdf_url=pdf_url,
                            local_path=local_path,
                            acquisition_status=(
                                "DOWNLOADED"
                            ),
                            rejection_reason=None,
                        )
                    )

                    print(
                        f"Descargados nuevos: "
                        f"{statistics.downloaded:,}"
                        f" | "
                        f"Inspeccionados: "
                        f"{statistics.inspected_articles:,}"
                        f" | "
                        f"Existentes omitidos: "
                        f"{statistics.skipped_existing:,}"
                        f" | "
                        f"Idioma rechazado: "
                        f"{statistics.rejected_language:,}"
                    )

        return statistics