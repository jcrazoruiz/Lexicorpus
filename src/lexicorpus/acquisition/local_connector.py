from collections.abc import Iterable
from pathlib import Path

from lexicorpus.acquisition.base_connector import BaseConnector
from lexicorpus.domain.document import Document


class LocalConnector(BaseConnector):
    def __init__(
        self,
        source_code: str,
        input_directory: Path,
        supported_extensions: set[str],
    ) -> None:
        self.source_code = source_code
        self.input_directory = input_directory.resolve()
        self.supported_extensions = {
            extension.lower()
            for extension in supported_extensions
        }

    def discover(self) -> Iterable[Document]:
        if not self.input_directory.exists():
            raise FileNotFoundError(
                f"No existe la carpeta de entrada: "
                f"{self.input_directory}"
            )

        for file_path in sorted(self.input_directory.rglob("*")):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.supported_extensions:
                continue

            yield Document(
                source_code=self.source_code,
                original_path=file_path,
            )