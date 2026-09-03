from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# PROYECTO
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "database"
    / "lexicorpus.db"
)

LEXICORPUS_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexicorpus"
    / "v1_5"
)

RESULTS_PATH = (
    LEXICORPUS_DIRECTORY
    / "LexiCorpus_Resultados.csv"
)

CROSS_COVERAGE_PATH = (
    LEXICORPUS_DIRECTORY
    / "LexiCorpus_Cobertura_Cruzada.csv"
)


# =============================================================================
# CARGA DE RESULTADOS PRINCIPALES
# =============================================================================

def load_main_results() -> list[dict[str, object]]:

    rows: list[dict[str, object]] = []

    with RESULTS_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required_fields = {
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
        }

        if not required_fields.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                f"{RESULTS_PATH.name} no contiene "
                f"las columnas esperadas."
            )

        for row in reader:

            rows.append(
                {
                    "source_code": (
                        row["Fuente"].strip()
                    ),
                    "lexicorpus_size": int(
                        row["TamanoSolicitado"]
                    ),
                    "vocabulary_available": int(
                        row["VocabularioDisponible"]
                    ),
                    "selected_terms": int(
                        row["TerminosSeleccionados"]
                    ),
                    "token_start": int(
                        row["TokenInicial"]
                    ),
                    "token_end": int(
                        row["TokenFinal"]
                    ),
                    "total_occurrences": int(
                        row["OcurrenciasTotales"]
                    ),
                    "covered_occurrences": int(
                        row["OcurrenciasCubiertas"]
                    ),
                    "outside_occurrences": int(
                        row["OcurrenciasFuera"]
                    ),
                    "coverage_percentage": float(
                        row["CoberturaPorcentaje"]
                    ),
                    "csv_path": (
                        row["CSV"].strip()
                    ),
                }
            )

    return rows


# =============================================================================
# CARGA DE COBERTURA CRUZADA
# =============================================================================

def load_cross_coverage() -> list[dict[str, object]]:

    rows: list[dict[str, object]] = []

    with CROSS_COVERAGE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required_fields = {
            "LexiCorpus",
            "Tamano",
            "FuenteEvaluada",
            "OcurrenciasTotales",
            "OcurrenciasCubiertas",
            "OcurrenciasFuera",
            "CoberturaPorcentaje",
        }

        if not required_fields.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                f"{CROSS_COVERAGE_PATH.name} "
                f"no contiene las columnas esperadas."
            )

        for row in reader:

            origin = (
                row["LexiCorpus"]
                .strip()
                .lower()
            )

            rows.append(
                {
                    "origin_source": origin,
                    "evaluated_source": (
                        row["FuenteEvaluada"]
                        .strip()
                    ),
                    "lexicorpus_size": int(
                        row["Tamano"]
                    ),
                    "total_occurrences": int(
                        row["OcurrenciasTotales"]
                    ),
                    "covered_occurrences": int(
                        row["OcurrenciasCubiertas"]
                    ),
                    "outside_occurrences": int(
                        row["OcurrenciasFuera"]
                    ),
                    "coverage_percentage": float(
                        row["CoberturaPorcentaje"]
                    ),
                }
            )

    return rows


# =============================================================================
# VALIDACIÓN
# =============================================================================

def validate_results(
    main_results: list[dict[str, object]],
    cross_results: list[dict[str, object]],
) -> None:

    if len(main_results) != 30:

        raise ValueError(
            f"Se esperaban 30 resultados principales "
            f"y se encontraron {len(main_results):,}."
        )

    if len(cross_results) != 30:

        raise ValueError(
            f"Se esperaban 30 resultados de cobertura "
            f"cruzada y se encontraron "
            f"{len(cross_results):,}."
        )

    main_keys = {
        (
            row["source_code"],
            row["lexicorpus_size"],
        )
        for row in main_results
    }

    if len(main_keys) != 30:

        raise ValueError(
            "Existen claves duplicadas en "
            "LexiCorpus_Resultados.csv."
        )

    cross_keys = {
        (
            row["origin_source"],
            row["evaluated_source"],
            row["lexicorpus_size"],
        )
        for row in cross_results
    }

    if len(cross_keys) != 30:

        raise ValueError(
            "Existen claves duplicadas en "
            "LexiCorpus_Cobertura_Cruzada.csv."
        )


# =============================================================================
# PERSISTENCIA
# =============================================================================

def persist_main_results(
    connection: sqlite3.Connection,
    rows: list[dict[str, object]],
    generated_at: str,
) -> None:

    sql = """
        INSERT INTO lexicorpus_result
        (
            source_code,
            lexicorpus_size,
            vocabulary_available,
            selected_terms,
            token_start,
            token_end,
            total_occurrences,
            covered_occurrences,
            outside_occurrences,
            coverage_percentage,
            csv_path,
            generated_at
        )
        VALUES
        (
            :source_code,
            :lexicorpus_size,
            :vocabulary_available,
            :selected_terms,
            :token_start,
            :token_end,
            :total_occurrences,
            :covered_occurrences,
            :outside_occurrences,
            :coverage_percentage,
            :csv_path,
            :generated_at
        )
        ON CONFLICT(
            source_code,
            lexicorpus_size
        )
        DO UPDATE SET
            vocabulary_available =
                excluded.vocabulary_available,
            selected_terms =
                excluded.selected_terms,
            token_start =
                excluded.token_start,
            token_end =
                excluded.token_end,
            total_occurrences =
                excluded.total_occurrences,
            covered_occurrences =
                excluded.covered_occurrences,
            outside_occurrences =
                excluded.outside_occurrences,
            coverage_percentage =
                excluded.coverage_percentage,
            csv_path =
                excluded.csv_path,
            generated_at =
                excluded.generated_at
    """

    for row in rows:

        parameters = dict(row)

        parameters["generated_at"] = (
            generated_at
        )

        connection.execute(
            sql,
            parameters,
        )


def persist_cross_results(
    connection: sqlite3.Connection,
    rows: list[dict[str, object]],
    generated_at: str,
) -> None:

    sql = """
        INSERT INTO lexicorpus_cross_coverage
        (
            origin_source,
            evaluated_source,
            lexicorpus_size,
            total_occurrences,
            covered_occurrences,
            outside_occurrences,
            coverage_percentage,
            generated_at
        )
        VALUES
        (
            :origin_source,
            :evaluated_source,
            :lexicorpus_size,
            :total_occurrences,
            :covered_occurrences,
            :outside_occurrences,
            :coverage_percentage,
            :generated_at
        )
        ON CONFLICT(
            origin_source,
            evaluated_source,
            lexicorpus_size
        )
        DO UPDATE SET
            total_occurrences =
                excluded.total_occurrences,
            covered_occurrences =
                excluded.covered_occurrences,
            outside_occurrences =
                excluded.outside_occurrences,
            coverage_percentage =
                excluded.coverage_percentage,
            generated_at =
                excluded.generated_at
    """

    for row in rows:

        parameters = dict(row)

        parameters["generated_at"] = (
            generated_at
        )

        connection.execute(
            sql,
            parameters,
        )


# =============================================================================
# VERIFICACIÓN POSTERIOR
# =============================================================================

def verify_database(
    connection: sqlite3.Connection,
) -> None:

    main_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM lexicorpus_result
        """
    ).fetchone()[0]

    cross_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM lexicorpus_cross_coverage
        """
    ).fetchone()[0]

    print()
    print(
        f"lexicorpus_result        : "
        f"{main_count:,} filas"
    )

    print(
        f"lexicorpus_cross_coverage: "
        f"{cross_count:,} filas"
    )

    if main_count != 30:

        raise RuntimeError(
            "lexicorpus_result no contiene "
            "exactamente 30 filas."
        )

    if cross_count != 30:

        raise RuntimeError(
            "lexicorpus_cross_coverage no contiene "
            "exactamente 30 filas."
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print()
    print("=" * 100)
    print(
        "PERSISTENCIA DE RESULTADOS "
        "LEXICORPUS v1.5"
    )
    print("=" * 100)

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{DATABASE_PATH}"
        )

    if not RESULTS_PATH.exists():

        raise FileNotFoundError(
            f"No existe: "
            f"{RESULTS_PATH}"
        )

    if not CROSS_COVERAGE_PATH.exists():

        raise FileNotFoundError(
            f"No existe: "
            f"{CROSS_COVERAGE_PATH}"
        )

    print()
    print(
        "Cargando resultados..."
    )

    main_results = (
        load_main_results()
    )

    cross_results = (
        load_cross_coverage()
    )

    print(
        f"Resultados principales  : "
        f"{len(main_results):,}"
    )

    print(
        f"Coberturas cruzadas     : "
        f"{len(cross_results):,}"
    )

    print()
    print(
        "Validando archivos..."
    )

    validate_results(
        main_results,
        cross_results,
    )

    print(
        "Validación              : OK"
    )

    generated_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )

    print()
    print(
        "Persistiendo en SQLite..."
    )

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        try:

            persist_main_results(
                connection,
                main_results,
                generated_at,
            )

            persist_cross_results(
                connection,
                cross_results,
                generated_at,
            )

            connection.commit()

            print(
                "Transacción             : COMMIT"
            )

            verify_database(
                connection
            )

        except Exception:

            connection.rollback()

            print(
                "Transacción             : ROLLBACK"
            )

            raise

    print()
    print("=" * 100)
    print(
        "PERSISTENCIA COMPLETADA"
    )
    print("=" * 100)

    print(
        "Resultados principales  : 30"
    )

    print(
        "Coberturas cruzadas     : 30"
    )

    print(
        "Estado                  : OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )