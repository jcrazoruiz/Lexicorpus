from __future__ import annotations

import bz2
import json
import re
import xml.etree.ElementTree as ET

from collections import Counter
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikipedia"
    / "wikipedia_snapshot_validation.json"
)

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikipedia_es"
    / "dump"
)

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikipedia"
)

OUTPUT_PATH = (
    REPORT_DIRECTORY
    / "wikipedia_segment_content_analysis.json"
)

MAXIMUM_SAMPLES = 20

PROGRESS_INTERVAL = 10_000


def format_elapsed(
    elapsed_seconds: float,
) -> str:
    total_seconds = int(
        elapsed_seconds
    )

    hours, remainder = divmod(
        total_seconds,
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


def load_validation() -> dict:
    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "No existe el archivo de validación:\n"
            f"{VALIDATION_PATH}"
        )

    return json.loads(
        VALIDATION_PATH.read_text(
            encoding="utf-8"
        )
    )


def get_first_segment(
    validation: dict,
) -> dict:
    segments = validation.get(
        "segments",
        []
    )

    if not segments:
        raise ValueError(
            "El archivo de validación "
            "no contiene segmentos."
        )

    return segments[0]


def local_name(
    tag: str,
) -> str:
    if "}" in tag:
        return tag.rsplit(
            "}",
            1,
        )[-1]

    return tag


def child_text(
    element: ET.Element,
    child_name: str,
) -> str | None:
    for child in element:
        if local_name(
            child.tag
        ) == child_name:
            return child.text

    return None


def find_revision_text(
    page_element: ET.Element,
) -> str:
    for child in page_element:

        if local_name(
            child.tag
        ) != "revision":
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
    page_element: ET.Element,
    wikitext: str,
) -> bool:
    for child in page_element:
        if local_name(
            child.tag
        ) == "redirect":
            return True

    return bool(
        re.match(
            r"^\s*#(?:REDIRECT|REDIRECCIÓN)",
            wikitext,
            flags=re.IGNORECASE,
        )
    )


def count_pattern(
    pattern: str,
    text: str,
) -> int:
    return len(
        re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )


def analyze_wikitext(
    text: str,
) -> dict:
    return {
        "characters": len(
            text
        ),
        "internal_links": count_pattern(
            r"\[\[",
            text,
        ),
        "external_links": count_pattern(
            r"\[(?:https?://)",
            text,
        ),
        "templates": count_pattern(
            r"\{\{",
            text,
        ),
        "references": count_pattern(
            r"<ref\b",
            text,
        ),
        "tables": count_pattern(
            r"\{\|",
            text,
        ),
        "headings": count_pattern(
            r"(?m)^={2,6}[^=\n].*?={2,6}\s*$",
            text,
        ),
        "categories": count_pattern(
            r"\[\[\s*Categor[ií]a\s*:",
            text,
        ),
        "files": count_pattern(
            r"\[\[\s*(?:Archivo|File|Imagen)\s*:",
            text,
        ),
        "html_comments": count_pattern(
            r"<!--",
            text,
        ),
        "math_tags": count_pattern(
            r"<math\b",
            text,
        ),
    }


def make_text_sample(
    text: str,
    maximum_length: int = 500,
) -> str:
    sample = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(sample) > maximum_length:
        sample = (
            sample[:maximum_length]
            + "..."
        )

    return sample


