from __future__ import annotations

import json
import sys

from dataclasses import asdict
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SRC_DIRECTORY = (
    PROJECT_ROOT
    / "src"
)

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIRECTORY),
    )


from lexicorpus.acquisition.wikipedia_dump_extractor import (
    WikipediaDumpExtractor,
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

RAW_DUMP_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikipedia_es"
    / "dump"
)

ARTICLE_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikipedia_es"
    / "articles"
)

METADATA_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "acquisition"
    / "wikipedia_es"
    / "wikipedia_acquisition.jsonl"
)


def format_elapsed(
    seconds: float,
) -> str:

    total = int(
        seconds
    )

    hours, remainder = divmod(
        total,
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


def main() -> int:

    print()
    print(
        "LexiCorpus v1.4 - "
        "Extracción Wikipedia"
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

    snapshot_date = (
        validation[
            "snapshot_date"
        ]
    )

    segment_path = (
        RAW_DUMP_DIRECTORY
        / segment[
            "filename"
        ]
    )

    if not segment_path.exists():

        print(
            "ERROR: no existe el segmento:"
        )

        print(
            segment_path
        )

        return 1

    print(
        "Snapshot             : "
        f"{snapshot_date}"
    )

    print(
        "Segmento             : "
        f"{segment['filename']}"
    )

    print(
        "Rango                : "
        f"p{segment['start_page']} "
        "-> "
        f"p{segment['end_page']}"
    )

    print(
        "Destino artículos    : "
        f"{ARTICLE_DIRECTORY}"
    )

    print(
        "Metadatos            : "
        f"{METADATA_PATH}"
    )

    print("-" * 88)

    # IMPORTANTE:
    # como esta es la primera extracción formal del segmento,
    # limpiamos el archivo JSONL previo si existe.
    #
    # NO elimina los TXT.
    METADATA_PATH.unlink(
        missing_ok=True
    )

    extractor = (
        WikipediaDumpExtractor(
            cleaner=(
                WikipediaWikitextCleaner()
            ),
            output_directory=(
                ARTICLE_DIRECTORY
            ),
            metadata_path=(
                METADATA_PATH
            ),
            snapshot_date=(
                snapshot_date
            ),
        )
    )

    timer_start = (
        perf_counter()
    )

    result = extractor.extract(
        segment_path
    )

    elapsed = (
        perf_counter()
        - timer_start
    )

    print()
    print("=" * 88)

    print(
        "Resultado"
    )

    print("-" * 88)

    for key, value in (
        asdict(
            result
        ).items()
    ):
        print(
            f"{key:<25}: "
            f"{value:,}"
        )

    print(
        "Tiempo total             : "
        f"{format_elapsed(elapsed)}"
    )

    print(
        "Directorio artículos     : "
        f"{ARTICLE_DIRECTORY}"
    )

    print(
        "Archivo metadata         : "
        f"{METADATA_PATH}"
    )

    return (
        0
        if result.errors == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )