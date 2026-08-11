from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.consolidation.source_consolidator import (
    SourceConsolidator,
)
from lexicorpus.quality.anomaly_detector import (
    AnomalyDetector,
)
from lexicorpus.quality.editorial_validator import (
    EditorialValidator,
)
from lexicorpus.storage.database import Database
from lexicorpus.storage.editorial_repository import (
    EditorialRepository,
)


SOURCE_CODE = "literatura_clasica"
CORPUS_VERSION = "v1.0"


def load_quality_configuration() -> dict:
    configuration_path = (
        PROJECT_ROOT
        / "settings"
        / "rules"
        / "literatura_clasica_quality.yaml"
    )

    if not configuration_path.exists():
        raise FileNotFoundError(
            f"No existe la configuración: "
            f"{configuration_path}"
        )

    with configuration_path.open(
        "r",
        encoding="utf-8",
    ) as configuration_file:
        configuration = yaml.safe_load(
            configuration_file
        )

    if not configuration:
        raise ValueError(
            "El archivo de configuración está vacío."
        )

    return configuration


def get_canonical_documents(
    connection,
    source_code: str,
):
    return connection.execute(
        """
        SELECT
            document_id,
            original_filename,
            title,
            author,
            canonical_path,
            word_count,
            character_count,
            paragraph_count
        FROM document
        WHERE source_code = ?
          AND status = 'CANONICAL'
        ORDER BY original_filename
        """,
        (source_code,),
    ).fetchall()


def write_document_report(
    document_id: str,
    original_filename: str,
    anomaly_report: dict,
    validation_result: dict,
) -> Path:
    report_directory = (
        PROJECT_ROOT
        / "reports"
        / "quality"
        / SOURCE_CODE
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        report_directory
        / f"{document_id}.json"
    )

    report_content = {
        "document_id": document_id,
        "original_filename": original_filename,
        "source_code": SOURCE_CODE,
        "anomaly_report": anomaly_report,
        "editorial_validation": validation_result,
    }

    report_path.write_text(
        json.dumps(
            report_content,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return report_path


def main() -> int:
    configuration = load_quality_configuration()

    profile = configuration["profile"]
    thresholds = configuration["thresholds"]
    scoring = configuration["editorial_scoring"]

    detector = AnomalyDetector(thresholds)
    validator = EditorialValidator(
        thresholds=thresholds,
        scoring=scoring,
    )

    database = Database(
        PROJECT_ROOT
        / "metadata"
        / "database"
        / "lexicorpus.db"
    )

    database.initialize()

    approved_count = 0
    review_count = 0
    rejected_count = 0

    with database.connect() as connection:
        editorial_repository = EditorialRepository(
            connection
        )

        editorial_repository.initialize()

        documents = get_canonical_documents(
            connection,
            SOURCE_CODE,
        )

        if not documents:
            print(
                "No se encontraron documentos canónicos "
                "para literatura clásica."
            )
            return 1

        print("\nAuditoría editorial")
        print("-" * 88)

        for row in documents:
            canonical_path = Path(
                row["canonical_path"]
            )

            if not canonical_path.exists():
                print(
                    f"{row['original_filename']:<45} "
                    "ERROR: archivo canónico inexistente"
                )
                rejected_count += 1
                continue

            text = canonical_path.read_text(
                encoding="utf-8"
            )

            anomaly_report = detector.analyze(text)

            validation_result = validator.validate(
                anomaly_report
            )

            anomaly_data = anomaly_report.to_dict()
            validation_data = (
                validation_result.to_dict()
            )

            report_path = write_document_report(
                document_id=row["document_id"],
                original_filename=(
                    row["original_filename"]
                ),
                anomaly_report=anomaly_data,
                validation_result=validation_data,
            )

            editorial_repository.save_audit(
                document_id=row["document_id"],
                audit_profile=profile["code"],
                editorial_status=(
                    validation_result.status
                ),
                editorial_score=(
                    validation_result.score
                ),
                approved=validation_result.approved,
                anomaly_report=anomaly_data,
                validation_result=validation_data,
                report_path=report_path,
            )

            if validation_result.status == "APPROVED":
                approved_count += 1
            elif (
                validation_result.status
                == "REVIEW_REQUIRED"
            ):
                review_count += 1
            else:
                rejected_count += 1

            print(
                f"{row['original_filename']:<45} "
                f"{validation_result.status:<18} "
                f"{validation_result.score:>3}/100 "
                f"{len(anomaly_report.anomalies):>3} "
                "anomalías"
            )

        approved_documents = (
            editorial_repository
            .get_latest_approved_documents(
                SOURCE_CODE
            )
        )

        print("-" * 88)
        print(f"Aprobados: {approved_count}")
        print(f"Requieren revisión: {review_count}")
        print(f"Rechazados: {rejected_count}")

        if not approved_documents:
            print(
                "\nNo hay documentos aprobados. "
                "No se realizará la consolidación."
            )
            return 1

        consolidator = SourceConsolidator(
            project_root=PROJECT_ROOT,
            corpus_version=CORPUS_VERSION,
        )

        result = consolidator.consolidate(
            source_code=SOURCE_CODE,
            documents=approved_documents,
        )

    statistics = result["statistics"]

    print("\nConsolidación completada")
    print("-" * 88)
    print(
        f"Documentos consolidados: "
        f"{statistics['document_count']}"
    )
    print(
        f"Palabras consolidadas: "
        f"{statistics['total_words']:,}"
    )
    print(
        f"Caracteres consolidados: "
        f"{statistics['total_characters']:,}"
    )
    print(
        f"Promedio editorial: "
        f"{statistics['average_editorial_score']}/100"
    )
    print(
        f"Manifiesto: "
        f"{result['manifest_path']}"
    )
    print(
        f"Metadatos: "
        f"{result['metadata_path']}"
    )
    print(
        f"Estadísticas: "
        f"{result['statistics_path']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())