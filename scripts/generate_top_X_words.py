from __future__ import annotations

import argparse
import csv
from pathlib import Path

from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "lexicorpus_frequency.csv"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
)

RESERVED_VALUES = 535

MIN_WORDS = 1
MAX_WORDS = 65000


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Genera un diccionario candidato de palabras "
            "para LexiMapSp-16 a partir del ranking léxico."
        )
    )

    parser.add_argument(
        "--words",
        type=int,
        required=True,
        help=(
            "Número de palabras a generar. "
            "El rango válido es de 1 a 65000."
        ),
    )

    return parser.parse_args()


def normalize_word_count(
    requested_words: int,
) -> int:
    if requested_words < MIN_WORDS:
        print(
            f"Valor solicitado: {requested_words:,}. "
            f"Se ajustará al mínimo permitido: "
            f"{MIN_WORDS:,}."
        )
        return MIN_WORDS

    if requested_words > MAX_WORDS:
        print(
            f"Valor solicitado: {requested_words:,}. "
            f"Se ajustará al máximo permitido: "
            f"{MAX_WORDS:,}."
        )
        return MAX_WORDS

    return requested_words


def load_ranked_words(
    word_count: int,
) -> list[dict[str, str]]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No existe el archivo de frecuencias: "
            f"{INPUT_FILE}"
        )

    selected_rows: list[dict[str, str]] = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            ranking = int(row["Ranking"])

            if ranking > word_count:
                break

            selected_rows.append(row)

    return selected_rows


def validate_rows(
    rows: list[dict[str, str]],
    word_count: int,
) -> None:
    if len(rows) != word_count:
        raise ValueError(
            f"Se solicitaron {word_count:,} palabras, "
            f"pero se obtuvieron {len(rows):,}."
        )

    rankings = [
        int(row["Ranking"])
        for row in rows
    ]

    expected_rankings = list(
        range(
            1,
            word_count + 1,
        )
    )

    if rankings != expected_rankings:
        raise ValueError(
            "Los rankings no forman una secuencia "
            f"continua de 1 a {word_count:,}."
        )

    words = [
        row["Palabra"]
        for row in rows
    ]

    if len(words) != len(set(words)):
        raise ValueError(
            "Se detectaron palabras duplicadas "
            "en el conjunto seleccionado."
        )


def write_output(
    rows: list[dict[str, str]],
    word_count: int,
) -> Path:
    generation_date = datetime.now().strftime(
    "%Y%m%d"
)

    output_path = (
        OUTPUT_DIRECTORY
        / (
            f"lexicorpus_top_{word_count}_words_"
            f"{generation_date}.csv"
        )
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:

        writer = csv.writer(output_file)

        writer.writerow(
            [
                "Token",
                "Ranking",
                "Palabra",
                "FrecuenciaAbsoluta",
                "FrecuenciaRelativa",
                "FrecuenciaDocumental",
            ]
        )

        for row in rows:
            ranking = int(row["Ranking"])

            token = (
                RESERVED_VALUES
                + ranking
            )

            writer.writerow(
                [
                    token,
                    ranking,
                    row["Palabra"],
                    row["FrecuenciaAbsoluta"],
                    row["FrecuenciaRelativa"],
                    row["FrecuenciaDocumental"],
                ]
            )

    return output_path


def main() -> int:
    args = parse_arguments()

    word_count = normalize_word_count(
        args.words
    )

    rows = load_ranked_words(
        word_count
    )

    validate_rows(
        rows,
        word_count
    )

    output_path = write_output(
        rows,
        word_count
    )

    first_token = RESERVED_VALUES + 1
    last_token = RESERVED_VALUES + word_count

    print("\nDiccionario candidato LexiMapSp-16")
    print("-" * 72)

    print(
        f"Valores reservados     : "
        f"0 - {RESERVED_VALUES}"
    )

    print(
        f"Palabras solicitadas   : "
        f"{args.words:,}"
    )

    print(
        f"Palabras generadas     : "
        f"{word_count:,}"
    )

    print(
        f"Ranking inicial        : 1"
    )

    print(
        f"Ranking final          : "
        f"{word_count:,}"
    )

    print(
        f"Token inicial          : "
        f"{first_token:,}"
    )

    print(
        f"Token final            : "
        f"{last_token:,}"
    )

    print(
        f"Archivo generado       : "
        f"{output_path}"
    )

    print("-" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())