from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PRIMARY_MAPPING = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_raw_to_document_id.jsonl"
)

RECOVERED_MAPPING = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_unmatched_recovery.jsonl"
)

OUTPUT_MAPPING = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_recovery_master.jsonl"
)


def load_jsonl(
    path: Path,
) -> list[dict]:
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line in input_file:
            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def main() -> int:
    primary_records = load_jsonl(
        PRIMARY_MAPPING
    )

    recovered_records = load_jsonl(
        RECOVERED_MAPPING
    )

    recovered_by_raw = {
        record["raw_filename"]: record
        for record in recovered_records
        if record.get("status") == "RECOVERED"
    }

    master_records = []

    matched = 0
    recovered = 0
    extraction_errors = 0
    unresolved = 0

    document_ids = set()

    for record in primary_records:
        status = record.get("status")

        if status == "MATCHED":
            final_record = {
                "raw_filename": record["raw_filename"],
                "document_id": record["document_id"],
                "status": "MATCHED",
            }

            matched += 1

        elif status == "UNMATCHED":
            recovered_record = recovered_by_raw.get(
                record["raw_filename"]
            )

            if recovered_record:
                final_record = {
                    "raw_filename": record["raw_filename"],
                    "document_id": (
                        recovered_record["document_id"]
                    ),
                    "status": "RECOVERED",
                }

                recovered += 1

            else:
                final_record = {
                    "raw_filename": record["raw_filename"],
                    "document_id": None,
                    "status": "UNRESOLVED",
                }

                unresolved += 1

        elif status == "EXTRACTION_ERROR":
            final_record = {
                "raw_filename": record["raw_filename"],
                "document_id": None,
                "status": "EXTRACTION_ERROR",
                "error": record.get("error"),
            }

            extraction_errors += 1

        else:
            final_record = {
                "raw_filename": record.get(
                    "raw_filename"
                ),
                "document_id": record.get(
                    "document_id"
                ),
                "status": "UNRESOLVED",
            }

            unresolved += 1

        document_id = final_record.get(
            "document_id"
        )

        if document_id:
            if document_id in document_ids:
                raise ValueError(
                    "document_id duplicado detectado: "
                    f"{document_id}"
                )

            document_ids.add(
                document_id
            )

        master_records.append(
            final_record
        )

    with OUTPUT_MAPPING.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for record in master_records:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print("\nMapa maestro SciELO")
    print("-" * 72)
    print(
        f"RAW totales        : "
        f"{len(master_records):,}"
    )
    print(
        f"Match exacto       : "
        f"{matched:,}"
    )
    print(
        f"Recuperados        : "
        f"{recovered:,}"
    )
    print(
        f"Errores extracción : "
        f"{extraction_errors:,}"
    )
    print(
        f"Sin resolver       : "
        f"{unresolved:,}"
    )
    print(
        f"document_id únicos : "
        f"{len(document_ids):,}"
    )
    print(
        f"Archivo generado   : "
        f"{OUTPUT_MAPPING}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())