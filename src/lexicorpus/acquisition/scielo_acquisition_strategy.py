from __future__ import annotations

from lexicorpus.acquisition.acquisition_strategy import (
    AcquisitionResult,
    AcquisitionStrategy,
)
from lexicorpus.acquisition.scielo_harvester import (
    ScieloHarvester,
)


class ScieloAcquisitionStrategy(AcquisitionStrategy):
    """
    Adaptador entre el contrato común de adquisición
    y el harvester específico de SciELO.
    """

    def __init__(
        self,
        harvester: ScieloHarvester,
    ) -> None:
        self.harvester = harvester

    def acquire(
        self,
        maximum_documents: int | None = None,
    ) -> AcquisitionResult:

        if maximum_documents is not None:
            self.harvester.maximum_documents_to_download = (
                maximum_documents
            )

        statistics = self.harvester.run()

        return AcquisitionResult(
            inspected=statistics.inspected,
            accepted_metadata=(
                statistics.accepted_metadata
            ),
            downloaded=statistics.downloaded,
            rejected_language=(
                statistics.rejected_language
            ),
            rejected_type=statistics.rejected_type,
            rejected_without_pdf=(
                statistics.rejected_without_pdf
            ),
            download_errors=statistics.download_errors,
        )