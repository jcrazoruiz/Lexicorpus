from __future__ import annotations

import bz2
import json
import re
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.parse import quote

from lexicorpus.acquisition.wikipedia_wikitext_cleaner import (
    WikipediaWikitextCleaner,
)


CATEGORY_PATTERN = re.compile(
    r"\[\[\s*Categor(?:ía|ia)\s*:\s*([^|\]]+)",
    flags=re.IGNORECASE,
)


# Primera taxonomía geográfica controlada.
# Representa ámbito geográfico de la noticia,
# NO variante lingüística del documento.
GEOGRAPHIC_CATEGORIES = {
    "Argentina": "AR",
    "Bolivia": "BO",
    "Brasil": "BR",
    "Chile": "CL",
    "Colombia": "CO",
    "Costa Rica": "CR",
    "Cuba": "CU",
    "Ecuador": "EC",
    "El Salvador": "SV",
    "España": "ES",
    "Estados Unidos": "US",
    "Guatemala": "GT",
    "Honduras": "HN",
    "México": "MX",
    "Nicaragua": "NI",
    "Panamá": "PA",
    "Paraguay": "PY",
    "Perú": "PE",
    "Puerto Rico": "PR",
    "República Dominicana": "DO",
    "Uruguay": "UY",
    "Venezuela": "VE",
}


@dataclass(slots=True)
class WikinewsExtractionResult:
    pages_inspected: int = 0
    namespace_zero: int = 0
    redirects: int = 0
    empty_wikitext: int = 0
    cleaned_empty: int = 0
    extracted: int = 0
    with_categories: int = 0
    with_geographic_scope: int = 0
    with_publication_date: int = 0
    errors: int = 0


