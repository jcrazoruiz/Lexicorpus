from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path


# =============================================================================
# CONFIGURACIÓN DEL PROYECTO
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.analysis.lexical_frequency import (
    LexicalFrequencyAnalyzer,
)


# =============================================================================
# CONFIGURACIÓN LEXICORPUS
# =============================================================================

FIRST_TOKEN = 537

LEXICORPUS_SIZES = (
    20_000,
    30_000,
    40_000,
    50_000,
    65_000,
)

SOURCES = {
    "literatura_clasica": "Literatura_Clasica",
    "scielo": "SciELO",
    "redalyc": "RedALyC",
    "wikipedia_es": "Wikipedia",
    "wikinews_es": "Wikinoticias",
}

DATABASE_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "database"
    / "lexicorpus.db"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexicorpus"
    / "v1_5"
)


# =============================================================================
# ACCESO A DOCUMENTOS CANONICAL
# =============================================================================

def resolve_canonical_path(
    source_code: str,
    document_id: str,
    stored_path: str | None,
) -> tuple[Path | None, bool]:
    """
    Resuelve la ubicación física actual de un documento CANONICAL.

    SQLite determina qué documentos pertenecen al corpus.

    canonical_path puede contener una ruta absoluta correspondiente a otra
    instalación del proyecto. Si esa ruta ya no existe, el archivo se busca
    dentro de la estructura actual del proyecto.

    Retorna:
        (ruta_resuelta, fue_reubicada)
    """

    # -------------------------------------------------------------------------
    # 1. Intentar primero la ruta almacenada en SQLite
    # -------------------------------------------------------------------------

    if stored_path:

        original_path = Path(stored_path)

        if original_path.exists():
            return original_path, False

        filename = original_path.name

    else:
        filename = f"{document_id}.txt"

    # -------------------------------------------------------------------------
    # 2. Resolver dentro de la instalación actual
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
    # 3. Intentar mediante document_id
    # -------------------------------------------------------------------------

    candidate_by_id = (
        canonical_directory
        / f"{document_id}.txt"
    )

    if candidate_by_id.exists():
        return candidate_by_id, True

    return None, True


def collect_canonical_documents(
    source_code: str,
) -> list[Path]:

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base SQLite: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as connection:

        rows = connection.execute(
            """
            SELECT
                document_id,
                canonical_path
            FROM document
            WHERE source_code = ?
              AND status = 'CANONICAL'
            ORDER BY document_id
            """,
            (source_code,),
        ).fetchall()

    if not rows:
        raise RuntimeError(
            f"No existen documentos CANONICAL "
            f"para la fuente: {source_code}"
        )

    documents: list[Path] = []
    missing_documents: list[tuple[str, str | None]] = []

    relocated_count = 0

    for document_id, stored_path in rows:

        resolved_path, relocated = resolve_canonical_path(
            source_code=source_code,
            document_id=document_id,
            stored_path=stored_path,
        )

        if resolved_path is None:

            missing_documents.append(
                (
                    document_id,
                    stored_path,
                )
            )

            continue

        documents.append(
            resolved_path
        )

        if relocated:
            relocated_count += 1

    print(
        f"CANONICAL en SQLite     : "
        f"{len(rows):,}"
    )

    print(
        f"Archivos localizados    : "
        f"{len(documents):,}"
    )

    print(
        f"Rutas reubicadas        : "
        f"{relocated_count:,}"
    )

    if missing_documents:

        print()
        print("ERROR DE INTEGRIDAD")
        print("-" * 80)

        print(
            f"Documentos no localizados: "
            f"{len(missing_documents):,}"
        )

        for document_id, stored_path in missing_documents[:10]:

            print()
            print(
                f"document_id : "
                f"{document_id}"
            )

            print(
                f"ruta SQLite : "
                f"{stored_path}"
            )

        if len(missing_documents) > 10:

            print(
                f"\n... y "
                f"{len(missing_documents) - 10:,} más"
            )

        raise RuntimeError(
            "Existen documentos CANONICAL registrados "
            "en SQLite que no pudieron localizarse "
            "en la instalación actual."
        )

    return documents


# =============================================================================
# CONSTRUCCIÓN DEL LEXICORPUS
# =============================================================================

def build_rows(
    results,
    lexicorpus_size: int,
) -> list[dict]:

    total_occurrences = sum(
        item.absolute_frequency
        for item in results
    )

    selected = results[
        :lexicorpus_size
    ]

    accumulated_frequency = 0

    rows: list[dict] = []

    for ranking, item in enumerate(
        selected,
        start=1,
    ):

        token = (
            FIRST_TOKEN
            + ranking
            - 1
        )

        relative_frequency = (
            item.absolute_frequency
            / total_occurrences
            if total_occurrences
            else 0.0
        )

        percentage = (
            relative_frequency
            * 100.0
        )

        accumulated_frequency += (
            item.absolute_frequency
        )

        accumulated_coverage = (
            accumulated_frequency
            / total_occurrences
            * 100.0
            if total_occurrences
            else 0.0
        )

        rows.append(
            {
                "Ranking": ranking,
                "Token": token,
                "Palabra": item.word,
                "Frecuencia": (
                    item.absolute_frequency
                ),
                "FrecuenciaRelativa": (
                    relative_frequency
                ),
                "Porcentaje": (
                    percentage
                ),
                "FrecuenciaAcumulada": (
                    accumulated_frequency
                ),
                "CoberturaAcumulada": (
                    accumulated_coverage
                ),
            }
        )

    return rows


# =============================================================================
# ESCRITURA CSV
# =============================================================================

def write_csv(
    output_path: Path,
    rows: list[dict],
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "Ranking",
        "Token",
        "Palabra",
        "Frecuencia",
        "FrecuenciaRelativa",
        "Porcentaje",
        "FrecuenciaAcumulada",
        "CoberturaAcumulada",
    ]

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            output_row = dict(
                row
            )

            output_row[
                "FrecuenciaRelativa"
            ] = (
                f"{row['FrecuenciaRelativa']:.10f}"
            )

            output_row[
                "Porcentaje"
            ] = (
                f"{row['Porcentaje']:.6f}"
            )

            output_row[
                "CoberturaAcumulada"
            ] = (
                f"{row['CoberturaAcumulada']:.6f}"
            )

            writer.writerow(
                output_row
            )


# =============================================================================
# PRESENTACIÓN DE RESULTADOS
# =============================================================================

def print_version_result(
    lexicorpus_size: int,
    vocabulary_available: int,
    selected_terms: int,
    total_occurrences: int,
    covered_occurrences: int,
    outside_occurrences: int,
    coverage_percentage: float,
    final_token: int,
    output_path: Path,
) -> None:

    print()
    print(
        f"LexiCorpus "
        f"{lexicorpus_size:,}"
    )

    print("-" * 80)

    print(
        f"Vocabulario disponible  : "
        f"{vocabulary_available:,}"
    )

    print(
        f"Términos seleccionados  : "
        f"{selected_terms:,}"
    )

    print(
        f"Ocurrencias totales     : "
        f"{total_occurrences:,}"
    )

    print(
        f"Ocurrencias cubiertas   : "
        f"{covered_occurrences:,}"
    )

    print(
        f"Ocurrencias fuera       : "
        f"{outside_occurrences:,}"
    )

    print(
        f"Cobertura               : "
        f"{coverage_percentage:.6f}%"
    )

    print(
        f"Rango de tokens         : "
        f"{FIRST_TOKEN:,} - "
        f"{final_token:,}"
    )

    print(
        f"CSV                     : "
        f"{output_path.name}"
    )


# =============================================================================
# GENERACIÓN DE LAS CINCO VERSIONES
# =============================================================================

