from __future__ import annotations

import bz2
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


SNAPSHOT = "20260801"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DUMP_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikinews_es"
    / "dump"
    / (
        f"eswikinews-{SNAPSHOT}-"
        f"pages-articles-multistream.xml.bz2"
    )
)

REPORT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikinews_es"
    / "wikinews_content_analysis.json"
)


CATEGORY_PATTERN = re.compile(
    r"\[\[\s*Categor(?:ía|ia)\s*:\s*"
    r"([^|\]]+)",
    flags=re.IGNORECASE,
)

INTERNAL_LINK_PATTERN = re.compile(
    r"\[\[[^\]]+\]\]"
)

TEMPLATE_PATTERN = re.compile(
    r"\{\{.*?\}\}",
    flags=re.DOTALL,
)

REFERENCE_PATTERN = re.compile(
    r"<ref\b[^>]*>.*?</ref\s*>"
    r"|<ref\b[^>]*/\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)

HEADING_PATTERN = re.compile(
    r"^={2,6}.*?={2,6}\s*$",
    flags=re.MULTILINE,
)

EXTERNAL_LINK_PATTERN = re.compile(
    r"\[(?:https?|ftp)://[^\s\]]+"
)

FILE_PATTERN = re.compile(
    r"\[\[\s*(?:Archivo|File|Imagen|Image)\s*:",
    flags=re.IGNORECASE,
)

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    flags=re.DOTALL,
)

TABLE_PATTERN = re.compile(
    r"\{\|",
)

