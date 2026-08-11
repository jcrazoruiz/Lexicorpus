from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LEXICAL_REPORTS = (
    PROJECT_ROOT
    / "reports"
    / "lexical"
)


def load_frequency_csv(
    path: Path,
) -> dict[str, dict[str, int | float]]:
    data: dict[str, dict[str, int | float]] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            word = row["Palabra"]

            data[word] = {
                "ranking": int(
                    row["Ranking"]
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


def main() -> int:
    literature = load_frequency_csv(
        LEXICAL_REPORTS
        / "literatura_clasica_frequency.csv"
    )

    scielo = load_frequency_csv(
        LEXICAL_REPORTS
        / "scielo_frequency.csv"
    )

    combined = load_frequency_csv(
        LEXICAL_REPORTS
        / "lexicorpus_frequency.csv"
    )

    all_words = set(combined)

    output_path = (
        LEXICAL_REPORTS
        / "lexicorpus_comparison.csv"
    )

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:
        writer = csv.writer(output_file)

        writer.writerow(
            [
                "Palabra",

                "FrecuenciaLiteratura",
                "FrecuenciaRelativaLiteratura",
                "FrecuenciaDocumentalLiteratura",
                "RankingLiteratura",

                "FrecuenciaSciELO",
                "FrecuenciaRelativaSciELO",
                "FrecuenciaDocumentalSciELO",
                "RankingSciELO",

                "FrecuenciaTotal",
                "FrecuenciaRelativaTotal",
                "FrecuenciaDocumentalTotal",
                "RankingTotal",
            ]
        )

        for word in sorted(
            all_words,
            key=lambda item: (
                -combined[item][
                    "absolute_frequency"
                ],
                item,
            ),
        ):
            literature_data = literature.get(
                word
            )

            scielo_data = scielo.get(
                word
            )

            combined_data = combined[word]

            writer.writerow(
                [
                    word,

                    (
                        literature_data["absolute_frequency"]
                        if literature_data
                        else 0
                    ),
                    (
                        literature_data["relative_frequency"]
                        if literature_data
                        else 0
                    ),
                    (
                        literature_data["document_frequency"]
                        if literature_data
                        else 0
                    ),
                    (
                        literature_data["ranking"]
                        if literature_data
                        else ""
                    ),

                    (
                        scielo_data["absolute_frequency"]
                        if scielo_data
                        else 0
                    ),
                    (
                        scielo_data["relative_frequency"]
                        if scielo_data
                        else 0
                    ),
                    (
                        scielo_data["document_frequency"]
                        if scielo_data
                        else 0
                    ),
                    (
                        scielo_data["ranking"]
                        if scielo_data
                        else ""
                    ),

                    combined_data["absolute_frequency"],
                    combined_data["relative_frequency"],
                    combined_data["document_frequency"],
                    combined_data["ranking"],
                ]
            )

    print(
        "Archivo generado:"
    )
    print(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())