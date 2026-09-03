from __future__ import annotations

import csv
from pathlib import Path


# =============================================================================
# PROYECTO
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LEXICAL_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "v1_5"
)

LEXICORPUS_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexicorpus"
    / "v1_5"
)

OUTPUT_PATH = (
    LEXICORPUS_DIRECTORY
    / "LexiCorpus_Cobertura_Cruzada.csv"
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

LEXICORPUS_SIZES = [
    20_000,
    30_000,
    40_000,
    50_000,
    65_000,
]

SOURCE_FILES = {
    "literatura_clasica": (
        "Literatura Clásica",
        LEXICAL_DIRECTORY
        / "Literatura_Clasica_frequency_complete.csv",
    ),
    "scielo": (
        "SciELO",
        LEXICAL_DIRECTORY
        / "SciELO_frequency_complete.csv",
    ),
    "redalyc": (
        "RedALyC",
        LEXICAL_DIRECTORY
        / "RedALyC_frequency_complete.csv",
    ),
    "wikipedia_es": (
        "Wikipedia",
        LEXICAL_DIRECTORY
        / "Wikipedia_frequency_complete.csv",
    ),
    "wikinews_es": (
        "Wikinoticias",
        LEXICAL_DIRECTORY
        / "Wikinoticias_frequency_complete.csv",
    ),
}


# =============================================================================
# CARGA DE FRECUENCIAS COMPLETAS
# =============================================================================

def load_frequency_table(
    path: Path,
) -> dict[str, int]:

    frequencies: dict[str, int] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required_fields = {
            "Palabra",
            "Frecuencia",
        }

        if not required_fields.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                f"El archivo {path.name} "
                f"no contiene las columnas esperadas."
            )

        for row in reader:

            word = (
                row["Palabra"]
                .strip()
            )

            frequency = int(
                row["Frecuencia"]
            )

            frequencies[word] = frequency

    return frequencies


# =============================================================================
# CARGA DE VOCABULARIO LEXICORPUS COMPLETO
# =============================================================================

def get_complete_lexicorpus_path(
    size: int,
) -> Path:

    return (
        LEXICORPUS_DIRECTORY
        / f"LexiCorpus_{size}_Completo.csv"
    )


def load_lexicorpus_vocabulary(
    size: int,
) -> set[str]:

    path = get_complete_lexicorpus_path(
        size
    )

    vocabulary: set[str] = set()

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if "Palabra" not in (
            reader.fieldnames or []
        ):
            raise ValueError(
                f"El archivo {path.name} "
                f"no contiene la columna Palabra."
            )

        for row in reader:

            word = (
                row["Palabra"]
                .strip()
            )

            vocabulary.add(
                word
            )

    return vocabulary


# =============================================================================
# COBERTURA
# =============================================================================

def calculate_coverage(
    vocabulary: set[str],
    frequencies: dict[str, int],
) -> tuple[int, int, int, float]:

    total_occurrences = sum(
        frequencies.values()
    )

    covered_occurrences = sum(
        frequency
        for word, frequency
        in frequencies.items()
        if word in vocabulary
    )

    outside_occurrences = (
        total_occurrences
        - covered_occurrences
    )

    coverage_percentage = (
        covered_occurrences
        / total_occurrences
        * 100
        if total_occurrences
        else 0.0
    )

    return (
        total_occurrences,
        covered_occurrences,
        outside_occurrences,
        coverage_percentage,
    )


# =============================================================================
# FRECUENCIA GLOBAL
# =============================================================================

def build_global_frequency_table(
    source_frequencies: dict[
        str,
        dict[str, int],
    ],
) -> dict[str, int]:

    global_frequencies: dict[str, int] = {}

    for frequencies in (
        source_frequencies.values()
    ):

        for word, frequency in (
            frequencies.items()
        ):

            global_frequencies[word] = (
                global_frequencies.get(
                    word,
                    0,
                )
                + frequency
            )

    return global_frequencies


# =============================================================================
# SALIDA
# =============================================================================

