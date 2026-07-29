import hashlib
from pathlib import Path


class HashService:
    BUFFER_SIZE = 1024 * 1024

    @classmethod
    def sha256_file(cls, file_path: Path) -> str:
        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(cls.BUFFER_SIZE):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def sha256_text(text: str) -> str:
        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()