def generate_versions(
    source_name: str,
    results,
) -> None:

    total_occurrences = sum(
        item.absolute_frequency
        for item in results
    )

    vocabulary_available = len(
        results
    )

    for lexicorpus_size in LEXICORPUS_SIZES:

        rows = build_rows(
            results,
            lexicorpus_size,
        )

        selected_terms = len(
            rows
        )

        covered_occurrences = (
            rows[-1][
                "FrecuenciaAcumulada"
            ]
            if rows
            else 0
        )

        outside_occurrences = (
            total_occurrences
            - covered_occurrences
        )

        coverage_percentage = (
            covered_occurrences
            / total_occurrences
            * 100.0
            if total_occurrences
            else 0.0
        )

        final_token = (
            FIRST_TOKEN
            + selected_terms
            - 1
            if selected_terms
            else FIRST_TOKEN - 1
        )

        output_path = (
            OUTPUT_DIRECTORY
            / (
                f"LexiCorpus_"
                f"{lexicorpus_size}_"
                f"{source_name}.csv"
            )
        )

        write_csv(
            output_path,
            rows,
        )

        print_version_result(
            lexicorpus_size=lexicorpus_size,
            vocabulary_available=vocabulary_available,
            selected_terms=selected_terms,
            total_occurrences=total_occurrences,
            covered_occurrences=covered_occurrences,
            outside_occurrences=outside_occurrences,
            coverage_percentage=coverage_percentage,
            final_token=final_token,
            output_path=output_path,
        )


# =============================================================================
# GENERACIÓN POR FUENTE
# =============================================================================

def generate_source(
    source_code: str,
) -> list[Path]:

    source_name = (
        SOURCES[source_code]
    )

    print()
    print("=" * 80)
    print(
        f"FUENTE: "
        f"{source_name}"
    )
    print("=" * 80)

    documents = (
        collect_canonical_documents(
            source_code
        )
    )

    print()
    print(
        "Calculando frecuencias léxicas..."
    )

    analyzer = (
        LexicalFrequencyAnalyzer()
    )

    results = analyzer.analyze(
        documents
    )

    print(
        f"Vocabulario disponible  : "
        f"{len(results):,}"
    )

    print(
        f"Ocurrencias totales     : "
        f"{sum(item.absolute_frequency for item in results):,}"
    )

    generate_versions(
        source_name=source_name,
        results=results,
    )

    return documents


# =============================================================================
# GENERACIÓN DEL CORPUS COMPLETO
# =============================================================================

def generate_complete(
    all_documents: list[Path],
) -> None:

    print()
    print("=" * 80)
    print(
        "FUENTE: Completo"
    )
    print("=" * 80)

    print(
        f"Documentos CANONICAL    : "
        f"{len(all_documents):,}"
    )

    print()
    print(
        "Calculando frecuencias léxicas globales..."
    )

    analyzer = (
        LexicalFrequencyAnalyzer()
    )

    results = analyzer.analyze(
        all_documents
    )

    print(
        f"Vocabulario disponible  : "
        f"{len(results):,}"
    )

    print(
        f"Ocurrencias totales     : "
        f"{sum(item.absolute_frequency for item in results):,}"
    )

    generate_versions(
        source_name="Completo",
        results=results,
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print()
    print("=" * 80)
    print(
        "GENERADOR FINAL LEXICORPUS"
    )
    print("=" * 80)

    number_of_sources = len(
        SOURCES
    )

    number_of_sizes = len(
        LEXICORPUS_SIZES
    )

    individual_versions = (
        number_of_sources
        * number_of_sizes
    )

    total_versions = (
        (number_of_sources + 1)
        * number_of_sizes
    )

    print(
        f"Fuentes individuales    : "
        f"{number_of_sources}"
    )

    print(
        f"Tamaños por fuente      : "
        f"{number_of_sizes}"
    )

    print(
        f"Versiones individuales  : "
        f"{individual_versions}"
    )

    print(
        f"Versiones Completo      : "
        f"{number_of_sizes}"
    )

    print(
        f"CSV totales esperados   : "
        f"{total_versions}"
    )

    all_documents: list[Path] = []

    for source_code in SOURCES:

        source_documents = (
            generate_source(
                source_code
            )
        )

        all_documents.extend(
            source_documents
        )

    generate_complete(
        all_documents
    )

    print()
    print("=" * 80)
    print(
        "GENERACIÓN FINALIZADA"
    )
    print("=" * 80)

    print(
        f"Total de CSV esperados  : "
        f"{total_versions}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )