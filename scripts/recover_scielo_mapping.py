from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.extraction.extractor_factory import (
    ExtractorFactory,
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

OUTPUT_PATH = (
    PROJECT_ROOT
    / "metadata"
    / "recovery"
    / "scielo_raw_to_document_id.jsonl"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def build_extracted_index() -> dict[str, str]:
    index: dict[str, str] = {}

    extracted_files = sorted(
        EXTRACTED_DIRECTORY.glob("*.txt")
    )

    print(
        f"Indexando archivos EXTRACTED: "
        f"{len(extracted_files):,}"
    )

    for position, path in enumerate(
        extracted_files,
        start=1,
    ):
        text = path.read_text(
            encoding="utf-8"
        )

        text_hash = sha256_text(text)

        if text_hash in index:
            raise ValueError(
                "Se detectó un hash EXTRACTED duplicado: "
                f"{text_hash}"
            )

        index[text_hash] = path.stem

        if position % 500 == 0:
            print(
                f"  Indexados: "
                f"{position:,}"
            )

    return index


def main() -> int:
    if not RAW_DIRECTORY.exists():
        raise FileNotFoundError(
            f"No existe: {RAW_DIRECTORY}"
        )

    if not EXTRACTED_DIRECTORY.exists():
        raise FileNotFoundError(
            f"No existe: {EXTRACTED_DIRECTORY}"
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    extracted_index = build_extracted_index()

    raw_files = sorted(
        RAW_DIRECTORY.glob("*.pdf")
    )

    print(
        f"\nPDF RAW encontrados: "
        f"{len(raw_files):,}"
    )

    factory = ExtractorFactory()

    matched = 0
    unmatched = 0
    extraction_errors = 0

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        for position, raw_path in enumerate(
            raw_files,
            start=1,
        ):
            extractor = factory.get(
                raw_path.suffix.lower()
            )

            try:
                text = extractor.extract(
                    raw_path
                )

            except Exception as exc:
                extraction_errors += 1

                record = {
                    "raw_filename": raw_path.name,
                    "document_id": None,
                    "extracted_sha256": None,
                    "status": "EXTRACTION_ERROR",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }

                output_file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

                continue

            extracted_hash = sha256_text(
                text
            )

            document_id = extracted_index.get(
                extracted_hash
            )

            if document_id is None:
                unmatched += 1

                record = {
                    "raw_filename": raw_path.name,
                    "document_id": None,
                    "extracted_sha256": (
                        extracted_hash
                    ),
                    "status": "UNMATCHED",
                }

            else:
                matched += 1

                record = {
                    "raw_filename": raw_path.name,
                    "document_id": document_id,
                    "extracted_sha256": (
                        extracted_hash
                    ),
                    "status": "MATCHED",
                }

            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

            if position % 100 == 0:
                print(
                    f"Procesados: {position:,} | "
                    f"Match: {matched:,} | "
                    f"Sin match: {unmatched:,}"
                )

    print("\nResultado")
    print("-" * 72)
    print(
        f"RAW procesados : {len(raw_files):,}"
    )
    print(
        f"Coincidencias  : {matched:,}"
    )
    print(
        f"Sin coincidencia: {unmatched:,}"
    )
    print(
        f"Errores extracción: {extraction_errors:,}"
    )
    print(
        f"Archivo generado: {OUTPUT_PATH}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())