class WikinewsDumpExtractor:

    def __init__(
        self,
        cleaner: WikipediaWikitextCleaner,
        output_directory: Path,
        metadata_path: Path,
        snapshot_date: str,
        source_code: str = "wikinews_es",
    ) -> None:

        self.cleaner = cleaner
        self.output_directory = output_directory
        self.metadata_path = metadata_path
        self.snapshot_date = snapshot_date
        self.source_code = source_code

    @staticmethod
    def _local_name(
        tag: str,
    ) -> str:

        if "}" in tag:
            return tag.rsplit(
                "}",
                1,
            )[-1]

        return tag

    @classmethod
    def _child_text(
        cls,
        element: ET.Element,
        name: str,
    ) -> str | None:

        for child in element:

            if cls._local_name(
                child.tag
            ) == name:

                return child.text

        return None

    @classmethod
    def _revision_text(
        cls,
        page: ET.Element,
    ) -> str:

        for child in page:

            if cls._local_name(
                child.tag
            ) != "revision":
                continue

            for item in child:

                if cls._local_name(
                    item.tag
                ) == "text":

                    return (
                        item.text
                        or ""
                    )

        return ""

    @classmethod
    def _is_redirect(
        cls,
        page: ET.Element,
        text: str,
    ) -> bool:

        for child in page:

            if cls._local_name(
                child.tag
            ) == "redirect":

                return True

        normalized = (
            text
            .lstrip()
            .casefold()
        )

        return (
            normalized.startswith(
                "#redirect"
            )
            or normalized.startswith(
                "#redirección"
            )
        )

    @classmethod
    def _page_id(
        cls,
        page: ET.Element,
    ) -> str:

        for child in page:

            if cls._local_name(
                child.tag
            ) == "id":

                return (
                    child.text
                    or ""
                ).strip()

        return ""

    @staticmethod
    def _build_source_url(
        title: str,
    ) -> str:

        normalized_title = quote(
            title.replace(
                " ",
                "_",
            ),
            safe="()_-'",
        )

        return (
            "https://es.wikinews.org/wiki/"
            + normalized_title
        )

    @staticmethod
    def _extract_categories(
        wikitext: str,
    ) -> list[str]:

        categories = {
            " ".join(
                category
                .strip()
                .split()
            )
            for category
            in CATEGORY_PATTERN.findall(
                wikitext
            )
            if category.strip()
        }

        return sorted(
            categories,
            key=str.casefold,
        )

    @staticmethod
    def _extract_geographic_scope(
        categories: list[str],
    ) -> list[str]:

        normalized_categories = {
            category.casefold()
            for category in categories
        }

        geographic_scope = []

        for (
            category_name,
            country_code,
        ) in GEOGRAPHIC_CATEGORIES.items():

            category_cf = (
                category_name.casefold()
            )

            if category_cf in (
                normalized_categories
            ):
                geographic_scope.append(
                    country_code
                )

        return sorted(
            geographic_scope
        )

    @staticmethod
    def _extract_publication_date(
        wikitext: str,
    ) -> str | None:
        """
        Busca las formas más comunes utilizadas
        históricamente por Wikinoticias.

        Devuelve YYYY-MM-DD cuando puede obtener
        una fecha inequívoca. En caso contrario,
        devuelve None.
        """

        patterns = (
            # {{fecha|31|enero|2005}}
            re.compile(
                r"\{\{\s*fecha\s*"
                r"\|\s*(\d{1,2})\s*"
                r"\|\s*([^\|\}]+?)\s*"
                r"\|\s*(\d{4})\s*"
                r"\}\}",
                flags=re.IGNORECASE,
            ),

            # {{fecha|31 de enero de 2005}}
            re.compile(
                r"\{\{\s*fecha\s*"
                r"\|\s*(\d{1,2})"
                r"\s+de\s+"
                r"([^\|\}]+?)"
                r"\s+de\s+"
                r"(\d{4})\s*"
                r"\}\}",
                flags=re.IGNORECASE,
            ),
        )

        match = None

        for pattern in patterns:

            match = pattern.search(
                wikitext
            )

            if match:
                break

        if not match:
            return None

        day_text = match.group(1)
        month_text = (
            match.group(2)
            .strip()
            .casefold()
        )
        year_text = match.group(3)

        month_text = (
            month_text
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        months = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "setiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }

        month = months.get(
            month_text
        )

        if month is None:
            return None

        try:
            day = int(
                day_text
            )

            year = int(
                year_text
            )

        except ValueError:
            return None

        if not (
            1 <= day <= 31
        ):
            return None

        return (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    def extract(
        self,
        dump_path: Path,
    ) -> WikinewsExtractionResult:

        result = (
            WikinewsExtractionResult()
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.metadata_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dump_filename = (
            dump_path.name
        )

        timer_start = (
            perf_counter()
        )

        with (
            bz2.open(
                dump_path,
                "rb",
            ) as input_file,
            self.metadata_path.open(
                "a",
                encoding="utf-8",
            ) as metadata_file,
        ):

            context = ET.iterparse(
                input_file,
                events=("end",),
            )

            for _, element in context:

                if self._local_name(
                    element.tag
                ) != "page":
                    continue

                result.pages_inspected += 1

                namespace = (
                    self._child_text(
                        element,
                        "ns",
                    )
                    or ""
                )

                if namespace != "0":
                    element.clear()
                    continue

                result.namespace_zero += 1

                wikitext = (
                    self._revision_text(
                        element
                    )
                )

                if self._is_redirect(
                    element,
                    wikitext,
                ):

                    result.redirects += 1
                    element.clear()
                    continue

                if not wikitext.strip():

                    result.empty_wikitext += 1
                    element.clear()
                    continue

                page_id = (
                    self._page_id(
                        element
                    )
                )

                title = (
                    self._child_text(
                        element,
                        "title",
                    )
                    or ""
                ).strip()

                if not page_id:

                    result.errors += 1
                    element.clear()
                    continue

                try:

                    cleaning_result = (
                        self.cleaner.clean(
                            wikitext
                        )
                    )

                except Exception:

                    result.errors += 1
                    element.clear()
                    continue

                cleaned_text = (
                    cleaning_result.text
                )

                if not cleaned_text.strip():

                    result.cleaned_empty += 1
                    element.clear()
                    continue

                categories = (
                    self._extract_categories(
                        wikitext
                    )
                )

                geographic_scope = (
                    self._extract_geographic_scope(
                        categories
                    )
                )

                publication_date = (
                    self._extract_publication_date(
                        wikitext
                    )
                )

                if categories:
                    result.with_categories += 1

                if geographic_scope:
                    result.with_geographic_scope += 1

                if publication_date:
                    result.with_publication_date += 1

                output_path = (
                    self.output_directory
                    / f"{page_id}.txt"
                )

                output_path.write_text(
                    cleaned_text + "\n",
                    encoding="utf-8",
                )

                metadata = {
                    "identifier": (
                        f"{self.source_code}:"
                        f"{page_id}"
                    ),
                    "source_code": (
                        self.source_code
                    ),
                    "page_id": (
                        page_id
                    ),
                    "title": (
                        title
                    ),
                    "snapshot_date": (
                        self.snapshot_date
                    ),
                    "dump_file": (
                        dump_filename
                    ),
                    "source_url": (
                        self._build_source_url(
                            title
                        )
                    ),

                    # Metadatos específicos
                    # de Wikinoticias.
                    "media_type": "prensa",
                    "publication_date": (
                        publication_date
                    ),
                    "categories": (
                        categories
                    ),
                    "geographic_scope": (
                        geographic_scope
                    ),

                    # Métricas de adquisición.
                    "original_wikitext_characters": (
                        cleaning_result
                        .original_characters
                    ),
                    "cleaned_characters": (
                        cleaning_result
                        .cleaned_characters
                    ),
                    "reduction_ratio": (
                        cleaning_result
                        .reduction_ratio
                    ),

                    "local_path": str(
                        output_path
                    ),
                    "acquisition_status": (
                        "EXTRACTED"
                    ),
                }

                metadata_file.write(
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                result.extracted += 1

                element.clear()

                if (
                    result.pages_inspected
                    % 5_000
                    == 0
                ):

                    elapsed = (
                        perf_counter()
                        - timer_start
                    )

                    print(
                        "\r"
                        "Páginas: "
                        f"{result.pages_inspected:,}"
                        " | Namespace 0: "
                        f"{result.namespace_zero:,}"
                        " | Extraídos: "
                        f"{result.extracted:,}"
                        " | Redirects: "
                        f"{result.redirects:,}"
                        " | Fecha: "
                        f"{result.with_publication_date:,}"
                        " | Geografía: "
                        f"{result.with_geographic_scope:,}"
                        " | Errores: "
                        f"{result.errors:,}"
                        " | Tiempo: "
                        f"{elapsed:,.1f}s",
                        end="",
                        flush=True,
                    )

        print()

        return result