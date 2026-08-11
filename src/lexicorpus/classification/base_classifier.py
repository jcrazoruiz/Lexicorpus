from __future__ import annotations

from abc import ABC, abstractmethod

from lexicorpus.domain.document import Document


class BaseClassifier(ABC):
    """
    Contrato común para los componentes que enriquecen
    y clasifican documentos dentro de LexiCorpus.
    """

    @abstractmethod
    def classify(
        self,
        document: Document,
    ) -> None:
        """
        Clasifica y enriquece los metadatos del documento.
        """
        raise NotImplementedError