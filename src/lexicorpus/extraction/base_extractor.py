from abc import ABC, abstractmethod
from pathlib import Path


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> str:
        """Obtiene texto sin efectuar todavía la limpieza."""
        raise NotImplementedError