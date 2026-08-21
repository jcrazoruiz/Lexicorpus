from __future__ import annotations

from lexicorpus.acquisition.acquisition_strategy import (
    AcquisitionResult,
    AcquisitionStrategy,
)
from lexicorpus.acquisition.redalyc_harvester import (
    RedalycHarvester,
)


class RedalycAcquisitionStrategy(
    AcquisitionStrategy
):
    """
    Adaptador entre el contrato común de adquisición
    de LexiCorpus y el harvester específico de RedALyC.
    """

    def __init__(
        self,
        harvester: RedalycHarvester,
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
            inspected=(
                statistics.inspected_articles
            ),
            accepted_metadata=(
                statistics.accepted_metadata
            ),
            downloaded=(
                statistics.downloaded
            ),
            rejected_language=(
                statistics.rejected_language
            ),
            rejected_type=0,
            rejected_without_pdf=(
                statistics.rejected_without_pdf
            ),
            download_errors=(
                statistics.download_errors
            ),
        )