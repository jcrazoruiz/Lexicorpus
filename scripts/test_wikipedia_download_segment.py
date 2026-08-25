from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import perf_counter

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikipedia"
    / "wikipedia_snapshot_validation.json"
)

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikipedia_es"
    / "dump"
)

STATE_PATH = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikipedia"
    / "wikipedia_download_state.json"
)

REQUEST_TIMEOUT = 120

CHUNK_SIZE = (
    1024
    * 1024
)

USER_AGENT = (
    "LexiCorpus/1.4 "
    "(https://github.com/jcrazoruiz/Lexicorpus; "
    "contact: jcrazoruiz@gmail.com)"
)


def format_bytes(
    size_bytes: int,
) -> str:
    units = (
        "B",
        "KiB",
        "MiB",
        "GiB",
        "TiB",
    )

    size = float(
        size_bytes
    )

    for unit in units:
        if size < 1024:
            return (
                f"{size:,.2f} "
                f"{unit}"
            )

        size /= 1024

    return (
        f"{size:,.2f} PiB"
    )


def format_elapsed(
    elapsed_seconds: float,
) -> str:
    total_seconds = int(
        elapsed_seconds
    )

    hours, remainder = divmod(
        total_seconds,
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


def load_validation() -> dict:
    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "No existe el archivo de validación:\n"
            f"{VALIDATION_PATH}"
        )

    return json.loads(
        VALIDATION_PATH.read_text(
            encoding="utf-8"
        )
    )


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "segments": {}
        }

    try:
        return json.loads(
            STATE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:
        return {
            "segments": {}
        }


def save_state(
    state: dict,
) -> None:
    STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    STATE_PATH.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def calculate_checksums(
    file_path: Path,
) -> tuple[
    str,
    str,
]:
    md5_hash = (
        hashlib.md5()
    )

    sha1_hash = (
        hashlib.sha1()
    )

    with file_path.open(
        "rb"
    ) as input_file:

        while True:
            block = (
                input_file.read(
                    CHUNK_SIZE
                )
            )

            if not block:
                break

            md5_hash.update(
                block
            )

            sha1_hash.update(
                block
            )

    return (
        md5_hash.hexdigest(),
        sha1_hash.hexdigest(),
    )


def build_session() -> requests.Session:
    session = (
        requests.Session()
    )

    session.headers.update(
        {
            "User-Agent": (
                USER_AGENT
            ),
            "Accept": (
                "*/*"
            ),
            "Accept-Encoding": (
                "identity"
            ),
        }
    )

    return session


def download_with_resume(
    session: requests.Session,
    url: str,
    destination: Path,
    expected_size: int | None,
) -> None:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_path = (
        destination.with_suffix(
            destination.suffix
            + ".part"
        )
    )

    existing_size = (
        partial_path.stat().st_size
        if partial_path.exists()
        else 0
    )

    request_headers = {}

    if existing_size > 0:
        request_headers[
            "Range"
        ] = (
            f"bytes={existing_size}-"
        )

        print(
            "Reanudando desde     : "
            f"{format_bytes(existing_size)}"
        )

    response = session.get(
        url,
        headers=request_headers,
        stream=True,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    try:
        # ---------------------------------------------------------
        # Si existe un parcial y Wikimedia acepta Range,
        # esperamos HTTP 206.
        #
        # Si devuelve 200, significa que el servidor está
        # entregando el archivo completo y reiniciamos desde cero.
        # ---------------------------------------------------------

        if (
            existing_size > 0
            and response.status_code
            == 200
        ):
            print(
                "Servidor no aceptó Range; "
                "reiniciando descarga."
            )

            existing_size = 0

            partial_path.unlink(
                missing_ok=True
            )

        elif (
            existing_size > 0
            and response.status_code
            != 206
        ):
            response.raise_for_status()

        else:
            response.raise_for_status()

        mode = (
            "ab"
            if existing_size > 0
            else "wb"
        )

        downloaded = (
            existing_size
        )

        last_percent = -1

        with partial_path.open(
            mode
        ) as output_file:

            for chunk in (
                response.iter_content(
                    chunk_size=(
                        CHUNK_SIZE
                    )
                )
            ):
                if not chunk:
                    continue

                output_file.write(
                    chunk
                )

                downloaded += (
                    len(chunk)
                )

                if expected_size:
                    percent = int(
                        downloaded
                        * 100
                        / expected_size
                    )

                    if (
                        percent
                        != last_percent
                    ):
                        print(
                            "\r"
                            "Descargando          : "
                            f"{percent:>3}% "
                            "("
                            f"{format_bytes(downloaded)}"
                            " / "
                            f"{format_bytes(expected_size)}"
                            ")",
                            end="",
                            flush=True,
                        )

                        last_percent = (
                            percent
                        )

    finally:
        response.close()

    print()

    if not partial_path.exists():
        raise FileNotFoundError(
            "No se generó el archivo "
            "parcial esperado."
        )

    actual_size = (
        partial_path.stat().st_size
    )

    if (
        expected_size is not None
        and actual_size
        != expected_size
    ):
        raise ValueError(
            "El tamaño descargado "
            "no coincide. "
            f"Esperado={expected_size}, "
            f"obtenido={actual_size}"
        )

    partial_path.replace(
        destination
    )


def main() -> int:
    print()
    print(
        "LexiCorpus v1.4 - "
        "Descarga piloto Wikipedia"
    )

    print("=" * 88)

    try:
        validation = (
            load_validation()
        )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"ERROR: {exc}"
        )

        return 1

    segments = (
        validation.get(
            "segments",
            [],
        )
    )

    if not segments:
        print(
            "ERROR: no existen "
            "segmentos validados."
        )

        return 1

    # ---------------------------------------------------------
    # PILOTO:
    # solamente segmento 1.
    # ---------------------------------------------------------

    segment = (
        segments[0]
    )

    filename = (
        segment["filename"]
    )

    url = (
        segment["url"]
    )

    expected_size = (
        segment.get(
            "size_bytes"
        )
    )

    expected_md5 = (
        segment.get(
            "md5"
        )
    )

    expected_sha1 = (
        segment.get(
            "sha1"
        )
    )

    destination = (
        RAW_DIRECTORY
        / filename
    )

    print(
        "Snapshot             : "
        f"{validation['snapshot_date']}"
    )

    print(
        "Segmento             : 1"
    )

    print(
        "Rango                : "
        f"p{segment['start_page']} "
        "-> "
        f"p{segment['end_page']}"
    )

    print(
        "Archivo              : "
        f"{filename}"
    )

    print(
        "URL                  : "
        f"{url}"
    )

    print(
        "Tamaño esperado      : "
        f"{format_bytes(expected_size or 0)}"
    )

    print(
        "Destino              : "
        f"{destination}"
    )

    print(
        "User-Agent           : "
        f"{USER_AGENT}"
    )

    print("-" * 88)

    state = load_state()

    state[
        "snapshot_date"
    ] = (
        validation[
            "snapshot_date"
        ]
    )

    state[
        "segments"
    ].setdefault(
        filename,
        {},
    )

    segment_state = (
        state[
            "segments"
        ][filename]
    )

    session = (
        build_session()
    )

    # ---------------------------------------------------------
    # Si el archivo ya existe,
    # no se vuelve a descargar.
    # ---------------------------------------------------------

    if destination.exists():
        print()
        print(
            "El archivo ya existe."
        )

        print(
            "Verificando integridad..."
        )

    else:
        segment_state[
            "status"
        ] = (
            "DOWNLOADING"
        )

        save_state(
            state
        )

        timer_start = (
            perf_counter()
        )

        try:
            download_with_resume(
                session=session,
                url=url,
                destination=(
                    destination
                ),
                expected_size=(
                    expected_size
                ),
            )

        except (
            requests.RequestException,
            OSError,
            ValueError,
        ) as exc:

            segment_state[
                "status"
            ] = (
                "DOWNLOAD_ERROR"
            )

            segment_state[
                "error"
            ] = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            save_state(
                state
            )

            print()
            print(
                "ERROR durante descarga:"
            )

            print(
                segment_state[
                    "error"
                ]
            )

            return 1

        elapsed = (
            perf_counter()
            - timer_start
        )

        print(
            "Tiempo descarga      : "
            f"{format_elapsed(elapsed)}"
        )

        segment_state[
            "status"
        ] = (
            "DOWNLOADED"
        )

        segment_state[
            "download_seconds"
        ] = (
            elapsed
        )

        save_state(
            state
        )

    # ---------------------------------------------------------
    # Verificación de integridad.
    # ---------------------------------------------------------

    print()
    print(
        "Calculando MD5 y SHA1..."
    )

    try:
        (
            actual_md5,
            actual_sha1,
        ) = (
            calculate_checksums(
                destination
            )
        )

    except OSError as exc:
        segment_state[
            "status"
        ] = (
            "VERIFY_ERROR"
        )

        segment_state[
            "error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        save_state(
            state
        )

        print(
            "ERROR: "
            f"{segment_state['error']}"
        )

        return 1

    md5_ok = (
        actual_md5.lower()
        == str(
            expected_md5
        ).lower()
    )

    sha1_ok = (
        actual_sha1.lower()
        == str(
            expected_sha1
        ).lower()
    )

    print()
    print(
        "Verificación"
    )

    print("-" * 88)

    print(
        "MD5 esperado         : "
        f"{expected_md5}"
    )

    print(
        "MD5 obtenido         : "
        f"{actual_md5}"
    )

    print(
        "MD5                  : "
        f"{'OK' if md5_ok else 'ERROR'}"
    )

    print()

    print(
        "SHA1 esperado        : "
        f"{expected_sha1}"
    )

    print(
        "SHA1 obtenido        : "
        f"{actual_sha1}"
    )

    print(
        "SHA1                 : "
        f"{'OK' if sha1_ok else 'ERROR'}"
    )

    segment_state.update(
        {
            "filename": (
                filename
            ),
            "url": (
                url
            ),
            "local_path": (
                str(
                    destination
                )
            ),
            "size_bytes": (
                destination.stat().st_size
            ),
            "expected_md5": (
                expected_md5
            ),
            "actual_md5": (
                actual_md5
            ),
            "expected_sha1": (
                expected_sha1
            ),
            "actual_sha1": (
                actual_sha1
            ),
            "md5_valid": (
                md5_ok
            ),
            "sha1_valid": (
                sha1_ok
            ),
        }
    )

    if (
        md5_ok
        and sha1_ok
    ):
        segment_state[
            "status"
        ] = (
            "VERIFIED"
        )

    else:
        segment_state[
            "status"
        ] = (
            "CHECKSUM_ERROR"
        )

    save_state(
        state
    )

    print()
    print("=" * 88)

    print(
        "Resultado"
    )

    print("-" * 88)

    print(
        "Estado               : "
        f"{segment_state['status']}"
    )

    print(
        "Archivo              : "
        f"{destination}"
    )

    print(
        "Tamaño               : "
        f"{format_bytes(destination.stat().st_size)}"
    )

    print(
        "Estado persistido en : "
        f"{STATE_PATH}"
    )

    if (
        segment_state[
            "status"
        ]
        != "VERIFIED"
    ):
        return 1

    print()
    print(
        "Segmento piloto descargado "
        "y verificado correctamente."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )