from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from time import perf_counter

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from lexicorpus.acquisition.acquisition_strategy_factory import (
    AcquisitionStrategyFactory,
)
from lexicorpus.config.source_registry import (
    SOURCE_REGISTRY,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Adquiere documentos desde una fuente configurada "
            "mediante la estrategia correspondiente de LexiCorpus."
        )
    )

    parser.add_argument(
        "--source",
        required=True,
        choices=sorted(SOURCE_REGISTRY.keys()),
        help="Fuente documental que se desea adquirir.",
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help=(
            "Número máximo de documentos nuevos a adquirir. "
            "Si se omite, se usa el valor definido en settings."
        ),
    )

    return parser.parse_args()


def load_source_configuration(
    source_code: str,
) -> dict:
    configuration_path = (
        PROJECT_ROOT
        / "settings"
        / "sources"
        / f"{source_code}.yaml"
    )

    if not configuration_path.exists():
        raise FileNotFoundError(
            "No existe la configuración para la fuente: "
            f"{configuration_path}"
        )

    with configuration_path.open(
        "r",
        encoding="utf-8",
    ) as configuration_file:
        configuration = yaml.safe_load(
            configuration_file
        )

    if not isinstance(configuration, dict):
        raise ValueError(
            f"La configuración de {source_code} "
            "no es válida."
        )

    source_configuration = configuration.get(
        "source"
    )

    if not isinstance(
        source_configuration,
        dict,
    ):
        raise ValueError(
            "No se encontró el bloque 'source' "
            f"en {source_code}.yaml."
        )

    return source_configuration


def format_elapsed_time(
    elapsed_seconds: float,
) -> str:
    total_seconds = int(elapsed_seconds)

    hours, remainder = divmod(
        total_seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


def main(
    source_code: str,
    maximum_documents: int | None = None,
) -> int:
    source = SOURCE_REGISTRY[source_code]

    if source.acquisition_strategy == "local":
        print(
            f"La fuente '{source.name}' "
            "no requiere adquisición remota."
        )
        return 0

    configuration = load_source_configuration(
        source_code
    )

    if not configuration.get(
        "enabled",
        False,
    ):
        print(
            f"La fuente '{source.name}' "
            "está deshabilitada."
        )
        return 1

    configured_maximum_documents = int(
        configuration["limits"][
            "maximum_documents_to_download"
        ]
    )

    effective_maximum_documents = (
        maximum_documents
        if maximum_documents is not None
        else configured_maximum_documents
    )

    strategy = (
        AcquisitionStrategyFactory.create(
            source_code=source.code,
            acquisition_strategy=(
                source.acquisition_strategy
            ),
            configuration=configuration,
            project_root=PROJECT_ROOT,
        )
    )

    started_at = datetime.now()
    timer_start = perf_counter()

    print("\nAdquisición LexiCorpus")
    print("-" * 88)
    print(f"Fuente              : {source.name}")
    print(
        "Estrategia          : "
        f"{source.acquisition_strategy}"
    )
    print(
        "Máximo documentos   : "
        f"{effective_maximum_documents}"
    )
    print(
        "Inicio              : "
        f"{started_at:%Y-%m-%d %H:%M:%S}"
    )
    print("-" * 88)

    result = strategy.acquire(
        maximum_documents=(
            effective_maximum_documents
        )
    )

    elapsed_seconds = (
        perf_counter() - timer_start
    )

    finished_at = datetime.now()

    elapsed_formatted = format_elapsed_time(
        elapsed_seconds
    )

    result_data = asdict(result)

    print("\nResultado de la adquisición")
    print("-" * 88)

    for key, value in result_data.items():
        print(f"{key:<35}: {value}")

    print("-" * 88)
    print(
        "Inicio              : "
        f"{started_at:%Y-%m-%d %H:%M:%S}"
    )
    print(
        "Finalización        : "
        f"{finished_at:%Y-%m-%d %H:%M:%S}"
    )
    print(
        "Tiempo transcurrido : "
        f"{elapsed_formatted}"
    )
    print(
        "Nuevos descargados  : "
        f"{result.downloaded}"
    )

    report_directory = (
        PROJECT_ROOT
        / "reports"
        / "acquisition"
        / source.code
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        report_directory
        / "acquisition_summary.json"
    )

    report_content = {
        "source_code": source.code,
        "source_name": source.name,
        "acquisition_strategy": (
            source.acquisition_strategy
        ),
        "maximum_documents_requested": (
            effective_maximum_documents
        ),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "elapsed_time": elapsed_formatted,
        "statistics": result_data,
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

    print("-" * 88)
    print(f"Reporte: {report_path}")

    return 0 if result.download_errors == 0 else 1


if __name__ == "__main__":
    args = parse_arguments()

    raise SystemExit(
        main(
            source_code=args.source,
            maximum_documents=(
                args.max_documents
            ),
        )
    )