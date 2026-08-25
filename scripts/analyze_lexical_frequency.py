from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.analysis.lexical_frequency import (
    LexicalFrequencyAnalyzer,
)


# ---------------------------------------------------------------------
# Configuración del análisis léxico LexiCorpus v1.4
# ---------------------------------------------------------------------

SOURCE_CODES = (
    "literatura_clasica",
    "scielo",
    "redalyc",
    "wikipedia_es",
)

MAX_LEXICAL_TOKENS = 65_000

FIRST_TOKEN = 537
LAST_TOKEN = 65_536


def collect_documents(
    source_code: str,
) -> list[Path]:
    """
    Recupera todos los documentos canónicos de una fuente.
    """

    source_directory = (
        PROJECT_ROOT
        / "data"
        / "canonical"
        / source_code
    )

    if not source_directory.exists():
        raise FileNotFoundError(
            f"No existe la carpeta canónica: "
            f"{source_directory}"
        )

    return sorted(
        path
        for path in source_directory.rglob("*.txt")
        if path.is_file()
    )


def prepare_top_results(
    results,
):
    """
    Selecciona como máximo los 65,000 términos más frecuentes.

    El orden recibido desde LexicalFrequencyAnalyzer es:
        1. frecuencia absoluta descendente
        2. palabra ascendente para desempates

    Los tokens LexiMapSp-16 disponibles para este vocabulario
    corresponden al intervalo 537..65536.
    """

    selected = results[:MAX_LEXICAL_TOKENS]

    alphabetical_words = sorted(
        item.word
        for item in selected
    )

    alphabetical_rank = {
        word: ranking
        for ranking, word in enumerate(
            alphabetical_words,
            start=1,
        )
    }

    return selected, alphabetical_rank


def build_rows(
    results,
    total_tokens: int,
):
    """
    Construye las filas manteniendo el token asignado por
    frecuencia independientemente del orden de salida.
    """

    selected, alphabetical_rank = (
        prepare_top_results(results)
    )

    rows = []

    for frequency_rank, item in enumerate(
        selected,
        start=1,
    ):
        token = FIRST_TOKEN + frequency_rank - 1

        if token > LAST_TOKEN:
            raise ValueError(
                f"Token fuera del rango LexiMapSp-16: "
                f"{token}"
            )

        relative_frequency = (
            item.absolute_frequency / total_tokens
            if total_tokens
            else 0
        )

        rows.append(
            {
                "Token": token,
                "RankingFrecuencia": frequency_rank,
                "RankingAlfabetico": (
                    alphabetical_rank[item.word]
                ),
                "Palabra": item.word,
                "FrecuenciaAbsoluta": (
                    item.absolute_frequency
                ),
                "FrecuenciaRelativa": (
                    relative_frequency
                ),
                "FrecuenciaDocumental": (
                    item.document_frequency
                ),
            }
        )

    return rows


