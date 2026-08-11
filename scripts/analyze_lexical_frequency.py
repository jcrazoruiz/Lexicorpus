from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.analysis.lexical_frequency import (
    LexicalFrequencyAnalyzer,
)


def collect_documents(
    source_code: str,
) -> list[Path]:
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


def write_frequency_csv(
    output_path: Path,
    results,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_tokens = sum(
        item.absolute_frequency
        for item in results
    )

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:

        writer = csv.writer(output_file)

        writer.writerow(
            [
                "Ranking",
                "Palabra",
                "FrecuenciaAbsoluta",
                "FrecuenciaRelativa",
                "FrecuenciaDocumental",
            ]
        )

        for ranking, item in enumerate(
            results,
            start=1,
        ):
            relative_frequency = (
                item.absolute_frequency
                / total_tokens
                if total_tokens
                else 0
            )

            writer.writerow(
                [
                    ranking,
                    item.word,
                    item.absolute_frequency,
                    f"{relative_frequency:.10f}",
                    item.document_frequency,
                ]
            )


def print_summary(
    source_name: str,
    document_count: int,
    results,
) -> None:
    total_tokens = sum(
        item.absolute_frequency
        for item in results
    )

    vocabulary_size = len(results)

    hapax_count = sum(
        1
        for item in results
        if item.absolute_frequency == 1
    )

    print("\n" + "=" * 72)
    print(source_name)
    print("=" * 72)
    print(
        f"Documentos analizados : "
        f"{document_count:,}"
    )
    print(
        f"Tokens léxicos        : "
        f"{total_tokens:,}"
    )
    print(
        f"Palabras distintas    : "
        f"{vocabulary_size:,}"
    )
    print(
        f"Hapax legomena        : "
        f"{hapax_count:,}"
    )

    print("\nTop 20")
    print("-" * 72)

    for ranking, item in enumerate(
        results[:20],
        start=1,
    ):
        print(
            f"{ranking:>4} "
            f"{item.word:<25} "
            f"{item.absolute_frequency:>12,}"
        )


def main() -> int:
    analyzer = LexicalFrequencyAnalyzer()

    literature_documents = collect_documents(
        "literatura_clasica"
    )

    scielo_documents = collect_documents(
        "scielo"
    )

    combined_documents = (
        literature_documents
        + scielo_documents
    )

    literature_results = analyzer.analyze(
        literature_documents
    )

    scielo_results = analyzer.analyze(
        scielo_documents
    )

    combined_results = analyzer.analyze(
        combined_documents
    )

    output_directory = (
        PROJECT_ROOT
        / "reports"
        / "lexical"
    )

    write_frequency_csv(
        output_directory
        / "literatura_clasica_frequency.csv",
        literature_results,
    )

    write_frequency_csv(
        output_directory
        / "scielo_frequency.csv",
        scielo_results,
    )

    write_frequency_csv(
        output_directory
        / "lexicorpus_frequency.csv",
        combined_results,
    )

    print_summary(
        "Literatura clásica",
        len(literature_documents),
        literature_results,
    )

    print_summary(
        "SciELO México",
        len(scielo_documents),
        scielo_results,
    )

    print_summary(
        "LexiCorpus combinado",
        len(combined_documents),
        combined_results,
    )

    print("\nArchivos generados:")
    print(
        output_directory
        / "literatura_clasica_frequency.csv"
    )
    print(
        output_directory
        / "scielo_frequency.csv"
    )
    print(
        output_directory
        / "lexicorpus_frequency.csv"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())