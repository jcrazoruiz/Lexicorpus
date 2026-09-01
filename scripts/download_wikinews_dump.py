from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import requests


SNAPSHOT = "20260801"

BASE_URL = (
    f"https://dumps.wikimedia.org/"
    f"eswikinews/{SNAPSHOT}/"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikinews_es"
    / "wikinews_snapshot_validation.json"
)

DOWNLOAD_STATE_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikinews_es"
    / "wikinews_download_state.json"
)

DESTINATION_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikinews_es"
    / "dump"
)

USER_AGENT = (
    "LexiCorpus/1.5 "
    "(https://github.com/jcrazoruiz/Lexicorpus; "
    "contact: jcrazoruiz@gmail.com)"
)

CHUNK_SIZE = 1024 * 1024


def human_size(
    size: int,
) -> str:

    value = float(size)

    for unit in (
        "B",
        "KiB",
        "MiB",
        "GiB",
    ):
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} TiB"


def format_time(
    seconds: float,
) -> str:

    seconds = int(seconds)

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


def calculate_hashes(
    path: Path,
) -> tuple[str, str]:

    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()

    with path.open(
        "rb",
    ) as input_file:

        while True:

            chunk = input_file.read(
                CHUNK_SIZE
            )

            if not chunk:
                break

            md5_hash.update(chunk)
            sha1_hash.update(chunk)

    return (
        md5_hash.hexdigest(),
        sha1_hash.hexdigest(),
    )


def download_file(
    url: str,
    destination: Path,
    expected_size: int | None,
) -> float:

    start_time = time.monotonic()

    with requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
        },
        stream=True,
        timeout=120,
    ) as response:

        response.raise_for_status()

        total_size = (
            expected_size
            or int(
                response.headers.get(
                    "Content-Length",
                    0,
                )
            )
        )

        downloaded = 0

        temporary_path = destination.with_suffix(
            destination.suffix + ".part"
        )

        with temporary_path.open(
            "wb",
        ) as output_file:

            for chunk in response.iter_content(
                chunk_size=CHUNK_SIZE,
            ):

                if not chunk:
                    continue

                output_file.write(chunk)

                downloaded += len(chunk)

                if total_size:

                    percentage = (
                        downloaded
                        / total_size
                        * 100
                    )

                    progress = (
                        f"\rDescargando          : "
                        f"{percentage:6.2f}% "
                        f"("
                        f"{human_size(downloaded)}"
                        f" / "
                        f"{human_size(total_size)}"
                        f")"
                    )

                else:

                    progress = (
                        f"\rDescargando          : "
                        f"{human_size(downloaded)}"
                    )

                print(
                    progress,
                    end="",
                    flush=True,
                )

        print()

        temporary_path.replace(
            destination
        )

    return (
        time.monotonic()
        - start_time
    )


def load_validation() -> dict:

    if not VALIDATION_PATH.exists():

        raise FileNotFoundError(
            "No existe el archivo de validación:\n"
            f"{VALIDATION_PATH}\n\n"
            "Ejecuta primero "
            "validate_wikinews_snapshot.py"
        )

    with VALIDATION_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:

        validation = json.load(
            input_file
        )

    if (
        validation.get("snapshot")
        != SNAPSHOT
    ):
        raise RuntimeError(
            "El snapshot del archivo de validación "
            "no coincide con el esperado."
        )

    if not validation.get(
        "all_valid"
    ):
        raise RuntimeError(
            "El snapshot no fue validado "
            "correctamente."
        )

    return validation