DATE_PATTERNS = [
    re.compile(
        r"\{\{\s*fecha\s*\|",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\{\{\s*date\s*\|",
        flags=re.IGNORECASE,
    ),
]


COUNTRY_NAMES = {
    "México",
    "España",
    "Argentina",
    "Colombia",
    "Chile",
    "Perú",
    "Venezuela",
    "Ecuador",
    "Bolivia",
    "Paraguay",
    "Uruguay",
    "Cuba",
    "Guatemala",
    "Honduras",
    "El Salvador",
    "Nicaragua",
    "Costa Rica",
    "Panamá",
    "República Dominicana",
    "Puerto Rico",
    "Estados Unidos",
    "Brasil",
}


def local_name(
    tag: str,
) -> str:

    return tag.rsplit(
        "}",
        1,
    )[-1]


def format_time(
    seconds: float,
) -> str:

    seconds = int(seconds)

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


def get_child_text(
    element: ET.Element,
    child_name: str,
) -> str | None:

    for child in element:

        if local_name(child.tag) == child_name:
            return child.text

    return None


def get_revision_text(
    page: ET.Element,
) -> str:

    for child in page:

        if local_name(child.tag) != "revision":
            continue

        for revision_child in child:

            if local_name(
                revision_child.tag
            ) == "text":

                return (
                    revision_child.text
                    or ""
                )

    return ""


def is_redirect(
    page: ET.Element,
    text: str,
) -> bool:

    for child in page:

        if local_name(child.tag) == "redirect":
            return True

    stripped = text.lstrip().lower()

    return (
        stripped.startswith("#redirect")
        or stripped.startswith("#redirección")
    )


def normalize_category(
    category: str,
) -> str:

    return " ".join(
        category.strip().split()
    )


def main() -> int:

    print(
        "LexiCorpus v1.5 - Análisis completo "
        "del dump Wikinoticias"
    )
    print("=" * 80)

    if not DUMP_PATH.exists():

        print(
            "ERROR: no existe el dump:"
        )
        print(DUMP_PATH)

        return 1

    print(
        f"Snapshot             : {SNAPSHOT}"
    )

    print(
        f"Archivo              : "
        f"{DUMP_PATH.name}"
    )

    print(
        f"Modo                 : dump completo"
    )

    print("-" * 80)

    start_time = time.monotonic()

    total_pages = 0
    namespace_zero = 0
    redirects = 0
    empty_text = 0
    candidate_articles = 0

    total_characters = 0

    minimum_length: int | None = None
    maximum_length = 0

    namespace_counter: Counter[int] = Counter()
    category_counter: Counter[str] = Counter()
    country_counter: Counter[str] = Counter()

    syntax_counter: Counter[str] = Counter()

    sample_titles: list[str] = []

    articles_with_categories = 0
    articles_without_categories = 0
    articles_with_date_template = 0

    with bz2.open(
        DUMP_PATH,
        "rb",
    ) as input_file:

        context = ET.iterparse(
            input_file,
            events=("end",),
        )

        for event, element in context:

            if local_name(
                element.tag
            ) != "page":
                continue

            total_pages += 1

            title = (
                get_child_text(
                    element,
                    "title",
                )
                or ""
            )

            namespace_text = (
                get_child_text(
                    element,
                    "ns",
                )
                or "-1"
            )

            try:
                namespace = int(
                    namespace_text
                )
            except ValueError:
                namespace = -1

            namespace_counter[
                namespace
            ] += 1

            if namespace != 0:

                element.clear()
                continue

            namespace_zero += 1

            text = get_revision_text(
                element
            )

            if not text:

                empty_text += 1
                element.clear()
                continue

            if is_redirect(
                element,
                text,
            ):

                redirects += 1
                element.clear()
                continue

            candidate_articles += 1

            length = len(text)

            total_characters += length

            if minimum_length is None:
                minimum_length = length
            else:
                minimum_length = min(
                    minimum_length,
                    length,
                )

            maximum_length = max(
                maximum_length,
                length,
            )

            if len(sample_titles) < 30:
                sample_titles.append(
                    title
                )

            categories = {
                normalize_category(
                    category
                )
                for category in (
                    CATEGORY_PATTERN.findall(
                        text
                    )
                )
                if category.strip()
            }

            if categories:

                articles_with_categories += 1

            else:

                articles_without_categories += 1

            category_counter.update(
                categories
            )

            # Primera aproximación para países.
            #
            # No utilizaremos todavía este resultado
            # como clasificación definitiva. Solo
            # queremos comprobar si las categorías
            # permiten identificar procedencia.
            lowered_categories = {
                category.casefold(): category
                for category in categories
            }

            for country in COUNTRY_NAMES:

                country_cf = country.casefold()

                matched = False

                for category_cf in (
                    lowered_categories
                ):

                    if (
                        category_cf == country_cf
                        or country_cf
                        in category_cf
                    ):
                        matched = True
                        break

                if matched:

                    country_counter[
                        country
                    ] += 1

            if any(
                pattern.search(text)
                for pattern in DATE_PATTERNS
            ):

                articles_with_date_template += 1

            syntax_counter[
                "internal_links"
            ] += len(
                INTERNAL_LINK_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "templates"
            ] += len(
                TEMPLATE_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "references"
            ] += len(
                REFERENCE_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "headings"
            ] += len(
                HEADING_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "external_links"
            ] += len(
                EXTERNAL_LINK_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "files"
            ] += len(
                FILE_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "html_comments"
            ] += len(
                HTML_COMMENT_PATTERN.findall(
                    text
                )
            )

            syntax_counter[
                "tables"
            ] += len(
                TABLE_PATTERN.findall(
                    text
                )
            )

            if (
                total_pages % 5000
                == 0
            ):

                elapsed = (
                    time.monotonic()
                    - start_time
                )

                print(
                    f"Páginas: "
                    f"{total_pages:,} | "
                    f"Namespace 0: "
                    f"{namespace_zero:,} | "
                    f"Artículos: "
                    f"{candidate_articles:,} | "
                    f"Tiempo: "
                    f"{format_time(elapsed)}"
                )

            element.clear()

    elapsed = (
        time.monotonic()
        - start_time
    )

    average_length = (
        total_characters
        / candidate_articles
        if candidate_articles
        else 0
    )

    report = {
        "lexicorpus_version": "1.5",
        "source_code": "wikinews_es",
        "source_name": (
            "Wikinoticias en español"
        ),
        "snapshot": SNAPSHOT,
        "dump_file": DUMP_PATH.name,

        "statistics": {
            "total_pages": total_pages,
            "namespace_zero": namespace_zero,
            "redirects": redirects,
            "empty_text": empty_text,
            "candidate_articles": (
                candidate_articles
            ),
            "total_wikitext_characters": (
                total_characters
            ),
            "minimum_length": (
                minimum_length
            ),
            "average_length": (
                average_length
            ),
            "maximum_length": (
                maximum_length
            ),
            "articles_with_categories": (
                articles_with_categories
            ),
            "articles_without_categories": (
                articles_without_categories
            ),
            "articles_with_date_template": (
                articles_with_date_template
            ),
        },

        "namespaces": dict(
            namespace_counter.most_common()
        ),

        "top_categories": [
            {
                "category": category,
                "articles": count,
            }
            for category, count
            in category_counter.most_common(
                100
            )
        ],

        "country_category_matches": dict(
            country_counter.most_common()
        ),

        "mediawiki_syntax": dict(
            syntax_counter
        ),

        "sample_titles": sample_titles,

        "elapsed_seconds": elapsed,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        json.dump(
            report,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 80)
    print("Resultado")
    print("-" * 80)

    print(
        f"Páginas inspeccionadas : "
        f"{total_pages:,}"
    )

    print(
        f"Namespace 0            : "
        f"{namespace_zero:,}"
    )

    print(
        f"Redirecciones          : "
        f"{redirects:,}"
    )

    print(
        f"Sin texto              : "
        f"{empty_text:,}"
    )

    print(
        f"Artículos candidatos   : "
        f"{candidate_articles:,}"
    )

    print(
        f"Caracteres wikitext    : "
        f"{total_characters:,}"
    )

    print(
        f"Longitud mínima        : "
        f"{minimum_length or 0:,}"
    )

    print(
        f"Longitud promedio      : "
        f"{average_length:,.2f}"
    )

    print(
        f"Longitud máxima        : "
        f"{maximum_length:,}"
    )

    print(
        f"Con categorías         : "
        f"{articles_with_categories:,}"
    )

    print(
        f"Sin categorías         : "
        f"{articles_without_categories:,}"
    )

    print(
        f"Con plantilla de fecha : "
        f"{articles_with_date_template:,}"
    )

    print(
        f"Tiempo                 : "
        f"{format_time(elapsed)}"
    )

    print()
    print("Namespaces encontrados")
    print("-" * 80)

    for namespace, count in (
        namespace_counter.most_common()
    ):

        print(
            f"{namespace:>5}: "
            f"{count:,}"
        )

    print()
    print("Top 30 categorías")
    print("-" * 80)

    for category, count in (
        category_counter.most_common(30)
    ):

        print(
            f"{count:>7,} | "
            f"{category}"
        )

    print()
    print(
        "Coincidencias preliminares por país"
    )
    print("-" * 80)

    if country_counter:

        for country, count in (
            country_counter.most_common()
        ):

            print(
                f"{country:<25} "
                f"{count:>7,}"
            )

    else:

        print(
            "No se detectaron coincidencias."
        )

    print()
    print("Sintaxis MediaWiki detectada")
    print("-" * 80)

    for name, count in (
        syntax_counter.most_common()
    ):

        print(
            f"{name:<25}: "
            f"{count:,}"
        )

    print()
    print("Muestra de títulos")
    print("-" * 80)

    for index, title in enumerate(
        sample_titles,
        start=1,
    ):

        print(
            f"{index:>3}. {title}"
        )

    print()
    print(
        f"Reporte               : "
        f"{REPORT_PATH}"
    )

    print()
    print(
        "Análisis completo del dump "
        "finalizado."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())