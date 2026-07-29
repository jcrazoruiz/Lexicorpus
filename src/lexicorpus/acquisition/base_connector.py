from abc import ABC, abstractmethod
from collections.abc import Iterable

from lexicorpus.domain.document import Document


class BaseConnector(ABC):
    @abstractmethod
    def discover(self) -> Iterable[Document]:
        """Descubre documentos disponibles en una fuente."""
        raise NotImplementedError