def write_results(
    rows: list[dict[str, object]],
) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "LexiCorpus",
        "Tamano",
        "FuenteEvaluada",
        "OcurrenciasTotales",
        "OcurrenciasCubiertas",
        "OcurrenciasFuera",
        "CoberturaPorcentaje",
    ]

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print()
    print("=" * 100)
    print(
        "ANÁLISIS DE COBERTURA CRUZADA "
        "LEXICORPUS v1.5"
    )
    print("=" * 100)

    # -------------------------------------------------------------------------
    # Cargar frecuencias completas
    # -------------------------------------------------------------------------

    source_frequencies: dict[
        str,
        dict[str, int],
    ] = {}

    source_names: dict[
        str,
        str,
    ] = {}

    print()
    print(
        "CARGANDO TABLAS COMPLETAS "
        "DE FRECUENCIA"
    )
    print("-" * 100)

    for source_code, (
        source_name,
        path,
    ) in SOURCE_FILES.items():

        print(
            f"Cargando {source_name:<20}...",
            end=" ",
            flush=True,
        )

        frequencies = (
            load_frequency_table(
                path
            )
        )

        source_frequencies[
            source_code
        ] = frequencies

        source_names[
            source_code
        ] = source_name

        total_occurrences = sum(
            frequencies.values()
        )

        print(
            f"{len(frequencies):,} términos | "
            f"{total_occurrences:,} ocurrencias"
        )

    # -------------------------------------------------------------------------
    # Crear tabla global
    # -------------------------------------------------------------------------

    print()
    print(
        "Construyendo frecuencia global..."
    )

    global_frequencies = (
        build_global_frequency_table(
            source_frequencies
        )
    )

    global_total = sum(
        global_frequencies.values()
    )

    print(
        f"Vocabulario global      : "
        f"{len(global_frequencies):,}"
    )

    print(
        f"Ocurrencias globales    : "
        f"{global_total:,}"
    )

    # -------------------------------------------------------------------------
    # Calcular coberturas
    # -------------------------------------------------------------------------

    results: list[
        dict[str, object]
    ] = []

    print()
    print("=" * 100)
    print(
        "COBERTURAS"
    )
    print("=" * 100)

    for size in LEXICORPUS_SIZES:

        vocabulary = (
            load_lexicorpus_vocabulary(
                size
            )
        )

        print()
        print(
            f"LexiCorpus Completo "
            f"{size:,}"
        )
        print("-" * 100)

        if len(vocabulary) != size:

            raise ValueError(
                f"LexiCorpus_{size}_Completo.csv "
                f"contiene {len(vocabulary):,} "
                f"términos y se esperaban "
                f"{size:,}."
            )

        # ---------------------------------------------------------------------
        # Fuentes individuales
        # ---------------------------------------------------------------------

        for source_code, frequencies in (
            source_frequencies.items()
        ):

            (
                total,
                covered,
                outside,
                percentage,
            ) = calculate_coverage(
                vocabulary=vocabulary,
                frequencies=frequencies,
            )

            source_name = (
                source_names[
                    source_code
                ]
            )

            print(
                f"{source_name:<20} "
                f"{covered:>12,} / "
                f"{total:>12,} "
                f"= {percentage:>10.6f}%"
            )

            results.append(
                {
                    "LexiCorpus": (
                        "Completo"
                    ),
                    "Tamano": size,
                    "FuenteEvaluada": (
                        source_code
                    ),
                    "OcurrenciasTotales": (
                        total
                    ),
                    "OcurrenciasCubiertas": (
                        covered
                    ),
                    "OcurrenciasFuera": (
                        outside
                    ),
                    "CoberturaPorcentaje": (
                        f"{percentage:.6f}"
                    ),
                }
            )

        # ---------------------------------------------------------------------
        # Global
        # ---------------------------------------------------------------------

        (
            total,
            covered,
            outside,
            percentage,
        ) = calculate_coverage(
            vocabulary=vocabulary,
            frequencies=global_frequencies,
        )

        print(
            f"{'Completo':<20} "
            f"{covered:>12,} / "
            f"{total:>12,} "
            f"= {percentage:>10.6f}%"
        )

        results.append(
            {
                "LexiCorpus": (
                    "Completo"
                ),
                "Tamano": size,
                "FuenteEvaluada": (
                    "completo"
                ),
                "OcurrenciasTotales": (
                    total
                ),
                "OcurrenciasCubiertas": (
                    covered
                ),
                "OcurrenciasFuera": (
                    outside
                ),
                "CoberturaPorcentaje": (
                    f"{percentage:.6f}"
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Guardar
    # -------------------------------------------------------------------------

    write_results(
        results
    )

    print()
    print("=" * 100)
    print(
        "ANÁLISIS COMPLETADO"
    )
    print("=" * 100)

    print(
        f"Resultados generados    : "
        f"{len(results):,}"
    )

    print(
        f"Archivo                 : "
        f"{OUTPUT_PATH.name}"
    )

    expected_results = (
        len(LEXICORPUS_SIZES)
        * 6
    )

    print(
        f"Resultados esperados    : "
        f"{expected_results:,}"
    )

    if len(results) != expected_results:

        raise RuntimeError(
            "La cantidad de resultados "
            "no coincide con la esperada."
        )

    print(
        "Estado                  : OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )