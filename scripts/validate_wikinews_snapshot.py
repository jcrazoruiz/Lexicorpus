from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import requests


SNAPSHOT = "20260801"

BASE_URL = (
    f"https://dumps.wikimedia.org/"
    f"eswikinews/{SNAPSHOT}/"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikinews_es"
)

REPORT_PATH = (
    REPORT_DIRECTORY
    / "wikinews_snapshot_validation.json"
)

USER_AGENT = (
    "LexiCorpus/1.5 "
    "(https://github.com/jcrazoruiz/Lexicorpus; "
    "contact: jcrazoruiz@gmail.com)"
)

XML_FILENAME = (
    f"eswikinews-{SNAPSHOT}-"
    f"pages-articles-multistream.xml.bz2"
)

INDEX_FILENAME = (
    f"eswikinews-{SNAPSHOT}-"
    f"pages-articles-multistream-index.txt.bz2"
)

MD5_FILENAME = (
    f"eswikinews-{SNAPSHOT}-md5sums.txt"
)

SHA1_FILENAME = (
    f"eswikinews-{SNAPSHOT}-sha1sums.txt"
)


def get_text(
    url: str,
) -> str:

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=60,
    )

    response.raise_for_status()

    return response.text


def parse_checksums(
    text: str,
) -> dict[str, str]:

    checksums: dict[str, str] = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 2:
            continue

        checksum = parts[0].strip()

        filename = parts[-1].strip()

        # Algunos formatos utilizan *archivo
        filename = filename.lstrip("*")

        checksums[filename] = checksum

    return checksums


def get_remote_size(
    filename: str,
) -> int | None:

    url = BASE_URL + filename

    # Intentamos HEAD primero.
    response = requests.head(
        url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=60,
        allow_redirects=True,
    )

    if response.ok:

        value = response.headers.get(
            "Content-Length"
        )

        if value and value.isdigit():
            return int(value)

    # Si HEAD no proporciona tamaño,
    # hacemos una petición parcial.
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Range": "bytes=0-0",
        },
        timeout=60,
        stream=True,
    )

    response.raise_for_status()

    content_range = response.headers.get(
        "Content-Range"
    )

    if content_range:

        match = re.search(
            r"/(\d+)$",
            content_range,
        )

        if match:
            return int(match.group(1))

    value = response.headers.get(
        "Content-Length"
    )

    if value and value.isdigit():
        return int(value)

    return None


def human_size(
    size: int | None,
) -> str:

    if size is None:
        return "desconocido"

    units = [
        "B",
        "KiB",
        "MiB",
        "GiB",
    ]

    value = float(size)

    for unit in units:

        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{size} B"


def main() -> int:

    print(
        "LexiCorpus v1.5 - Validación del "
        "snapshot Wikinoticias"
    )
    print("=" * 80)

    print(f"Snapshot             : {SNAPSHOT}")
    print(f"URL fija             : {BASE_URL}")

    print()
    print("Consultando checksums oficiales...")
    print("-" * 80)

    md5_text = get_text(
        BASE_URL + MD5_FILENAME
    )

    sha1_text = get_text(
        BASE_URL + SHA1_FILENAME
    )

    md5_checksums = parse_checksums(
        md5_text
    )

    sha1_checksums = parse_checksums(
        sha1_text
    )

    print(
        f"MD5 registrados      : "
        f"{len(md5_checksums):,}"
    )

    print(
        f"SHA1 registrados     : "
        f"{len(sha1_checksums):,}"
    )

    files = [
        XML_FILENAME,
        INDEX_FILENAME,
    ]

    validation_records = []

    print()
    print("Validando archivos requeridos")
    print("-" * 80)

    all_valid = True

    for filename in files:

        md5 = md5_checksums.get(
            filename
        )

        sha1 = sha1_checksums.get(
            filename
        )

        size = get_remote_size(
            filename
        )

        valid = (
            md5 is not None
            and sha1 is not None
        )

        if not valid:
            all_valid = False

        print()
        print(filename)

        print(
            f"  Tamaño : "
            f"{human_size(size)}"
        )

        print(
            f"  MD5    : "
            f"{md5 or 'NO DISPONIBLE'}"
        )

        print(
            f"  SHA1   : "
            f"{sha1 or 'NO DISPONIBLE'}"
        )

        print(
            f"  Estado : "
            f"{'OK' if valid else 'ERROR'}"
        )

        validation_records.append(
            {
                "filename": filename,
                "url": BASE_URL + filename,
                "size_bytes": size,
                "md5": md5,
                "sha1": sha1,
                "validated": valid,
            }
        )

    report = {
        "lexicorpus_version": "1.5",
        "source_code": "wikinews_es",
        "source_name": (
            "Wikinoticias en español"
        ),
        "snapshot": SNAPSHOT,
        "base_url": BASE_URL,
        "files": validation_records,
        "all_valid": all_valid,
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        json.dump(
            report,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 80)
    print("Resultado")
    print("-" * 80)

    print(
        f"Snapshot fijado      : "
        f"{SNAPSHOT}"
    )

    print(
        f"Archivos requeridos  : "
        f"{len(files)}"
    )

    print(
        f"Con MD5 + SHA1       : "
        f"{sum(1 for x in validation_records if x['validated'])}"
    )

    print(
        f"Archivo validación   : "
        f"{REPORT_PATH}"
    )

    print()

    if all_valid:

        print(
            "Snapshot validado correctamente."
        )

        print(
            "Todavía no se descargaron "
            "archivos del dump."
        )

        return 0

    print(
        "La validación encontró archivos "
        "sin checksums."
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())