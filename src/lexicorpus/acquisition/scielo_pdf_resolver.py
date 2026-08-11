from __future__ import annotations

from urllib.parse import urljoin

import requests

from lexicorpus.acquisition.scielo_metadata_parser import (
    ScieloMetadataParser,
)


class ScieloPdfResolverError(RuntimeError):
    """Error al resolver la URL directa de un PDF de SciELO."""


class ScieloPdfResolver:
    def __init__(
        self,
        timeout_seconds: int = 45,
    ) -> None:
        self.timeout_seconds = timeout_seconds

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "LexiCorpus/1.1 "
                    "(academic corpus research)"
                ),
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "*/*;q=0.8"
                ),
            }
        )

    def resolve(
        self,
        candidate_url: str,
    ) -> str:
        response = self.session.get(
            candidate_url,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        # Algunas colecciones podrían entregar el PDF directamente.
        if "application/pdf" in content_type:
            return response.url

        pdf_url = (
            ScieloMetadataParser
            .extract_pdf_url_from_html(
                response.text
            )
        )

        if not pdf_url:
            raise ScieloPdfResolverError(
                "No se encontró una URL PDF directa "
                "en la página intermedia de SciELO."
            )

        return urljoin(
            response.url,
            pdf_url,
        )