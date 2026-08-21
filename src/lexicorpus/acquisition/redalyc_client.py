from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True, slots=True)
class RedalycIssue:
    year: str
    volume: str
    issue_label: str
    issue_type: str
    issue_id: str
    jats_status: str


@dataclass(frozen=True, slots=True)
class RedalycJournal:
    journal_id: str
    name: str
    country: str | None
    thematic_area: str | None
    language: str | None
    issues: tuple[RedalycIssue, ...]


class RedalycClient:
    BASE_URL = "https://www.redalyc.org"

    JOURNAL_SEARCH_EXPRESSION = "[aA TO Zz]"
    DEFAULT_PAGE_SIZE = 15
    DEFAULT_ORDER_BY = "Nombre-0"

    REQUEST_TIMEOUT = 30

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "LexiCorpus/1.3"
                )
            }
        )

    def get_journals_page(
        self,
        page: int = 1,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError(
                "page debe ser mayor o igual a 1."
            )

        if page_size is None:
            page_size = self.DEFAULT_PAGE_SIZE

        if page_size < 1:
            raise ValueError(
                "page_size debe ser mayor o igual a 1."
            )

        url = (
            f"{self.BASE_URL}/service/r2020/"
            f"getJournals/"
            f"{self.JOURNAL_SEARCH_EXPRESSION}/"
            f"{page}/"
            f"{page_size}/"
            f"1/"
            f"{self.DEFAULT_ORDER_BY}"
        )

        response = self.session.get(
            url,
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "La respuesta del catálogo "
                "de RedALyC no es un objeto JSON."
            )

        return data

    def iter_journals(
        self,
        page_size: int | None = None,
    ):
        if page_size is None:
            page_size = self.DEFAULT_PAGE_SIZE

        page = 1
        yielded = 0
        total_results: int | None = None

        while True:
            data = self.get_journals_page(
                page=page,
                page_size=page_size,
            )

            if total_results is None:
                total_results = int(
                    data.get(
                        "totalResultados",
                        0,
                    )
                    or 0
                )

            results = (
                data.get("resultados")
                or []
            )

            if not results:
                break

            for record in results:
                journal = (
                    self._parse_journal(
                        record
                    )
                )

                if journal is None:
                    continue

                yield journal
                yielded += 1

            if (
                total_results
                and yielded >= total_results
            ):
                break

            if len(results) < page_size:
                break

            page += 1

    def get_issue_article_ids(
        self,
        journal_id: str,
        issue_id: str,
    ) -> list[str]:
        url = (
            f"{self.BASE_URL}/toc.oa"
        )

        response = self.session.get(
            url,
            params={
                "id": journal_id,
                "numero": issue_id,
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        article_ids: set[str] = set()

        for anchor in soup.find_all(
            "a",
            href=True,
        ):
            href = (
                anchor.get("href")
                or ""
            )

            match = re.search(
                r"articulo\.oa\?id=(\d+)",
                href,
                flags=re.IGNORECASE,
            )

            if match:
                article_ids.add(
                    match.group(1)
                )

        return sorted(
            article_ids
        )

    def get_article(
        self,
        article_id: str,
    ) -> dict[str, Any]:
        url = (
            f"{self.BASE_URL}/service/r2020/"
            f"getArticleByID/{article_id}/"
        )

        response = self.session.get(
            url,
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "La respuesta del artículo "
                "no es un objeto JSON."
            )

        return data

    def get_pdf_url(
        self,
        article: dict[str, Any],
    ) -> str | None:
        article_id = self._clean(
            article.get("cveArticulo")
        )

        journal_id = self._clean(
            article.get("cveRevista")
        )

        if not article_id:
            return None

        # La página pública del artículo expone
        # citation_pdf_url. Es preferible utilizar
        # esa URL antes que inferir rutas internas.
        article_page_url = (
            f"{self.BASE_URL}/articulo.oa"
        )

        response = self.session.get(
            article_page_url,
            params={
                "id": article_id,
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        metadata = soup.find(
            "meta",
            attrs={
                "name": "citation_pdf_url",
            },
        )

        if metadata is not None:
            content = self._clean(
                metadata.get("content")
            )

            if content:
                return content

        # Fallback para el patrón convencional
        # que ya observamos en RedALyC.
        if journal_id:
            return (
                f"{self.BASE_URL}/pdf/"
                f"{journal_id}/"
                f"{article_id}.pdf"
            )

        return None

    def download_pdf(
        self,
        pdf_url: str,
    ) -> bytes:
        response = self.session.get(
            pdf_url,
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
            .lower()
        )

        if (
            "application/pdf"
            not in content_type
        ):
            raise ValueError(
                "La respuesta obtenida no "
                "corresponde a un PDF. "
                f"Content-Type={content_type!r}"
            )

        if not response.content:
            raise ValueError(
                "El PDF descargado está vacío."
            )

        return response.content

    @classmethod
    def _parse_journal(
        cls,
        record: dict[str, Any],
    ) -> RedalycJournal | None:
        journal_id = cls._clean(
            record.get("clave")
        )

        if not journal_id:
            return None

        issues = cls._parse_issues(
            cls._clean(
                record.get(
                    "aniosNumeros"
                )
            )
        )

        return RedalycJournal(
            journal_id=journal_id,
            name=(
                cls._clean(
                    record.get("nombre")
                )
                or journal_id
            ),
            country=cls._clean(
                record.get("pais")
            ),
            thematic_area=cls._clean(
                record.get("nomAre")
            ),
            language=cls._clean(
                record.get("abrentidi")
            ),
            issues=tuple(issues),
        )

    @classmethod
    def _parse_issues(
        cls,
        value: str | None,
    ) -> list[RedalycIssue]:
        if not value:
            return []

        issues: list[RedalycIssue] = []

        year_blocks = value.split(
            ">>>"
        )

        for year_block in year_blocks:
            year_block = (
                year_block.strip()
            )

            if not year_block:
                continue

            parts = year_block.split(
                "-"
            )

            if len(parts) < 6:
                continue

            year = parts[0].strip()

            values = parts[1:]

            # Cada número está representado por:
            #
            # volumen
            # número
            # tipo
            # clave
            # jats
            #
            # Es decir, bloques de cinco campos.
            for index in range(
                0,
                len(values),
                5,
            ):
                group = values[
                    index:index + 5
                ]

                if len(group) != 5:
                    continue

                (
                    volume,
                    issue_label,
                    issue_type,
                    issue_id,
                    jats_status,
                ) = (
                    item.strip()
                    for item in group
                )

                if not issue_id:
                    continue

                issues.append(
                    RedalycIssue(
                        year=year,
                        volume=volume,
                        issue_label=(
                            issue_label
                        ),
                        issue_type=(
                            issue_type
                        ),
                        issue_id=issue_id,
                        jats_status=(
                            jats_status
                        ),
                    )
                )

        return issues

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