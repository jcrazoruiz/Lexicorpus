from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from lexicorpus.acquisition.http_downloader import (
    HttpDownloader,
)
from lexicorpus.acquisition.oai_checkpoint_repository import OaiCheckpointRepository
from lexicorpus.acquisition.oai_pmh_client import (
    OaiPmhClient,
)
from lexicorpus.acquisition.scielo_metadata_parser import (
    ScieloMetadataParser,
)
from lexicorpus.acquisition.scielo_pdf_resolver import (
    ScieloPdfResolver,
)
from lexicorpus.acquisition.acquisition_repository import (
    AcquisitionRepository,
)
from lexicorpus.acquisition.metadata_filter import (
    MetadataFilter,
)

@dataclass(slots=True)
class HarvestStatistics:
    inspected: int = 0
    accepted_metadata: int = 0
    downloaded: int = 0
    rejected_language: int = 0
    rejected_type: int = 0
    rejected_without_pdf: int = 0
    download_errors: int = 0



class ScieloHarvester:
    def __init__(
        self,
        client: OaiPmhClient,
        parser: ScieloMetadataParser,
        downloader: HttpDownloader,
        pdf_resolver: ScieloPdfResolver,
        metadata_filter: MetadataFilter,
        acquisition_repository: AcquisitionRepository,
        checkpoint_repository: OaiCheckpointRepository,
        raw_directory: Path,
        maximum_records_to_inspect: int | None,
        maximum_documents_to_download: int,
    ) -> None:
        self.client = client
        self.parser = parser
        self.downloader = downloader
        self.pdf_resolver = pdf_resolver
        self.metadata_filter = metadata_filter
        self.acquisition_repository = acquisition_repository
        self.checkpoint_repository = checkpoint_repository
        self.raw_directory = raw_directory
        self.maximum_records_to_inspect = maximum_records_to_inspect
        self.maximum_documents_to_download = maximum_documents_to_download

    def run(self) -> HarvestStatistics:
        statistics = HarvestStatistics()

        checkpoint = self.checkpoint_repository.load()

        last_processed_datestamp = checkpoint.last_datestamp

        self.raw_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for element in self.client.list_records(
            maximum_records=(
                self.maximum_records_to_inspect
            ),
            from_date=checkpoint.last_datestamp,
        ):

            statistics.inspected += 1

            record = self.parser.parse(element)

            if record is None:
                continue

            if record.oai_datestamp:
                last_processed_datestamp = (
                    record.oai_datestamp
                )

            if self.acquisition_repository.exists_by_identifier(
                record.identifier
            ):
                continue

            filter_result = self.metadata_filter.evaluate(
                record
            )

            if not filter_result.accepted:
                record.acquisition_status = (
                    filter_result.status
                )

                record.rejection_reason = (
                    filter_result.reason
                )

                if filter_result.status == "REJECTED_LANGUAGE":
                    statistics.rejected_language += 1

                elif filter_result.status == "REJECTED_TYPE":
                    statistics.rejected_type += 1

                elif (
                    filter_result.status
                    == "REJECTED_WITHOUT_PDF"
                ):
                    statistics.rejected_without_pdf += 1

                self.acquisition_repository.save(record)
                continue

            statistics.accepted_metadata += 1

            identifier_hash = hashlib.sha256(
                record.identifier.encode("utf-8")
            ).hexdigest()[:24]

            try:
                resolved_pdf_url = self.pdf_resolver.resolve(
                    record.pdf_url or ""
                )

                record.pdf_url = resolved_pdf_url

                local_path = self.downloader.download_pdf(
                    url=resolved_pdf_url,
                    destination_directory=self.raw_directory,
                    filename_stem=identifier_hash,
                )

            except Exception as exc:
                record.acquisition_status = (
                    "DOWNLOAD_ERROR"
                )

                record.rejection_reason = (
                    f"{type(exc).__name__}: {exc}"
                )

                statistics.download_errors += 1

                self.acquisition_repository.save(record)
                continue

            record.local_path = str(local_path)
            record.acquisition_status = "DOWNLOADED"

            statistics.downloaded += 1

            self.acquisition_repository.save(record)

            if (
                statistics.downloaded
                >= self.maximum_documents_to_download
            ):
                break

        if last_processed_datestamp:
            checkpoint.last_datestamp = (
                last_processed_datestamp
            )

            self.checkpoint_repository.save(
                checkpoint
            )

        return statistics
