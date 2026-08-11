from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OaiCheckpoint:
    last_datestamp: str | None = None


class OaiCheckpointRepository:
    """
    Persiste el punto de avance de una fuente OAI-PMH.

    El checkpoint conserva:
    - el último datestamp evaluado;
    - los identificadores ya evaluados dentro de ese mismo día.
    """

    def __init__(
        self,
        checkpoint_path: Path,
    ) -> None:
        self.checkpoint_path = checkpoint_path.resolve()

        self.checkpoint_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def load(self) -> OaiCheckpoint:
        if not self.checkpoint_path.exists():
            return OaiCheckpoint()

        content = self.checkpoint_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            return OaiCheckpoint()

        data = json.loads(content)

        return OaiCheckpoint(
            last_datestamp=data.get("last_datestamp"),
        )

    def save(
        self,
        checkpoint: OaiCheckpoint,
    ) -> None:
        content = {
            "last_datestamp": checkpoint.last_datestamp,
        }

        self.checkpoint_path.write_text(
            json.dumps(
                content,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )