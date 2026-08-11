from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "lexicorpus_frequency.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
    / "lexicorpus_coverage.csv"
)


CUTOFFS = [
    10,
    50,
    100,
    128,
    512,
    1024,
    5000,
    10000,
    25000,
    50000,
    65000,
]


def main() -> int:
    rows = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            rows.append(
                {
                    "ranking": int(row["Ranking"]),
                    "word": row["Palabra"],
                    "frequency": int(
                        row["FrecuenciaAbsoluta"]
                    ),
                }
            )

    total_tokens = sum(
        row["frequency"]
        for row in rows
    )

    cumulative_frequency = 0
    cutoff_index = 0
    results = []

    for row in rows:
        cumulative_frequency += row["frequency"]

        while (
            cutoff_index < len(CUTOFFS)
            and row["ranking"] >= CUTOFFS[cutoff_index]
        ):
            cutoff = CUTOFFS[cutoff_index]

            coverage = (
                cumulative_frequency
                / total_tokens
                if total_tokens
                else 0
            )

            results.append(
                {
                    "Vocabulario": cutoff,
                    "FrecuenciaAcumulada": (
                        cumulative_frequency
                    ),
                    "Cobertura": coverage,
                }
            )

            cutoff_index += 1

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:
        writer = csv.writer(output_file)

        writer.writerow(
            [
                "Vocabulario",
                "FrecuenciaAcumulada",
                "Cobertura",
                "CoberturaPorcentaje",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result["Vocabulario"],
                    result["FrecuenciaAcumulada"],
                    f"{result['Cobertura']:.10f}",
                    f"{result['Cobertura'] * 100:.4f}",
                ]
            )

    print("\nCobertura léxica acumulada")
    print("-" * 72)

    for result in results:
        print(
            f"Top {result['Vocabulario']:>7,} "
            f"-> "
            f"{result['Cobertura'] * 100:>8.4f}%"
        )

    print("-" * 72)
    print(f"Tokens totales: {total_tokens:,}")
    print(f"Vocabulario total: {len(rows):,}")
    print(f"Archivo generado: {OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())