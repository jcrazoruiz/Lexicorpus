from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.extraction.extractor_factory import (
    ExtractorFactory,
)


MAPPING_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_raw_to_document_id.jsonl"
)

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "scielo"
)

EXTRACTED_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "scielo"
)


def normalize_for_comparison(
    text: str,
) -> str:
    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def similarity_key(
    text: str,
) -> str:
    normalized = normalize_for_comparison(
        text
    )

    # Usamos un fragmento grande del contenido
    # para evitar coincidencias débiles.
    return normalized[:5000]


def main() -> int:
    records = []

    with MAPPING_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line in input_file:
            records.append(
                json.loads(line)
            )

    unmatched_raw = [
        record["raw_filename"]
        for record in records
        if record["status"] == "UNMATCHED"
    ]

    matched_document_ids = {
        record["document_id"]
        for record in records
        if record["status"] == "MATCHED"
        and record["document_id"]
    }

    unmatched_extracted = [
        path
        for path in EXTRACTED_DIRECTORY.glob(
            "*.txt"
        )
        if path.stem not in matched_document_ids
    ]

    print(
        f"RAW pendientes      : "
        f"{len(unmatched_raw):,}"
    )

    print(
        f"EXTRACTED pendientes: "
        f"{len(unmatched_extracted):,}"
    )

    extracted_index = {}

    for path in unmatched_extracted:
        text = path.read_text(
            encoding="utf-8"
        )

        key = similarity_key(text)

        extracted_index.setdefault(
            key,
            [],
        ).append(path)

    factory = ExtractorFactory()

    recovered = []
    unresolved = []

    for raw_filename in unmatched_raw:
        raw_path = (
            RAW_DIRECTORY
            / raw_filename
        )

        extractor = factory.get(
            raw_path.suffix.lower()
        )

        try:
            text = extractor.extract(
                raw_path
            )

        except Exception as exc:
            unresolved.append(
                {
                    "raw_filename": raw_filename,
                    "reason": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )
            continue

        key = similarity_key(text)

        candidates = extracted_index.get(
            key,
            [],
        )

        if len(candidates) == 1:
            recovered.append(
                {
                    "raw_filename": raw_filename,
                    "document_id": (
                        candidates[0].stem
                    ),
                    "status": "RECOVERED",
                }
            )

        else:
            unresolved.append(
                {
                    "raw_filename": raw_filename,
                    "reason": (
                        f"candidates={len(candidates)}"
                    ),
                }
            )

    print("\nResultado")
    print("-" * 72)
    print(
        f"Recuperados : "
        f"{len(recovered):,}"
    )
    print(
        f"Pendientes  : "
        f"{len(unresolved):,}"
    )

    output_path = (
        PROJECT_ROOT
        / "metadata"
        / "recovery"
        / "scielo_unmatched_recovery.jsonl"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for record in recovered:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

        for record in unresolved:
            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"Archivo generado: "
        f"{output_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())