def main() -> int:
    print()

    print(
        "LexiCorpus v1.4 - "
        "Análisis completo del segmento Wikipedia"
    )

    print("=" * 88)

    try:
        validation = (
            load_validation()
        )

        segment = (
            get_first_segment(
                validation
            )
        )

    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"ERROR: {exc}"
        )

        return 1

    filename = (
        segment["filename"]
    )

    input_path = (
        RAW_DIRECTORY
        / filename
    )

    if not input_path.exists():
        print(
            "ERROR: no existe el segmento "
            "descargado:"
        )

        print(
            input_path
        )

        return 1

    print(
        "Snapshot             : "
        f"{validation['snapshot_date']}"
    )

    print(
        "Segmento             : "
        f"{filename}"
    )

    print(
        "Rango                : "
        f"p{segment['start_page']} "
        "-> "
        f"p{segment['end_page']}"
    )

    print(
        "Modo                 : "
        "segmento completo"
    )

    print("-" * 88)

    timer_start = (
        perf_counter()
    )

    pages_inspected = 0
    namespace_zero = 0
    redirects = 0
    empty_text = 0
    articles_analyzed = 0

    namespaces = Counter()

    total_characters = 0

    feature_totals = Counter()

    minimum_length: int | None = None
    maximum_length = 0

    samples: list[dict] = []

    try:
        with bz2.open(
            input_path,
            mode="rb",
        ) as compressed_file:

            context = ET.iterparse(
                compressed_file,
                events=("end",),
            )

            for _, element in context:

                if local_name(
                    element.tag
                ) != "page":
                    continue

                pages_inspected += 1

                title = (
                    child_text(
                        element,
                        "title",
                    )
                    or ""
                )

                namespace_text = (
                    child_text(
                        element,
                        "ns",
                    )
                    or ""
                )

                try:
                    namespace = int(
                        namespace_text
                    )

                except ValueError:
                    namespace = -1

                namespaces[
                    namespace
                ] += 1

                wikitext = (
                    find_revision_text(
                        element
                    )
                )

                if namespace == 0:
                    namespace_zero += 1

                    if is_redirect(
                        element,
                        wikitext,
                    ):
                        redirects += 1

                    elif not wikitext.strip():
                        empty_text += 1

                    else:
                        analysis = (
                            analyze_wikitext(
                                wikitext
                            )
                        )

                        articles_analyzed += 1

                        characters = (
                            analysis[
                                "characters"
                            ]
                        )

                        total_characters += (
                            characters
                        )

                        if (
                            minimum_length
                            is None
                            or characters
                            < minimum_length
                        ):
                            minimum_length = (
                                characters
                            )

                        if (
                            characters
                            > maximum_length
                        ):
                            maximum_length = (
                                characters
                            )

                        for (
                            key,
                            value,
                        ) in analysis.items():

                            if key == "characters":
                                continue

                            feature_totals[
                                key
                            ] += value

                        if (
                            len(samples)
                            < MAXIMUM_SAMPLES
                        ):
                            samples.append(
                                {
                                    "title": title,
                                    "characters": (
                                        characters
                                    ),
                                    "features": (
                                        analysis
                                    ),
                                    "sample": (
                                        make_text_sample(
                                            wikitext
                                        )
                                    ),
                                }
                            )

                element.clear()

                if (
                    pages_inspected
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    elapsed = (
                        perf_counter()
                        - timer_start
                    )

                    print(
                        "\r"
                        "Páginas: "
                        f"{pages_inspected:,}"
                        " | Namespace 0: "
                        f"{namespace_zero:,}"
                        " | Artículos: "
                        f"{articles_analyzed:,}"
                        " | Redirects: "
                        f"{redirects:,}"
                        " | Tiempo: "
                        f"{format_elapsed(elapsed)}",
                        end="",
                        flush=True,
                    )

    except (
        OSError,
        EOFError,
        ET.ParseError,
    ) as exc:
        print()

        print(
            "ERROR procesando segmento:"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    print()

    elapsed_seconds = (
        perf_counter()
        - timer_start
    )

    average_length = (
        total_characters
        / articles_analyzed
        if articles_analyzed
        else 0
    )

    print()
    print("=" * 88)

    print(
        "Resultado"
    )

    print("-" * 88)

    print(
        "Páginas inspeccionadas : "
        f"{pages_inspected:,}"
    )

    print(
        "Namespace 0            : "
        f"{namespace_zero:,}"
    )

    print(
        "Redirecciones          : "
        f"{redirects:,}"
    )

    print(
        "Sin texto              : "
        f"{empty_text:,}"
    )

    print(
        "Artículos analizados   : "
        f"{articles_analyzed:,}"
    )

    print(
        "Caracteres wikitext    : "
        f"{total_characters:,}"
    )

    print(
        "Longitud mínima        : "
        f"{minimum_length or 0:,}"
    )

    print(
        "Longitud promedio      : "
        f"{average_length:,.2f}"
    )

    print(
        "Longitud máxima        : "
        f"{maximum_length:,}"
    )

    print(
        "Tiempo                 : "
        f"{format_elapsed(elapsed_seconds)}"
    )

    print()
    print(
        "Namespaces encontrados"
    )

    print("-" * 88)

    for (
        namespace,
        count,
    ) in namespaces.most_common():

        print(
            f"{namespace:>5}: "
            f"{count:,}"
        )

    print()
    print(
        "Sintaxis MediaWiki detectada"
    )

    print("-" * 88)

    for (
        feature,
        count,
    ) in feature_totals.most_common():

        print(
            f"{feature:<25}: "
            f"{count:,}"
        )

    report = {
        "lexicorpus_version": "1.4",
        "source_code": "wikipedia_es",
        "snapshot_date": (
            validation[
                "snapshot_date"
            ]
        ),
        "segment": {
            "filename": filename,
            "start_page": (
                segment[
                    "start_page"
                ]
            ),
            "end_page": (
                segment[
                    "end_page"
                ]
            ),
        },
        "mode": "complete_segment",
        "statistics": {
            "pages_inspected": (
                pages_inspected
            ),
            "namespace_zero": (
                namespace_zero
            ),
            "redirects": (
                redirects
            ),
            "empty_text": (
                empty_text
            ),
            "articles_analyzed": (
                articles_analyzed
            ),
            "total_wikitext_characters": (
                total_characters
            ),
            "minimum_length": (
                minimum_length or 0
            ),
            "average_length": (
                average_length
            ),
            "maximum_length": (
                maximum_length
            ),
            "elapsed_seconds": (
                elapsed_seconds
            ),
        },
        "namespaces": dict(
            namespaces
        ),
        "mediawiki_features": dict(
            feature_totals
        ),
        "samples": samples,
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Reporte               : "
        f"{OUTPUT_PATH}"
    )

    print()
    print(
        "Análisis completo del segmento "
        "finalizado."
    )

    print(
        "No se modificó todavía "
        "el corpus."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )