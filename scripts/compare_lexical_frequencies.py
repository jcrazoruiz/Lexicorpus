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
    "Literatura": (
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
    / "lexicorpus_top65000_comparison.csv"
)


def load_frequency_csv(
    path: Path,
) -> dict[str, dict]:
    """
    Carga un reporte de frecuencia léxica y utiliza
    la palabra como clave.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo requerido: {path}"
        )

    data: dict[str, dict] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:

        reader = csv.DictReader(input_file)

        for row in reader:
            word = row["Palabra"]

            data[word] = {
                "token": int(
                    row["Token"]
                ),
                "frequency_rank": int(
                    row["RankingFrecuencia"]
                ),
                "alphabetical_rank": int(
                    row["RankingAlfabetico"]
                ),
                "absolute_frequency": int(
                    row["FrecuenciaAbsoluta"]
                ),
                "relative_frequency": float(
                    row["FrecuenciaRelativa"]
                ),
                "document_frequency": int(
                    row["FrecuenciaDocumental"]
                ),
            }

    return data


def format_relative_frequency(
    value: float,
) -> str:
    return f"{value:.10f}"


def main() -> int:

    print(
        "LexiCorpus v1.4 - Comparación léxica"
    )
    print("=" * 80)

    # -------------------------------------------------------------
    # Cargar vocabulario global
    # -------------------------------------------------------------

    global_data = load_frequency_csv(
        GLOBAL_FILE
    )

    print(
        f"Términos globales cargados : "
        f"{len(global_data):,}"
    )

    if len(global_data) != 65_000:
        raise ValueError(
            "El vocabulario global no contiene "
            "exactamente 65,000 términos."
        )

    # -------------------------------------------------------------
    # Cargar fuentes
    # -------------------------------------------------------------

    source_data: dict[
        str,
        dict[str, dict],
    ] = {}

    for source_name, source_file in (
        SOURCE_FILES.items()
    ):
        data = load_frequency_csv(
            source_file
        )

        source_data[source_name] = data

        print(
            f"{source_name:<20}: "
            f"{len(data):>7,} términos"
        )

    # -------------------------------------------------------------
    # Construcción del CSV maestro
    # -------------------------------------------------------------

    fieldnames = [
        "TokenGlobal",
        "RankingGlobal",
        "RankingAlfabeticoGlobal",
        "Palabra",

        "FrecuenciaTotal",
        "FrecuenciaRelativaTotal",
        "FrecuenciaDocumentalTotal",
    ]

    for source_name in SOURCE_FILES:
        fieldnames.extend(
            [
                f"Frecuencia{source_name}",
                f"FrecuenciaRelativa{source_name}",
                f"FrecuenciaDocumental{source_name}",
                f"Ranking{source_name}",
            ]
        )

    rows = []

    global_items = sorted(
        global_data.items(),
        key=lambda item: (
            item[1]["frequency_rank"]
        ),
    )

    for word, global_values in global_items:

        row = {
            "TokenGlobal": (
                global_values["token"]
            ),
            "RankingGlobal": (
                global_values[
                    "frequency_rank"
                ]
            ),
            "RankingAlfabeticoGlobal": (
                global_values[
                    "alphabetical_rank"
                ]
            ),
            "Palabra": word,

            "FrecuenciaTotal": (
                global_values[
                    "absolute_frequency"
                ]
            ),
            "FrecuenciaRelativaTotal": (
                format_relative_frequency(
                    global_values[
                        "relative_frequency"
                    ]
                )
            ),
            "FrecuenciaDocumentalTotal": (
                global_values[
                    "document_frequency"
                ]
            ),
        }

        for source_name in SOURCE_FILES:

            values = source_data[
                source_name
            ].get(word)

            if values is None:
                row[
                    f"Frecuencia{source_name}"
                ] = 0

                row[
                    f"FrecuenciaRelativa{source_name}"
                ] = (
                    "0.0000000000"
                )

                row[
                    f"FrecuenciaDocumental{source_name}"
                ] = 0

                row[
                    f"Ranking{source_name}"
                ] = ""

            else:
                row[
                    f"Frecuencia{source_name}"
                ] = (
                    values[
                        "absolute_frequency"
                    ]
                )

                row[
                    f"FrecuenciaRelativa{source_name}"
                ] = (
                    format_relative_frequency(
                        values[
                            "relative_frequency"
                        ]
                    )
                )

                row[
                    f"FrecuenciaDocumental{source_name}"
                ] = (
                    values[
                        "document_frequency"
                    ]
                )

                row[
                    f"Ranking{source_name}"
                ] = (
                    values[
                        "frequency_rank"
                    ]
                )

        rows.append(row)

    # -------------------------------------------------------------
    # Escribir CSV
    # -------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    # -------------------------------------------------------------
    # Estadísticas comparativas
    # -------------------------------------------------------------

    print()
    print("=" * 80)
    print("Cobertura del vocabulario global por fuente")
    print("=" * 80)

    global_words = set(
        global_data
    )

    for source_name in SOURCE_FILES:

        source_words = set(
            source_data[source_name]
        )

        common_words = (
            global_words
            & source_words
        )

        missing_words = (
            global_words
            - source_words
        )

        coverage = (
            len(common_words)
            / len(global_words)
            if global_words
            else 0
        )

        print()
        print(source_name)
        print("-" * 80)

        print(
            f"Términos globales presentes : "
            f"{len(common_words):,}"
        )

        print(
            f"Términos globales ausentes  : "
            f"{len(missing_words):,}"
        )

        print(
            f"Cobertura vocabulario global: "
            f"{coverage:.4%}"
        )

    # -------------------------------------------------------------
    # Validación de tokens globales
    # -------------------------------------------------------------

    tokens = sorted(
        values["token"]
        for values in global_data.values()
    )

    expected_tokens = list(
        range(
            536,
            65_536,
        )
    )

    tokens_valid = (
        tokens == expected_tokens
    )

    print()
    print("=" * 80)
    print("Validación LexiMapSp-16")
    print("=" * 80)

    print(
        f"Términos              : "
        f"{len(global_data):,}"
    )

    print(
        f"Token inicial         : "
        f"{tokens[0]:,}"
    )

    print(
        f"Token final           : "
        f"{tokens[-1]:,}"
    )

    print(
        f"Secuencia continua    : "
        f"{'OK' if tokens_valid else 'ERROR'}"
    )

    if not tokens_valid:
        raise ValueError(
            "La secuencia de tokens globales "
            "no es continua entre 536 y 65,535."
        )

    print()
    print("=" * 80)
    print("Comparación finalizada")
    print("=" * 80)

    print(
        f"Archivo generado:\n"
        f"{OUTPUT_FILE}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())