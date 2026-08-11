from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class AcquisitionResult:
    inspected: int = 0
    accepted_metadata: int = 0
    downloaded: int = 0
    rejected_language: int = 0
    rejected_type: int = 0
    rejected_without_pdf: int = 0
    download_errors: int = 0


class AcquisitionStrategy(ABC):
    """
    Contrato común para las estrategias de adquisición
    documental de LexiCorpus.
    """

    @abstractmethod
    def acquire(
        self,
        maximum_documents: int | None = None,
    ) -> AcquisitionResult:
        """
        Ejecuta la adquisición de documentos nuevos.

        maximum_documents representa el número máximo de
        documentos nuevos que se desea adquirir.
        """
        raise NotImplementedError