from __future__ import annotations

import bz2
import json
import sys
import xml.etree.ElementTree as ET

from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIRECTORY = (
    PROJECT_ROOT
    / "src"
)

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIRECTORY),
    )


from lexicorpus.acquisition.wikipedia_wikitext_cleaner import (
    WikipediaWikitextCleaner,
)


SNAPSHOT = "20260801"

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

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikinews_es"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "wikinews_cleaner_test.json"
)

MAXIMUM_ARTICLES = 100
MAXIMUM_SAMPLES = 15


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
    name: str,
) -> str | None:

    for child in element:

        if local_name(
            child.tag
        ) == name:

            return child.text

    return None


def revision_text(
    page: ET.Element,
) -> str:

    for child in page:

        if local_name(
            child.tag
        ) != "revision":
            continue

        for item in child:

            if local_name(
                item.tag
            ) == "text":

                return (
                    item.text
                    or ""
                )

    return ""


def is_redirect(
    page: ET.Element,
    text: str,
) -> bool:

    for child in page:

        if local_name(
            child.tag
        ) == "redirect":

            return True

    stripped = (
        text
        .lstrip()
        .casefold()
    )

    return (
        stripped.startswith(
            "#redirect"
        )
        or stripped.startswith(
            "#redirección"
        )
    )


def make_sample(
    text: str,
    maximum_length: int = 900,
) -> str:

    normalized = (
        " ".join(
            text.split()
        )
    )

    if len(normalized) > maximum_length:

        return (
            normalized[
                :maximum_length
            ]
            + "..."
        )

    return normalized


def main() -> int:

    print()
    print(
        "LexiCorpus v1.5 - "
        "Prueba del limpiador Wikinoticias"
    )
    print("=" * 80)

    if not DUMP_PATH.exists():

        print(
            "ERROR: no existe el dump:"
        )
        print(DUMP_PATH)

        return 1

    print(
        f"Snapshot             : "
        f"{SNAPSHOT}"
    )

    print(
        f"Máximo artículos     : "
        f"{MAXIMUM_ARTICLES:,}"
    )

    print("-" * 80)

    cleaner = (
        WikipediaWikitextCleaner()
    )

    analyzed = 0

    original_characters = 0
    cleaned_characters = 0

    minimum_reduction = 1.0
    maximum_reduction = 0.0

    empty_after_cleaning = 0

    samples: list[dict] = []

    timer_start = perf_counter()

    with bz2.open(
        DUMP_PATH,
        "rb",
    ) as input_file:

        context = ET.iterparse(
            input_file,
            events=("end",),
        )

        for _, element in context:

            if local_name(
                element.tag
            ) != "page":

                continue

            namespace = (
                child_text(
                    element,
                    "ns",
                )
                or ""
            )

            if namespace != "0":

                element.clear()
                continue

            title = (
                child_text(
                    element,
                    "title",
                )
                or ""
            ).strip()

            wikitext = (
                revision_text(
                    element
                )
            )

            if not wikitext.strip():

                element.clear()
                continue

            if is_redirect(
                element,
                wikitext,
            ):

                element.clear()
                continue

            result = cleaner.clean(
                wikitext
            )

            analyzed += 1

            original_characters += (
                result.original_characters
            )

            cleaned_characters += (
                result.cleaned_characters
            )

            minimum_reduction = min(
                minimum_reduction,
                result.reduction_ratio,
            )

            maximum_reduction = max(
                maximum_reduction,
                result.reduction_ratio,
            )

            if not result.text.strip():

                empty_after_cleaning += 1

            if (
                len(samples)
                < MAXIMUM_SAMPLES
            ):

                samples.append(
                    {
                        "title": title,
                        "original_characters": (
                            result.original_characters
                        ),
                        "cleaned_characters": (
                            result.cleaned_characters
                        ),
                        "reduction_ratio": (
                            result.reduction_ratio
                        ),
                        "before": (
                            make_sample(
                                wikitext
                            )
                        ),
                        "after": (
                            make_sample(
                                result.text
                            )
                        ),
                    }
                )

            element.clear()

            if (
                analyzed
                >= MAXIMUM_ARTICLES
            ):

                break

    elapsed = (
        perf_counter()
        - timer_start
    )

    removed_characters = (
        original_characters
        - cleaned_characters
    )

    global_reduction = (
        removed_characters
        / original_characters
        if original_characters
        else 0
    )

    print()
    print("Resultado")
    print("-" * 80)

    print(
        f"Artículos analizados      : "
        f"{analyzed:,}"
    )

    print(
        f"Caracteres originales     : "
        f"{original_characters:,}"
    )

    print(
        f"Caracteres limpios        : "
        f"{cleaned_characters:,}"
    )

    print(
        f"Caracteres eliminados     : "
        f"{removed_characters:,}"
    )

    print(
        f"Reducción global          : "
        f"{global_reduction:.2%}"
    )

    print(
        f"Reducción mínima          : "
        f"{minimum_reduction:.2%}"
    )

    print(
        f"Reducción máxima          : "
        f"{maximum_reduction:.2%}"
    )

    print(
        f"Vacíos tras limpieza      : "
        f"{empty_after_cleaning:,}"
    )

    print(
        f"Tiempo                    : "
        f"{elapsed:.2f} s"
    )

    print()
    print("=" * 80)
    print("Muestras")
    print("=" * 80)

    for index, sample in enumerate(
        samples,
        start=1,
    ):

        print()
        print(
            f"{index}. "
            f"{sample['title']}"
        )

        print(
            f"Original : "
            f"{sample['original_characters']:,}"
        )

        print(
            f"Limpio   : "
            f"{sample['cleaned_characters']:,}"
        )

        print(
            f"Reducción: "
            f"{sample['reduction_ratio']:.2%}"
        )

        print()
        print("ANTES:")
        print(
            sample["before"]
        )

        print()
        print("DESPUÉS:")
        print(
            sample["after"]
        )

        print("-" * 80)

    report = {
        "lexicorpus_version": "1.5",
        "source_code": "wikinews_es",
        "snapshot": SNAPSHOT,
        "articles_analyzed": analyzed,
        "original_characters": (
            original_characters
        ),
        "cleaned_characters": (
            cleaned_characters
        ),
        "removed_characters": (
            removed_characters
        ),
        "global_reduction_ratio": (
            global_reduction
        ),
        "minimum_reduction_ratio": (
            minimum_reduction
        ),
        "maximum_reduction_ratio": (
            maximum_reduction
        ),
        "empty_after_cleaning": (
            empty_after_cleaning
        ),
        "elapsed_seconds": elapsed,
        "samples": samples,
    }

    REPORT_DIRECTORY.mkdir(
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
    print(
        f"Reporte                   : "
        f"{REPORT_PATH}"
    )

    print()
    print(
        "Prueba finalizada. "
        "No se modificó el corpus."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())