def write_csv(
    output_path: Path,
    rows,
) -> None:
    """
    Escribe un reporte CSV.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "Token",
        "RankingFrecuencia",
        "RankingAlfabetico",
        "Palabra",
        "FrecuenciaAbsoluta",
        "FrecuenciaRelativa",
        "FrecuenciaDocumental",
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
            output_row = dict(row)

            output_row["FrecuenciaRelativa"] = (
                f"{row['FrecuenciaRelativa']:.10f}"
            )

            writer.writerow(output_row)


def write_reports(
    output_directory: Path,
    report_name: str,
    results,
) -> tuple[Path, Path]:
    """
    Genera dos representaciones del mismo vocabulario:

    1. ordenado por frecuencia
    2. ordenado alfabéticamente

    El Token no cambia entre ambos archivos.
    """

    total_tokens = sum(
        item.absolute_frequency
        for item in results
    )

    rows = build_rows(
        results,
        total_tokens,
    )

    frequency_rows = sorted(
        rows,
        key=lambda row: (
            row["RankingFrecuencia"]
        ),
    )

    alphabetical_rows = sorted(
        rows,
        key=lambda row: (
            row["RankingAlfabetico"]
        ),
    )

    frequency_path = (
        output_directory
        / f"{report_name}_top65000_frequency.csv"
    )

    alphabetical_path = (
        output_directory
        / f"{report_name}_top65000_alphabetical.csv"
    )

    write_csv(
        frequency_path,
        frequency_rows,
    )

    write_csv(
        alphabetical_path,
        alphabetical_rows,
    )

    return (
        frequency_path,
        alphabetical_path,
    )


def print_summary(
    source_name: str,
    document_count: int,
    results,
) -> None:
    """
    Presenta las estadísticas generales del análisis.
    """

    total_tokens = sum(
        item.absolute_frequency
        for item in results
    )

    vocabulary_size = len(results)

    selected_count = min(
        vocabulary_size,
        MAX_LEXICAL_TOKENS,
    )

    hapax_count = sum(
        1
        for item in results
        if item.absolute_frequency == 1
    )

    selected_frequency = sum(
        item.absolute_frequency
        for item in results[:MAX_LEXICAL_TOKENS]
    )

    coverage = (
        selected_frequency / total_tokens
        if total_tokens
        else 0
    )

    print("\n" + "=" * 80)
    print(source_name)
    print("=" * 80)

    print(
        f"Documentos analizados       : "
        f"{document_count:,}"
    )

    print(
        f"Tokens léxicos              : "
        f"{total_tokens:,}"
    )

    print(
        f"Palabras distintas          : "
        f"{vocabulary_size:,}"
    )

    print(
        f"Hapax legomena              : "
        f"{hapax_count:,}"
    )

    print(
        f"Términos seleccionados      : "
        f"{selected_count:,}"
    )

    print(
        f"Cobertura Top 65,000        : "
        f"{coverage:.4%}"
    )

    if selected_count:
        final_token = (
            FIRST_TOKEN
            + selected_count
            - 1
        )

        print(
            f"Rango de tokens utilizado   : "
            f"{FIRST_TOKEN:,} - "
            f"{final_token:,}"
        )

    print("\nTop 20")
    print("-" * 80)

    for ranking, item in enumerate(
        results[:20],
        start=1,
    ):
        token = FIRST_TOKEN + ranking - 1

        print(
            f"{ranking:>4} "
            f"Token {token:>5} "
            f"{item.word:<25} "
            f"{item.absolute_frequency:>15,}"
        )


def analyze_corpus(
    analyzer: LexicalFrequencyAnalyzer,
    name: str,
    report_name: str,
    documents: list[Path],
    output_directory: Path,
) -> None:
    """
    Ejecuta el análisis completo de un corpus.
    """

    print("\n" + "=" * 80)
    print(f"Analizando: {name}")
    print("=" * 80)

    print(
        f"Documentos encontrados: "
        f"{len(documents):,}"
    )

    results = analyzer.analyze(
        documents
    )

    frequency_path, alphabetical_path = (
        write_reports(
            output_directory,
            report_name,
            results,
        )
    )

    print_summary(
        name,
        len(documents),
        results,
    )

    print("\nArchivos generados:")

    print(
        f"  Frecuencia : "
        f"{frequency_path}"
    )

    print(
        f"  Alfabético : "
        f"{alphabetical_path}"
    )


def main() -> int:

    print(
        "LexiCorpus v1.4 - Análisis léxico"
    )

    print("=" * 80)

    print(
        f"Vocabulario máximo : "
        f"{MAX_LEXICAL_TOKENS:,}"
    )

    print(
        f"Tokens reservados  : "
        f"1 - {FIRST_TOKEN - 1}"
    )

    print(
        f"Tokens léxicos     : "
        f"{FIRST_TOKEN} - {LAST_TOKEN}"
    )

    analyzer = LexicalFrequencyAnalyzer()

    documents_by_source: dict[
        str,
        list[Path],
    ] = {}

    # -------------------------------------------------------------
    # Recuperar documentos
    # -------------------------------------------------------------

    for source_code in SOURCE_CODES:
        documents_by_source[source_code] = (
            collect_documents(source_code)
        )

    all_documents = []

    for source_code in SOURCE_CODES:
        all_documents.extend(
            documents_by_source[source_code]
        )

    output_directory = (
        PROJECT_ROOT
        / "reports"
        / "lexical"
        / "v1_4"
    )

    # -------------------------------------------------------------
    # Análisis global
    # -------------------------------------------------------------

    analyze_corpus(
        analyzer=analyzer,
        name="LexiCorpus global v1.4",
        report_name="lexicorpus",
        documents=all_documents,
        output_directory=output_directory,
    )

    # -------------------------------------------------------------
    # Análisis por fuente
    # -------------------------------------------------------------

    source_names = {
        "literatura_clasica": (
            "Literatura clásica"
        ),
        "scielo": (
            "SciELO México"
        ),
        "redalyc": (
            "RedALyC"
        ),
        "wikipedia_es": (
            "Wikipedia en español"
        ),
    }

    for source_code in SOURCE_CODES:

        analyze_corpus(
            analyzer=analyzer,
            name=source_names[source_code],
            report_name=source_code,
            documents=(
                documents_by_source[source_code]
            ),
            output_directory=output_directory,
        )

    print("\n" + "=" * 80)
    print("Análisis finalizado")
    print("=" * 80)

    print(
        f"Reportes disponibles en:\n"
        f"{output_directory}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())