from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lexicorpus.acquisition.remote_record import RemoteRecord


class AcquisitionRepository:
    """
    Almacena los resultados de adquisición y mantiene
    la trazabilidad de cada registro remoto.
    """

    def __init__(
        self,
        metadata_directory: Path,
        source_code: str,
    ) -> None:
        self.metadata_directory = metadata_directory.resolve()
        self.source_code = source_code

        self.metadata_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.records_path = (
            self.metadata_directory
            / f"{self.source_code}_acquisition.jsonl"
        )

    def reset(self) -> None:
        self.records_path.write_text(
            "",
            encoding="utf-8",
        )

    def save(self, record: RemoteRecord) -> None:
        self._append_json(record.to_dict())

    def save_dict(
        self,
        record: dict[str, Any],
    ) -> None:
        self._append_json(record)

    def _append_json(
        self,
        record: dict[str, Any],
    ) -> None:
        with self.records_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as metadata_file:
            metadata_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def exists_by_identifier(
        self,
        identifier: str,
    ) -> bool:
        if not self.records_path.exists():
            return False

        with self.records_path.open(
            "r",
            encoding="utf-8",
        ) as metadata_file:
            for line in metadata_file:
                if not line.strip():
                    continue

                record = json.loads(line)

                if (
                    record.get("identifier")
                    == identifier
                    and record.get("acquisition_status")
                    == "DOWNLOADED"
                ):
                    return True

        return False