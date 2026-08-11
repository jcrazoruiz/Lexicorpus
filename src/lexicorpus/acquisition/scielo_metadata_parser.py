from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from lexicorpus.acquisition.oai_pmh_client import NAMESPACES
from lexicorpus.acquisition.remote_record import RemoteRecord


PDF_EXTENSION_PATTERN = re.compile(
    r"\.pdf(?:$|\?)",
    flags=re.IGNORECASE,
)


class ScieloMetadataParser:
    def parse(
        self,
        record_element: ET.Element,
    ) -> RemoteRecord | None:
        header = record_element.find(
            "oai:header",
            NAMESPACES,
        )

        if header is None:
            return None

        if header.attrib.get("status") == "deleted":
            return None

        identifier_element = header.find(
            "oai:identifier",
            NAMESPACES,
        )

        datestamp_element = header.find(
            "oai:datestamp",
            NAMESPACES,
        )

        if (
            identifier_element is None
            or not identifier_element.text
        ):
            return None

        metadata = record_element.find(
            "oai:metadata",
            NAMESPACES,
        )

        if metadata is None:
            return None

        dc = metadata.find(
            "oai_dc:dc",
            NAMESPACES,
        )

        if dc is None:
            return None

        titles = self._values(dc, "dc:title")
        creators = self._values(dc, "dc:creator")
        languages = self._values(dc, "dc:language")
        types = self._values(dc, "dc:type")
        dates = self._values(dc, "dc:date")
        identifiers = self._values(dc, "dc:identifier")
        subjects = self._values(dc, "dc:subject")
        rights = self._values(dc, "dc:rights")
        descriptions = self._values(
            dc,
            "dc:description",
        )

        article_url = self._find_article_url(
            identifiers
        )

        pdf_url = self._find_pdf_url(
            identifiers
        )

        if pdf_url is None and article_url:
            pdf_url = self._build_pdf_candidate(
                article_url
            )

        return RemoteRecord(
            identifier=identifier_element.text.strip(),
            source_code="scielo",
            oai_datestamp=(
                datestamp_element.text.strip()
                if (
                    datestamp_element is not None
                    and datestamp_element.text
                )
                else None
            ),
            title=titles[0] if titles else None,
            authors=creators,
            language=(
                languages[0].strip().lower()
                if languages
                else None
            ),
            resource_type=(
                types[0].strip().lower()
                if types
                else None
            ),
            publication_date=(
                dates[0]
                if dates
                else None
            ),
            identifiers=identifiers,
            subjects=subjects,
            rights=rights,
            descriptions=descriptions,
            article_url=article_url,
            pdf_url=pdf_url,
        )

    @staticmethod
    def _values(
        dc_element: ET.Element,
        path: str,
    ) -> list[str]:
        values: list[str] = []

        for element in dc_element.findall(
            path,
            NAMESPACES,
        ):
            if element.text and element.text.strip():
                values.append(element.text.strip())

        return values

    @staticmethod
    def _find_pdf_url(
        identifiers: list[str],
    ) -> str | None:
        for value in identifiers:
            normalized = value.strip()

            if not normalized.startswith(
                ("http://", "https://")
            ):
                continue

            if (
                PDF_EXTENSION_PATTERN.search(normalized)
                or "script=sci_pdf" in normalized
            ):
                return normalized

        return None

    @staticmethod
    def _find_article_url(
        identifiers: list[str],
    ) -> str | None:
        candidates = [
            value.strip()
            for value in identifiers
            if value.strip().startswith(
                ("http://", "https://")
            )
        ]

        for candidate in candidates:
            if "script=sci_arttext" in candidate:
                return candidate

        for candidate in candidates:
            if "scielo" in candidate.lower():
                return candidate

        return candidates[0] if candidates else None

    @staticmethod
    def _build_pdf_candidate(
        article_url: str,
    ) -> str | None:
        parsed = urlparse(article_url)
        query = parse_qs(parsed.query)

        pid = query.get("pid", [None])[0]

        if not pid:
            return None

        query["script"] = ["sci_pdf"]

        return urlunparse(
            parsed._replace(
                query=urlencode(
                    {
                        key: values[0]
                        for key, values in query.items()
                        if values
                    }
                )
            )
        )

    @staticmethod
    def extract_pdf_url_from_html(
        html: str,
    ) -> str | None:
        match = re.search(
            r'https?://[^"\'\s<>]+\.pdf',
            html,
            flags=re.IGNORECASE,
        )

        if match is None:
            return None

        return match.group(0)