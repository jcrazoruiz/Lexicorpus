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
    / "LexiCorpus_Resultados.csv"
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

TOKEN_START = 537

LEXICORPUS_SIZES = [
    20_000,
    30_000,
    40_000,
    50_000,
    65_000,
]

SOURCES = {
    "literatura_clasica": {
        "display_name": "Literatura Clásica",
        "file_name": "Literatura_Clasica",
        "frequency_file": (
            "Literatura_Clasica_frequency_complete.csv"
        ),
    },
    "scielo": {
        "display_name": "SciELO",
        "file_name": "SciELO",
        "frequency_file": (
            "SciELO_frequency_complete.csv"
        ),
    },
    "redalyc": {
        "display_name": "RedALyC",
        "file_name": "RedALyC",
        "frequency_file": (
            "RedALyC_frequency_complete.csv"
        ),
    },
    "wikipedia_es": {
        "display_name": "Wikipedia",
        "file_name": "Wikipedia",
        "frequency_file": (
            "Wikipedia_frequency_complete.csv"
        ),
    },
    "wikinews_es": {
        "display_name": "Wikinoticias",
        "file_name": "Wikinoticias",
        "frequency_file": (
            "Wikinoticias_frequency_complete.csv"
        ),
    },
}


# =============================================================================
# ESTADÍSTICAS DE FRECUENCIA
# =============================================================================

def load_frequency_stats(
    path: Path,
) -> tuple[int, int, set[str]]:

    vocabulary: set[str] = set()

    total_occurrences = 0

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
                f"{path.name} no contiene "
                f"las columnas esperadas."
            )

        for row in reader:

            word = row["Palabra"].strip()

            frequency = int(
                row["Frecuencia"]
            )

            vocabulary.add(word)

            total_occurrences += frequency

    return (
        len(vocabulary),
        total_occurrences,
        vocabulary,
    )


def build_source_stats() -> dict[str, dict[str, int]]:

    stats: dict[str, dict[str, int]] = {}

    global_vocabulary: set[str] = set()

    global_occurrences = 0

    print()
    print(
        "CARGANDO ESTADÍSTICAS "
        "DE FRECUENCIA"
    )
    print("-" * 100)

    for source_code, config in (
        SOURCES.items()
    ):

        path = (
            LEXICAL_DIRECTORY
            / config["frequency_file"]
        )

        (
            vocabulary_available,
            total_occurrences,
            vocabulary,
        ) = load_frequency_stats(
            path
        )

        stats[source_code] = {
            "vocabulary_available": (
                vocabulary_available
            ),
            "total_occurrences": (
                total_occurrences
            ),
        }

        global_vocabulary.update(
            vocabulary
        )

        global_occurrences += (
            total_occurrences
        )

        print(
            f"{config['display_name']:<20} "
            f"{vocabulary_available:>10,} términos | "
            f"{total_occurrences:>15,} ocurrencias"
        )

    stats["completo"] = {
        "vocabulary_available": (
            len(global_vocabulary)
        ),
        "total_occurrences": (
            global_occurrences
        ),
    }

    print("-" * 100)

    print(
        f"{'Completo':<20} "
        f"{len(global_vocabulary):>10,} términos | "
        f"{global_occurrences:>15,} ocurrencias"
    )

    return stats


# =============================================================================
# LECTURA DE UN LEXICORPUS
# =============================================================================

def read_lexicorpus(
    path: Path,
) -> dict[str, int | float]:

    row_count = 0

    first_token: int | None = None
    last_token: int | None = None

    last_cumulative_frequency = 0

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required_fields = {
            "Ranking",
            "Token",
            "Palabra",
            "Frecuencia",
            "FrecuenciaAcumulada",
            "CoberturaAcumulada",
        }

        if not required_fields.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                f"{path.name} no contiene "
                f"las columnas esperadas."
            )

        expected_ranking = 1
        expected_token = TOKEN_START

        for row in reader:

            row_count += 1

            ranking = int(
                row["Ranking"]
            )

            token = int(
                row["Token"]
            )

            cumulative_frequency = int(
                row["FrecuenciaAcumulada"]
            )

            if ranking != expected_ranking:

                raise ValueError(
                    f"{path.name}: ranking inválido "
                    f"en fila {row_count:,}. "
                    f"Esperado {expected_ranking:,}, "
                    f"encontrado {ranking:,}."
                )

            if token != expected_token:

                raise ValueError(
                    f"{path.name}: token inválido "
                    f"en fila {row_count:,}. "
                    f"Esperado {expected_token:,}, "
                    f"encontrado {token:,}."
                )

            if first_token is None:
                first_token = token

            last_token = token

            last_cumulative_frequency = (
                cumulative_frequency
            )

            expected_ranking += 1
            expected_token += 1

    if row_count == 0:

        raise ValueError(
            f"{path.name} está vacío."
        )

    return {
        "selected_terms": row_count,
        "token_start": (
            first_token
            if first_token is not None
            else TOKEN_START
        ),
        "token_end": (
            last_token
            if last_token is not None
            else TOKEN_START
        ),
        "covered_occurrences": (
            last_cumulative_frequency
        ),
    }


# =============================================================================
# RUTAS DE LEXICORPUS
# =============================================================================

def get_lexicorpus_path(
    size: int,
    source_file_name: str,
) -> Path:

    return (
        LEXICORPUS_DIRECTORY
        / (
            f"LexiCorpus_{size}_"
            f"{source_file_name}.csv"
        )
    )


# =============================================================================
# GENERACIÓN DE RESULTADOS
# =============================================================================

def build_results(
    source_stats: dict[str, dict[str, int]],
) -> list[dict[str, object]]:

    results: list[dict[str, object]] = []

    source_order = list(
        SOURCES.keys()
    ) + ["completo"]

    print()
    print("=" * 100)
    print(
        "VALIDACIÓN DE LAS 30 VERSIONES "
        "LEXICORPUS"
    )
    print("=" * 100)

    for source_code in source_order:

        if source_code == "completo":

            display_name = "Completo"
            file_name = "Completo"

        else:

            config = SOURCES[
                source_code
            ]

            display_name = (
                config["display_name"]
            )

            file_name = (
                config["file_name"]
            )

        vocabulary_available = (
            source_stats[source_code][
                "vocabulary_available"
            ]
        )

        total_occurrences = (
            source_stats[source_code][
                "total_occurrences"
            ]
        )

        print()
        print(
            f"FUENTE: {display_name}"
        )
        print("-" * 100)

        for requested_size in (
            LEXICORPUS_SIZES
        ):

            path = get_lexicorpus_path(
                requested_size,
                file_name,
            )

            if not path.exists():

                raise FileNotFoundError(
                    f"No existe {path}"
                )

            lexicorpus_data = (
                read_lexicorpus(
                    path
                )
            )

            selected_terms = int(
                lexicorpus_data[
                    "selected_terms"
                ]
            )

            token_start = int(
                lexicorpus_data[
                    "token_start"
                ]
            )

            token_end = int(
                lexicorpus_data[
                    "token_end"
                ]
            )

            covered_occurrences = int(
                lexicorpus_data[
                    "covered_occurrences"
                ]
            )

            expected_selected_terms = min(
                requested_size,
                vocabulary_available,
            )

            if (
                selected_terms
                != expected_selected_terms
            ):

                raise ValueError(
                    f"{path.name}: "
                    f"{selected_terms:,} términos "
                    f"seleccionados; se esperaban "
                    f"{expected_selected_terms:,}."
                )

            expected_token_end = (
                TOKEN_START
                + selected_terms
                - 1
            )

            if token_start != TOKEN_START:

                raise ValueError(
                    f"{path.name}: "
                    f"token inicial "
                    f"{token_start:,}; "
                    f"se esperaba "
                    f"{TOKEN_START:,}."
                )

            if (
                token_end
                != expected_token_end
            ):

                raise ValueError(
                    f"{path.name}: "
                    f"token final "
                    f"{token_end:,}; "
                    f"se esperaba "
                    f"{expected_token_end:,}."
                )

            if (
                covered_occurrences
                > total_occurrences
            ):

                raise ValueError(
                    f"{path.name}: "
                    f"las ocurrencias cubiertas "
                    f"superan el total."
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

            relative_path = (
                path.relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            )

            results.append(
                {
                    "Fuente": (
                        source_code
                    ),
                    "TamanoSolicitado": (
                        requested_size
                    ),
                    "VocabularioDisponible": (
                        vocabulary_available
                    ),
                    "TerminosSeleccionados": (
                        selected_terms
                    ),
                    "TokenInicial": (
                        token_start
                    ),
                    "TokenFinal": (
                        token_end
                    ),
                    "OcurrenciasTotales": (
                        total_occurrences
                    ),
                    "OcurrenciasCubiertas": (
                        covered_occurrences
                    ),
                    "OcurrenciasFuera": (
                        outside_occurrences
                    ),
                    "CoberturaPorcentaje": (
                        f"{coverage_percentage:.6f}"
                    ),
                    "CSV": relative_path,
                }
            )

            print(
                f"{requested_size:>6,} | "
                f"seleccionados "
                f"{selected_terms:>6,} | "
                f"tokens "
                f"{token_start:>5,}-"
                f"{token_end:>6,} | "
                f"cobertura "
                f"{coverage_percentage:>10.6f}%"
            )

    return results


# =============================================================================
# ESCRITURA
# =============================================================================

def write_results(
    results: list[dict[str, object]],
) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "Fuente",
        "TamanoSolicitado",
        "VocabularioDisponible",
        "TerminosSeleccionados",
        "TokenInicial",
        "TokenFinal",
        "OcurrenciasTotales",
        "OcurrenciasCubiertas",
        "OcurrenciasFuera",
        "CoberturaPorcentaje",
        "CSV",
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
            results
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print()
    print("=" * 100)
    print(
        "GENERACIÓN DE RESULTADOS "
        "LEXICORPUS v1.5"
    )
    print("=" * 100)

    source_stats = (
        build_source_stats()
    )

    results = build_results(
        source_stats
    )

    expected_results = (
        6
        * len(
            LEXICORPUS_SIZES
        )
    )

    if len(results) != expected_results:

        raise RuntimeError(
            f"Se generaron "
            f"{len(results):,} resultados; "
            f"se esperaban "
            f"{expected_results:,}."
        )

    write_results(
        results
    )

    print()
    print("=" * 100)
    print(
        "GENERACIÓN COMPLETADA"
    )
    print("=" * 100)

    print(
        f"Resultados generados    : "
        f"{len(results):,}"
    )

    print(
        f"Resultados esperados    : "
        f"{expected_results:,}"
    )

    print(
        f"Archivo                 : "
        f"{OUTPUT_PATH.name}"
    )

    print(
        "Estado                  : OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )