from __future__ import annotations

import csv
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# PROYECTO
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DATABASE_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "database"
    / "lexicorpus.db"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "v1_5"
)

SOURCES = {
    "literatura_clasica": "Literatura_Clasica",
    "scielo": "SciELO",
    "redalyc": "RedALyC",
    "wikipedia_es": "Wikipedia",
    "wikinews_es": "Wikinoticias",
}


# =============================================================================
# TOKENIZACIÓN
# =============================================================================

WORD_PATTERN = re.compile(
    r"(?<![\wáéíóúüñ])"
    r"[a-záéíóúüñ]{2,}"
    r"(?![\wáéíóúüñ])",
    flags=re.IGNORECASE,
)


@dataclass(slots=True)
class LexicalFrequency:
    word: str
    absolute_frequency: int
    document_frequency: int


# =============================================================================
# UTILIDADES
# =============================================================================

def format_seconds(seconds: float) -> str:

    seconds = max(
        0,
        int(seconds),
    )

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


# =============================================================================
# RESOLUCIÓN DE DOCUMENTOS
# =============================================================================

def resolve_document_path(
    source_code: str,
    document_id: str,
    stored_path: str | None,
) -> tuple[Path | None, bool]:

    # -------------------------------------------------------------------------
    # 1. Ruta almacenada en SQLite
    # -------------------------------------------------------------------------

    if stored_path:

        stored = Path(
            stored_path
        )

        if stored.exists():
            return stored, False

        filename = stored.name

    else:

        filename = (
            f"{document_id}.txt"
        )

    # -------------------------------------------------------------------------
    # 2. Ruta dentro de la instalación actual
    # -------------------------------------------------------------------------

    canonical_directory = (
        PROJECT_ROOT
        / "data"
        / "canonical"
        / source_code
    )

    candidate = (
        canonical_directory
        / filename
    )

    if candidate.exists():
        return candidate, True

    # -------------------------------------------------------------------------
    # 3. Segunda alternativa: document_id
    # -------------------------------------------------------------------------

    candidate = (
        canonical_directory
        / f"{document_id}.txt"
    )

    if candidate.exists():
        return candidate, True

    return None, True


def collect_documents(
    source_code: str,
) -> list[Path]:

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        rows = connection.execute(
            """
            SELECT
                document_id,
                canonical_path
            FROM document
            WHERE source_code = ?
              AND status = 'CANONICAL'
              AND canonical_path IS NOT NULL
            ORDER BY document_id
            """,
            (source_code,),
        ).fetchall()

    documents: list[Path] = []

    missing: list[str] = []

    relocated = 0

    for document_id, canonical_path in rows:

        path, was_relocated = (
            resolve_document_path(
                source_code=source_code,
                document_id=document_id,
                stored_path=canonical_path,
            )
        )

        if path is None:

            missing.append(
                document_id
            )

            continue

        documents.append(
            path
        )

        if was_relocated:
            relocated += 1

    print(
        f"CANONICAL SQLite       : "
        f"{len(rows):,}"
    )

    print(
        f"Archivos localizados   : "
        f"{len(documents):,}"
    )

    print(
        f"Rutas reubicadas       : "
        f"{relocated:,}"
    )

    if missing:

        print()
        print(
            f"ERROR: "
            f"{len(missing):,} documentos "
            f"no pudieron localizarse."
        )

        for document_id in missing[:10]:
            print(
                f"  {document_id}"
            )

        raise RuntimeError(
            f"No pudieron localizarse "
            f"{len(missing):,} documentos "
            f"de {source_code}."
        )

    return documents


# =============================================================================
# ANÁLISIS LÉXICO CON PROGRESO
# =============================================================================

def tokenize(
    text: str,
) -> list[str]:

    normalized_text = (
        text.lower()
    )

    return WORD_PATTERN.findall(
        normalized_text
    )


def analyze_with_progress(
    source_name: str,
    document_paths: list[Path],
) -> list[LexicalFrequency]:

    frequencies: Counter[str] = (
        Counter()
    )

    document_frequencies: Counter[str] = (
        Counter()
    )

    total_documents = len(
        document_paths
    )

    if total_documents == 0:
        return []

    started_at = time.perf_counter()

    next_percentage = 10

    print()
    print(
        "Calculando frecuencias léxicas..."
    )

    for index, document_path in enumerate(
        document_paths,
        start=1,
    ):

        text = document_path.read_text(
            encoding="utf-8"
        )

        words = tokenize(
            text
        )

        frequencies.update(
            words
        )

        document_frequencies.update(
            set(words)
        )

        current_percentage = (
            index
            / total_documents
            * 100
        )

        should_report = (
            current_percentage >= next_percentage
            or index == total_documents
        )

        if should_report:

            elapsed = (
                time.perf_counter()
                - started_at
            )

            documents_per_minute = (
                index
                / elapsed
                * 60
                if elapsed > 0
                else 0.0
            )

            remaining_documents = (
                total_documents
                - index
            )

            eta_seconds = (
                remaining_documents
                / (index / elapsed)
                if elapsed > 0
                and index > 0
                else 0.0
            )

            percentage_to_show = min(
                100,
                int(
                    current_percentage
                ),
            )

            print(
                f"[{source_name}] "
                f"{percentage_to_show:>3}% | "
                f"{index:,} / "
                f"{total_documents:,} docs | "
                f"Transcurrido "
                f"{format_seconds(elapsed)} | "
                f"{documents_per_minute:,.1f} docs/min | "
                f"ETA "
                f"{format_seconds(eta_seconds)}"
            )

            while (
                next_percentage
                <= current_percentage
            ):
                next_percentage += 10

    results = [
        LexicalFrequency(
            word=word,
            absolute_frequency=frequency,
            document_frequency=(
                document_frequencies[word]
            ),
        )
        for word, frequency
        in frequencies.items()
    ]

    results.sort(
        key=lambda item: (
            -item.absolute_frequency,
            item.word,
        )
    )

    total_elapsed = (
        time.perf_counter()
        - started_at
    )

    print()
    print(
        f"Análisis completado     : "
        f"{format_seconds(total_elapsed)}"
    )

    return results


# =============================================================================
# GENERACIÓN DEL CSV
# =============================================================================

def write_frequency_table(
    source_name: str,
    results: list[LexicalFrequency],
) -> Path:

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIRECTORY
        / (
            f"{source_name}_"
            f"frequency_complete.csv"
        )
    )

    total_occurrences = sum(
        item.absolute_frequency
        for item in results
    )

    fieldnames = [
        "Ranking",
        "Palabra",
        "Frecuencia",
        "FrecuenciaRelativa",
        "FrecuenciaDocumental",
    ]

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for ranking, item in enumerate(
            results,
            start=1,
        ):

            relative_frequency = (
                item.absolute_frequency
                / total_occurrences
                if total_occurrences
                else 0.0
            )

            writer.writerow(
                {
                    "Ranking": ranking,
                    "Palabra": (
                        item.word
                    ),
                    "Frecuencia": (
                        item.absolute_frequency
                    ),
                    "FrecuenciaRelativa": (
                        f"{relative_frequency:.10f}"
                    ),
                    "FrecuenciaDocumental": (
                        item.document_frequency
                    ),
                }
            )

    return output_path


# =============================================================================
# PROCESAMIENTO POR FUENTE
# =============================================================================

def process_source(
    source_code: str,
    source_name: str,
) -> None:

    print()
    print("=" * 100)
    print(
        f"FUENTE: {source_name}"
    )
    print("=" * 100)

    documents = collect_documents(
        source_code
    )

    results = analyze_with_progress(
        source_name=source_name,
        document_paths=documents,
    )

    total_occurrences = sum(
        item.absolute_frequency
        for item in results
    )

    print()
    print(
        f"Vocabulario            : "
        f"{len(results):,}"
    )

    print(
        f"Ocurrencias            : "
        f"{total_occurrences:,}"
    )

    print()
    print(
        "Escribiendo tabla completa..."
    )

    output_path = write_frequency_table(
        source_name=source_name,
        results=results,
    )

    print(
        f"Archivo                : "
        f"{output_path.name}"
    )

    print(
        f"Filas                  : "
        f"{len(results):,}"
    )

    print(
        "Estado                 : OK"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print()
    print("=" * 100)
    print(
        "GENERACIÓN DE TABLAS COMPLETAS "
        "DE FRECUENCIA LÉXICA - LEXICORPUS v1.5"
    )
    print("=" * 100)

    print(
        f"Fuentes                : "
        f"{len(SOURCES)}"
    )

    process_started_at = (
        time.perf_counter()
    )

    for source_code, source_name in (
        SOURCES.items()
    ):

        process_source(
            source_code=source_code,
            source_name=source_name,
        )

    total_elapsed = (
        time.perf_counter()
        - process_started_at
    )

    print()
    print("=" * 100)
    print(
        "GENERACIÓN COMPLETADA"
    )
    print("=" * 100)

    print(
        f"Tablas generadas       : "
        f"{len(SOURCES)}"
    )

    print(
        f"Tiempo total           : "
        f"{format_seconds(total_elapsed)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )