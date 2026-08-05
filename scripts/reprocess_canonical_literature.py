from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from lexicorpus.cleaning.canonical_cleaner import (
    CanonicalCleaner,
)
from lexicorpus.quality.quality_metrics import (
    calculate_metrics,
)
from lexicorpus.registration.hash_service import (
    HashService,
)
from lexicorpus.storage.database import Database


SOURCE_CODE = "literatura_clasica"


def main() -> int:
    cleaner = CanonicalCleaner()

    database = Database(
        PROJECT_ROOT
        / "metadata"
        / "database"
        / "lexicorpus.db"
    )

    with database.connect() as connection:
        documents = connection.execute(
            """
            SELECT
                document_id,
                original_filename,
                canonical_path
            FROM document
            WHERE source_code = ?
            AND status = 'CANONICAL'
            ORDER BY original_filename
            """,
            (SOURCE_CODE,),
        ).fetchall()

        if not documents:
            print(
                "No existen documentos canónicos "
                "para reprocesar."
            )
            return 1

        print("\nReprocesamiento canónico")
        print("-" * 80)

        for row in documents:
            normalized_path = (
                PROJECT_ROOT
                / "data"
                / "normalized"
                / SOURCE_CODE
                / f"{row['document_id']}.txt"
            )

            if not normalized_path.exists():
                print(
                    f"{row['original_filename']:<45} "
                    "ERROR: no existe normalized_path"
                )
                continue

            normalized_text = normalized_path.read_text(
                encoding="utf-8"
            )

            canonical_text = cleaner.clean(
                normalized_text
            )

            canonical_path = Path(
                row["canonical_path"]
            )

            canonical_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            canonical_path.write_text(
                canonical_text,
                encoding="utf-8",
            )

            metrics = calculate_metrics(
                canonical_text
            )

            canonical_sha256 = (
                HashService.sha256_text(
                    canonical_text
                )
            )

            connection.execute(
                """
                UPDATE document
                SET
                    canonical_sha256 = ?,
                    word_count = ?,
                    character_count = ?,
                    paragraph_count = ?,
                    updated_at = datetime('now')
                WHERE document_id = ?
                """,
                (
                    canonical_sha256,
                    metrics.word_count,
                    metrics.character_count,
                    metrics.paragraph_count,
                    row["document_id"],
                ),
            )

            print(
                f"{row['original_filename']:<45} "
                f"{metrics.word_count:>10} palabras"
            )

        connection.commit()

    print("-" * 80)
    print("Reprocesamiento completado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())