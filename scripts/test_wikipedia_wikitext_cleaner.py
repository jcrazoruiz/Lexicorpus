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
    / "wikipedia_cleaner_test.json"
)

MAXIMUM_ARTICLES = 100
MAXIMUM_SAMPLES = 10


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
) -> bool:

    for child in page:
        if local_name(
            child.tag
        ) == "redirect":
            return True

    return False


def make_sample(
    text: str,
    length: int = 800,
) -> str:

    text = " ".join(
        text.split()
    )

    if len(text) > length:
        return (
            text[:length]
            + "..."
        )

    return text


def main() -> int:

    print()
    print(
        "LexiCorpus v1.4 - "
        "Prueba del limpiador Wikipedia"
    )
    print("=" * 88)

    validation = json.loads(
        VALIDATION_PATH.read_text(
            encoding="utf-8"
        )
    )

    segment = (
        validation[
            "segments"
        ][0]
    )

    input_path = (
        RAW_DIRECTORY
        / segment["filename"]
    )

    if not input_path.exists():
        print(
            "ERROR: no existe el segmento."
        )

        return 1

    cleaner = (
        WikipediaWikitextCleaner()
    )

    analyzed = 0

    original_characters = 0
    cleaned_characters = 0

    minimum_ratio = 1.0
    maximum_ratio = 0.0

    samples: list[dict] = []

    timer_start = (
        perf_counter()
    )

    with bz2.open(
        input_path,
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

            if is_redirect(
                element
            ):
                element.clear()
                continue

            title = (
                child_text(
                    element,
                    "title",
                )
                or ""
            )

            wikitext = (
                revision_text(
                    element
                )
            )

            if not wikitext.strip():
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

            minimum_ratio = min(
                minimum_ratio,
                result.reduction_ratio,
            )

            maximum_ratio = max(
                maximum_ratio,
                result.reduction_ratio,
            )

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
                        "original_sample": (
                            make_sample(
                                wikitext
                            )
                        ),
                        "cleaned_sample": (
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

    removed = (
        original_characters
        - cleaned_characters
    )

    overall_reduction = (
        removed
        / original_characters
        if original_characters
        else 0.0
    )

    print(
        "Artículos analizados : "
        f"{analyzed:,}"
    )

    print(
        "Caracteres originales: "
        f"{original_characters:,}"
    )

    print(
        "Caracteres limpios   : "
        f"{cleaned_characters:,}"
    )

    print(
        "Caracteres eliminados: "
        f"{removed:,}"
    )

    print(
        "Reducción global     : "
        f"{overall_reduction:.2%}"
    )

    print(
        "Reducción mínima     : "
        f"{minimum_ratio:.2%}"
    )

    print(
        "Reducción máxima     : "
        f"{maximum_ratio:.2%}"
    )

    print(
        "Tiempo               : "
        f"{elapsed:.2f} s"
    )

    print()
    print(
        "Muestras"
    )
    print("-" * 88)

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
            "Original : "
            f"{sample['original_characters']:,}"
        )

        print(
            "Limpio   : "
            f"{sample['cleaned_characters']:,}"
        )

        print(
            "Reducción: "
            f"{sample['reduction_ratio']:.2%}"
        )

        print()
        print(
            "ANTES:"
        )

        print(
            sample[
                "original_sample"
            ]
        )

        print()
        print(
            "DESPUÉS:"
        )

        print(
            sample[
                "cleaned_sample"
            ]
        )

    report = {
        "lexicorpus_version": (
            "1.4"
        ),
        "source_code": (
            "wikipedia_es"
        ),
        "snapshot_date": (
            validation[
                "snapshot_date"
            ]
        ),
        "segment": (
            segment["filename"]
        ),
        "articles_analyzed": (
            analyzed
        ),
        "original_characters": (
            original_characters
        ),
        "cleaned_characters": (
            cleaned_characters
        ),
        "removed_characters": (
            removed
        ),
        "overall_reduction_ratio": (
            overall_reduction
        ),
        "minimum_reduction_ratio": (
            minimum_ratio
        ),
        "maximum_reduction_ratio": (
            maximum_ratio
        ),
        "elapsed_seconds": (
            elapsed
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
    print("=" * 88)

    print(
        "Reporte:"
    )

    print(
        OUTPUT_PATH
    )

    print()
    print(
        "Prueba finalizada. "
        "No se modificó el corpus."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )