from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests


class DownloadError(RuntimeError):
    """Error producido durante la descarga de un archivo remoto."""


class HttpDownloader:
    def __init__(
        self,
        timeout_seconds: int = 45,
        delay_seconds: float = 1.5,
        maximum_bytes: int = 50 * 1024 * 1024,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds
        self.maximum_bytes = maximum_bytes

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "LexiCorpus/1.1 "
                    "(academic corpus research)"
                ),
                "Accept": (
                    "application/pdf,"
                    "application/octet-stream;q=0.8"
                ),
            }
        )

    def download_pdf(
        self,
        url: str,
        destination_directory: Path,
        filename_stem: str,
    ) -> Path:
        destination_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        response = self.session.get(
            url,
            timeout=self.timeout_seconds,
            stream=True,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        content_length = response.headers.get(
            "Content-Length"
        )

        if (
            content_length
            and int(content_length) > self.maximum_bytes
        ):
            raise DownloadError(
                "El archivo supera el límite permitido."
            )

        temporary_path = (
            destination_directory
            / f"{filename_stem}.part"
        )

        total_bytes = 0
        digest = hashlib.sha256()

        with temporary_path.open("wb") as output_file:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if not chunk:
                    continue

                total_bytes += len(chunk)

                if total_bytes > self.maximum_bytes:
                    temporary_path.unlink(
                        missing_ok=True
                    )

                    raise DownloadError(
                        "La descarga superó el límite "
                        "máximo permitido."
                    )

                digest.update(chunk)
                output_file.write(chunk)

        with temporary_path.open("rb") as pdf_file:
            signature = pdf_file.read(5)

        if signature != b"%PDF-":
            temporary_path.unlink(
                missing_ok=True
            )

            raise DownloadError(
                "La URL no devolvió un PDF válido. "
                f"Content-Type: {content_type}"
            )

        final_path = (
            destination_directory
            / f"{filename_stem}.pdf"
        )

        temporary_path.replace(final_path)

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        return final_path