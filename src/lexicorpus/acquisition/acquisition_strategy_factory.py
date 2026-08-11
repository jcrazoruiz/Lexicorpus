from __future__ import annotations

from pathlib import Path

from lexicorpus.acquisition.acquisition_repository import (
    AcquisitionRepository,
)
from lexicorpus.acquisition.acquisition_strategy import (
    AcquisitionStrategy,
)
from lexicorpus.acquisition.http_downloader import (
    HttpDownloader,
)
from lexicorpus.acquisition.metadata_filter import (
    MetadataFilter,
)
from lexicorpus.acquisition.oai_checkpoint_repository import (
    OaiCheckpointRepository,
)
from lexicorpus.acquisition.oai_pmh_client import (
    OaiPmhClient,
)
from lexicorpus.acquisition.scielo_acquisition_strategy import (
    ScieloAcquisitionStrategy,
)
from lexicorpus.acquisition.scielo_harvester import (
    ScieloHarvester,
)
from lexicorpus.acquisition.scielo_metadata_parser import (
    ScieloMetadataParser,
)
from lexicorpus.acquisition.scielo_pdf_resolver import (
    ScieloPdfResolver,
)


class AcquisitionStrategyFactory:
    """
    Construye la estrategia de adquisición correspondiente
    a una fuente documental.
    """

    @staticmethod
    def create(
        source_code: str,
        acquisition_strategy: str,
        configuration: dict,
        project_root: Path,
    ) -> AcquisitionStrategy:

        if acquisition_strategy == "oai_pmh":
            return (
                AcquisitionStrategyFactory
                ._create_oai_pmh_strategy(
                    source_code=source_code,
                    configuration=configuration,
                    project_root=project_root,
                )
            )

        raise ValueError(
            "Estrategia de adquisición no soportada: "
            f"{acquisition_strategy}"
        )

    @staticmethod
    def _create_oai_pmh_strategy(
        source_code: str,
        configuration: dict,
        project_root: Path,
    ) -> AcquisitionStrategy:

        if source_code != "scielo":
            raise ValueError(
                "Actualmente la estrategia OAI-PMH "
                "solo está implementada para SciELO."
            )

        limits = configuration["limits"]
        storage = configuration["storage"]
        filters = configuration["filters"]

        request_delay = float(
            limits["delay_between_requests_seconds"]
        )

        client = OaiPmhClient(
            base_url=configuration["oai_base_url"],
            metadata_prefix=configuration.get(
                "metadata_prefix",
                "oai_dc",
            ),
            timeout_seconds=int(
                limits["request_timeout_seconds"]
            ),
            delay_seconds=request_delay,
        )

        acquisition_repository = (
            AcquisitionRepository(
                metadata_directory=(
                    project_root
                    / storage["metadata_directory"]
                ),
                source_code=source_code,
            )
        )

        checkpoint_repository = (
            OaiCheckpointRepository(
                checkpoint_path=(
                    project_root
                    / storage["metadata_directory"]
                    / "checkpoint.json"
                )
            )
        )

        harvester = ScieloHarvester(
            client=client,
            parser=ScieloMetadataParser(),
            downloader=HttpDownloader(
                timeout_seconds=int(
                    limits[
                        "request_timeout_seconds"
                    ]
                ),
                delay_seconds=request_delay,
            ),
            pdf_resolver=ScieloPdfResolver(
                timeout_seconds=int(
                    limits[
                        "request_timeout_seconds"
                    ]
                ),
            ),
            metadata_filter=MetadataFilter(
                accepted_languages=set(
                    filters["accepted_languages"]
                ),
                accepted_resource_types=set(
                    filters[
                        "accepted_resource_types"
                    ]
                ),
                require_pdf=bool(
                    filters.get(
                        "require_pdf",
                        True,
                    )
                ),
            ),
            acquisition_repository=(
                acquisition_repository
            ),
            checkpoint_repository=(
                checkpoint_repository
            ),
            raw_directory=(
                project_root
                / storage["raw_directory"]
            ),
            maximum_records_to_inspect=(
                int(
                    limits[
                        "maximum_records_to_inspect"
                    ]
                )
                if limits.get(
                    "maximum_records_to_inspect"
                )
                is not None
                else None
            ),
            maximum_documents_to_download=int(
                limits[
                    "maximum_documents_to_download"
                ]
            ),
        )

        return ScieloAcquisitionStrategy(
            harvester=harvester
        )