def main() -> int:

    print(
        "LexiCorpus v1.5 - Descarga "
        "del dump Wikinoticias"
    )
    print("=" * 80)

    validation = load_validation()

    files = validation.get(
        "files",
        [],
    )

    if not files:
        raise RuntimeError(
            "El archivo de validación no "
            "contiene archivos."
        )

    DESTINATION_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    download_results = []

    print(
        f"Snapshot             : "
        f"{SNAPSHOT}"
    )

    print(
        f"Archivos             : "
        f"{len(files)}"
    )

    print(
        f"Destino              : "
        f"{DESTINATION_DIRECTORY}"
    )

    print("-" * 80)

    total_start = time.monotonic()

    for index, record in enumerate(
        files,
        start=1,
    ):

        filename = record["filename"]

        url = record["url"]

        expected_size = record.get(
            "size_bytes"
        )

        expected_md5 = record["md5"]

        expected_sha1 = record["sha1"]

        destination = (
            DESTINATION_DIRECTORY
            / filename
        )

        print()
        print(
            f"Archivo {index}/{len(files)}"
        )
        print("-" * 80)

        print(
            f"Nombre               : "
            f"{filename}"
        )

        print(
            f"Tamaño esperado      : "
            f"{human_size(expected_size)}"
            if expected_size
            else
            "Tamaño esperado      : desconocido"
        )

        print(
            f"URL                  : "
            f"{url}"
        )

        print(
            f"Destino              : "
            f"{destination}"
        )

        print()

        # Si existe un archivo anterior,
        # lo verificamos antes de descargarlo
        # nuevamente.
        if destination.exists():

            print(
                "El archivo ya existe. "
                "Verificando..."
            )

            actual_md5, actual_sha1 = (
                calculate_hashes(
                    destination
                )
            )

            if (
                actual_md5 == expected_md5
                and actual_sha1 == expected_sha1
            ):

                print(
                    "Archivo existente     : VERIFIED"
                )

                download_results.append(
                    {
                        "filename": filename,
                        "path": str(destination),
                        "size_bytes": (
                            destination.stat().st_size
                        ),
                        "md5": actual_md5,
                        "sha1": actual_sha1,
                        "status": "VERIFIED",
                        "downloaded": False,
                    }
                )

                continue

            print(
                "El archivo existente no coincide "
                "con los checksums."
            )

            print(
                "Se descargará nuevamente."
            )

            destination.unlink()

        elapsed = download_file(
            url=url,
            destination=destination,
            expected_size=expected_size,
        )

        print(
            f"Tiempo descarga      : "
            f"{format_time(elapsed)}"
        )

        actual_size = (
            destination.stat().st_size
        )

        print()
        print(
            "Calculando MD5 y SHA1..."
        )

        actual_md5, actual_sha1 = (
            calculate_hashes(
                destination
            )
        )

        md5_ok = (
            actual_md5
            == expected_md5
        )

        sha1_ok = (
            actual_sha1
            == expected_sha1
        )

        size_ok = (
            expected_size is None
            or actual_size == expected_size
        )

        print()
        print("Verificación")
        print("-" * 80)

        print(
            f"Tamaño esperado      : "
            f"{human_size(expected_size)}"
            if expected_size
            else
            "Tamaño esperado      : desconocido"
        )

        print(
            f"Tamaño obtenido      : "
            f"{human_size(actual_size)}"
        )

        print(
            f"Tamaño               : "
            f"{'OK' if size_ok else 'ERROR'}"
        )

        print()

        print(
            f"MD5 esperado         : "
            f"{expected_md5}"
        )

        print(
            f"MD5 obtenido         : "
            f"{actual_md5}"
        )

        print(
            f"MD5                  : "
            f"{'OK' if md5_ok else 'ERROR'}"
        )

        print()

        print(
            f"SHA1 esperado        : "
            f"{expected_sha1}"
        )

        print(
            f"SHA1 obtenido        : "
            f"{actual_sha1}"
        )

        print(
            f"SHA1                 : "
            f"{'OK' if sha1_ok else 'ERROR'}"
        )

        verified = (
            size_ok
            and md5_ok
            and sha1_ok
        )

        download_results.append(
            {
                "filename": filename,
                "path": str(destination),
                "size_bytes": actual_size,
                "md5": actual_md5,
                "sha1": actual_sha1,
                "status": (
                    "VERIFIED"
                    if verified
                    else "FAILED"
                ),
                "downloaded": True,
            }
        )

        if not verified:

            print()
            print(
                "ERROR: el archivo descargado "
                "no superó la verificación."
            )

            return 1

    total_elapsed = (
        time.monotonic()
        - total_start
    )

    state = {
        "lexicorpus_version": "1.5",
        "source_code": "wikinews_es",
        "source_name": (
            "Wikinoticias en español"
        ),
        "snapshot": SNAPSHOT,
        "base_url": BASE_URL,
        "files": download_results,
        "all_verified": all(
            item["status"] == "VERIFIED"
            for item in download_results
        ),
    }

    DOWNLOAD_STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DOWNLOAD_STATE_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        json.dump(
            state,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 80)
    print("Resultado")
    print("-" * 80)

    print(
        f"Snapshot             : "
        f"{SNAPSHOT}"
    )

    print(
        f"Archivos verificados : "
        f"{sum(1 for x in download_results if x['status'] == 'VERIFIED')}"
        f"/{len(download_results)}"
    )

    print(
        f"Tiempo total         : "
        f"{format_time(total_elapsed)}"
    )

    print(
        f"Estado persistido en : "
        f"{DOWNLOAD_STATE_PATH}"
    )

    print()

    print(
        "Dump de Wikinoticias descargado "
        "y verificado correctamente."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())