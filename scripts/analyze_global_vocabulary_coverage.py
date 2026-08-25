from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LEXICAL_REPORTS = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "v1_4"
)

GLOBAL_FILE = (
    LEXICAL_REPORTS
    / "lexicorpus_top65000_frequency.csv"
)

SOURCE_FILES = {
    "Literatura clásica": (
        LEXICAL_REPORTS
        / "literatura_clasica_top65000_frequency.csv"
    ),
    "SciELO": (
        LEXICAL_REPORTS
        / "scielo_top65000_frequency.csv"
    ),
    "RedALyC": (
        LEXICAL_REPORTS
        / "redalyc_top65000_frequency.csv"
    ),
    "Wikipedia": (
        LEXICAL_REPORTS
        / "wikipedia_es_top65000_frequency.csv"
    ),
}

OUTPUT_FILE = (
    LEXICAL_REPORTS
    / "global_vocabulary_coverage.csv"
)


def load_frequency_csv(
    path: Path,
) -> dict[str, int]:

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo requerido: {path}"
        )

    data: dict[str, int] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:

        reader = csv.DictReader(input_file)

        for row in reader:
            data[row["Palabra"]] = int(
                row["FrecuenciaAbsoluta"]
            )

    return data


def main() -> int:

    print(
        "LexiCorpus v1.4 - Cobertura del "
        "vocabulario global"
    )
    print("=" * 80)

    global_frequency = load_frequency_csv(
        GLOBAL_FILE
    )

    global_words = set(global_frequency)

    if len(global_words) != 65_000:
        raise ValueError(
            "El vocabulario global debe contener "
            "exactamente 65,000 términos."
        )

    print(
        f"Vocabulario global : "
        f"{len(global_words):,} términos"
    )

    rows = []

    # Totales obtenidos en el análisis léxico v1.4.
    #
    # Son tokens léxicos, NO word_count de la BD.
    source_total_tokens = {
        "Literatura clásica": 550_430,
        "SciELO": 38_538_532,
        "RedALyC": 31_685_970,
        "Wikipedia": 85_037_674,
    }

    print()
    print("=" * 80)
    print(
        "Cobertura del diccionario global "
        "por fuente"
    )
    print("=" * 80)

    for source_name, source_file in (
        SOURCE_FILES.items()
    ):

        source_frequency = load_frequency_csv(
            source_file
        )

        total_tokens = source_total_tokens[
            source_name
        ]

        common_words = (
            global_words
            & set(source_frequency)
        )

        covered_tokens = sum(
            source_frequency[word]
            for word in common_words
        )

        uncovered_tokens = (
            total_tokens - covered_tokens
        )

        token_coverage = (
            covered_tokens / total_tokens
            if total_tokens
            else 0
        )

        vocabulary_overlap = (
            len(common_words)
            / len(global_words)
            if global_words
            else 0
        )

        print()
        print(source_name)
        print("-" * 80)

        print(
            f"Tokens totales              : "
            f"{total_tokens:,}"
        )

        print(
            f"Tokens cubiertos            : "
            f"{covered_tokens:,}"
        )

        print(
            f"Tokens fuera del diccionario: "
            f"{uncovered_tokens:,}"
        )

        print(
            f"Cobertura por ocurrencias   : "
            f"{token_coverage:.4%}"
        )

        print(
            f"Términos globales presentes : "
            f"{len(common_words):,}"
        )

        print(
            f"Solapamiento vocabulario    : "
            f"{vocabulary_overlap:.4%}"
        )

        rows.append(
            {
                "Fuente": source_name,
                "TokensTotales": total_tokens,
                "TokensCubiertos": covered_tokens,
                "TokensFueraDiccionario": (
                    uncovered_tokens
                ),
                "CoberturaOcurrencias": (
                    f"{token_coverage:.10f}"
                ),
                "TerminosGlobalesPresentes": (
                    len(common_words)
                ),
                "SolapamientoVocabulario": (
                    f"{vocabulary_overlap:.10f}"
                ),
            }
        )

    # -------------------------------------------------------------
    # Global
    # -------------------------------------------------------------

    global_total_tokens = 155_812_606

    global_covered_tokens = sum(
        global_frequency.values()
    )

    global_uncovered_tokens = (
        global_total_tokens
        - global_covered_tokens
    )

    global_coverage = (
        global_covered_tokens
        / global_total_tokens
    )

    print()
    print("=" * 80)
    print("LexiCorpus global")
    print("=" * 80)

    print(
        f"Tokens totales              : "
        f"{global_total_tokens:,}"
    )

    print(
        f"Tokens cubiertos            : "
        f"{global_covered_tokens:,}"
    )

    print(
        f"Tokens fuera del diccionario: "
        f"{global_uncovered_tokens:,}"
    )

    print(
        f"Cobertura por ocurrencias   : "
        f"{global_coverage:.4%}"
    )

    rows.append(
        {
            "Fuente": "LexiCorpus global",
            "TokensTotales": (
                global_total_tokens
            ),
            "TokensCubiertos": (
                global_covered_tokens
            ),
            "TokensFueraDiccionario": (
                global_uncovered_tokens
            ),
            "CoberturaOcurrencias": (
                f"{global_coverage:.10f}"
            ),
            "TerminosGlobalesPresentes": (
                len(global_words)
            ),
            "SolapamientoVocabulario": (
                f"{1.0:.10f}"
            ),
        }
    )

    # -------------------------------------------------------------
    # CSV
    # -------------------------------------------------------------

    fieldnames = [
        "Fuente",
        "TokensTotales",
        "TokensCubiertos",
        "TokensFueraDiccionario",
        "CoberturaOcurrencias",
        "TerminosGlobalesPresentes",
        "SolapamientoVocabulario",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 80)
    print("Análisis finalizado")
    print("=" * 80)

    print(
        f"Archivo generado:\n"
        f"{OUTPUT_FILE}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())