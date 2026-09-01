from __future__ import annotations

import sys
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


from lexicorpus.acquisition.wikinews_dump_extractor import (
    WikinewsDumpExtractor,
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

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikinews_es"
    / "articles"
)

METADATA_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "acquisition"
    / "wikinews_es"
    / "wikinews_acquisition.jsonl"
)


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


def main() -> int:

    print()
    print(
        "LexiCorpus v1.5 - "
        "Extracción Wikinoticias"
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
        f"Dump                 : "
        f"{DUMP_PATH.name}"
    )

    print(
        f"Destino artículos    : "
        f"{OUTPUT_DIRECTORY}"
    )

    print(
        f"Metadatos            : "
        f"{METADATA_PATH}"
    )

    print("-" * 80)

    # Evitamos duplicar el JSONL si el script
    # se ejecuta accidentalmente dos veces.
    if METADATA_PATH.exists():

        print()
        print(
            "ERROR: ya existe el archivo "
            "de metadatos:"
        )

        print(
            METADATA_PATH
        )

        print()
        print(
            "No se realizó ninguna extracción."
        )

        return 2

    cleaner = (
        WikipediaWikitextCleaner()
    )

    extractor = (
        WikinewsDumpExtractor(
            cleaner=cleaner,
            output_directory=(
                OUTPUT_DIRECTORY
            ),
            metadata_path=(
                METADATA_PATH
            ),
            snapshot_date=SNAPSHOT,
        )
    )

    start = perf_counter()

    result = extractor.extract(
        DUMP_PATH
    )

    elapsed = (
        perf_counter()
        - start
    )

    print()
    print("=" * 80)
    print("Resultado")
    print("-" * 80)

    print(
        f"Páginas inspeccionadas : "
        f"{result.pages_inspected:,}"
    )

    print(
        f"Namespace 0            : "
        f"{result.namespace_zero:,}"
    )

    print(
        f"Redirecciones          : "
        f"{result.redirects:,}"
    )

    print(
        f"Wikitext vacío         : "
        f"{result.empty_wikitext:,}"
    )

    print(
        f"Vacíos tras limpieza   : "
        f"{result.cleaned_empty:,}"
    )

    print(
        f"Artículos extraídos    : "
        f"{result.extracted:,}"
    )

    print(
        f"Con categorías         : "
        f"{result.with_categories:,}"
    )

    print(
        f"Con ámbito geográfico  : "
        f"{result.with_geographic_scope:,}"
    )

    print(
        f"Con fecha publicación  : "
        f"{result.with_publication_date:,}"
    )

    print(
        f"Errores                : "
        f"{result.errors:,}"
    )

    print(
        f"Tiempo                 : "
        f"{format_time(elapsed)}"
    )

    print()
    print(
        f"Metadatos              : "
        f"{METADATA_PATH}"
    )

    print()
    print(
        "Extracción completa finalizada."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())