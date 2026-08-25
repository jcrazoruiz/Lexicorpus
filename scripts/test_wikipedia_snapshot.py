from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WIKI_CODE = "eswiki"
BASE_URL = "https://dumps.wikimedia.org"

WIKI_INDEX_URL = (
    f"{BASE_URL}/{WIKI_CODE}/"
)

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "acquisition"
    / "wikipedia"
)

MANIFEST_PATH = (
    REPORT_DIRECTORY
    / "wikipedia_dump_manifest.json"
)

OUTPUT_PATH = (
    REPORT_DIRECTORY
    / "wikipedia_snapshot_validation.json"
)

REQUEST_TIMEOUT = 60


def get_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "LexiCorpus/1.4 "
                "(Wikipedia acquisition research)"
            )
        }
    )

    return session


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "No existe el manifiesto:\n"
            f"{MANIFEST_PATH}"
        )

    return json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )


def detect_latest_snapshot(
    session: requests.Session,
) -> str:
    response = session.get(
        WIKI_INDEX_URL,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    snapshots: list[str] = []

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = (
            anchor.get("href")
            or ""
        ).strip()

        match = re.fullmatch(
            r"(\d{8})/",
            href,
        )

        if match:
            snapshots.append(
                match.group(1)
            )

    if not snapshots:
        raise ValueError(
            "No se detectaron snapshots "
            "fechados de Wikimedia."
        )

    return max(snapshots)


def download_text(
    session: requests.Session,
    url: str,
) -> str:
    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.text


def parse_checksums(
    content: str,
) -> dict[str, str]:
    result: dict[str, str] = {}

    for line in content.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 2:
            continue

        checksum = parts[0].strip()

        filename = (
            parts[-1]
            .strip()
            .lstrip("*")
        )

        result[filename] = checksum

    return result


def convert_latest_filename(
    filename: str,
    snapshot_date: str,
) -> str:
    prefix = (
        f"{WIKI_CODE}-latest-"
    )

    if not filename.startswith(
        prefix
    ):
        raise ValueError(
            "Nombre inesperado: "
            f"{filename}"
        )

    return (
        f"{WIKI_CODE}-"
        f"{snapshot_date}-"
        f"{filename[len(prefix):]}"
    )


def main() -> int:
    print()
    print(
        "LexiCorpus v1.4 - "
        "Validación del snapshot Wikipedia"
    )
    print("=" * 88)

    session = get_session()

    print(
        "Consultando snapshots oficiales..."
    )

    print(
        f"URL: {WIKI_INDEX_URL}"
    )

    try:
        snapshot_date = (
            detect_latest_snapshot(
                session
            )
        )

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        print()
        print(
            "ERROR detectando snapshot:"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    snapshot_url = (
        f"{BASE_URL}/"
        f"{WIKI_CODE}/"
        f"{snapshot_date}/"
    )

    print()
    print(
        "Snapshot detectado   : "
        f"{snapshot_date}"
    )

    print(
        "URL fija             : "
        f"{snapshot_url}"
    )

    md5_url = (
        f"{snapshot_url}"
        f"{WIKI_CODE}-"
        f"{snapshot_date}-md5sums.txt"
    )

    sha1_url = (
        f"{snapshot_url}"
        f"{WIKI_CODE}-"
        f"{snapshot_date}-sha1sums.txt"
    )

    try:
        md5_content = download_text(
            session,
            md5_url,
        )

        sha1_content = download_text(
            session,
            sha1_url,
        )

    except requests.RequestException as exc:
        print()
        print(
            "ERROR obteniendo checksums:"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    md5_checksums = parse_checksums(
        md5_content
    )

    sha1_checksums = parse_checksums(
        sha1_content
    )

    print()
    print(
        "Checksums disponibles"
    )
    print("-" * 88)

    print(
        "MD5 registrados      : "
        f"{len(md5_checksums):,}"
    )

    print(
        "SHA1 registrados     : "
        f"{len(sha1_checksums):,}"
    )

    try:
        manifest = load_manifest()

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ) as exc:
        print()
        print(
            "ERROR leyendo manifiesto:"
        )

        print(exc)

        return 1

    selected_segments = (
        manifest.get(
            "selected_segments",
            []
        )
    )

    validated_segments: list[dict] = []

    missing_checksums = 0

    print()
    print(
        "Validando segmentos seleccionados"
    )
    print("-" * 88)

    for position, segment in enumerate(
        selected_segments,
        start=1,
    ):
        latest_filename = (
            segment["filename"]
        )

        fixed_filename = (
            convert_latest_filename(
                latest_filename,
                snapshot_date,
            )
        )

        md5 = md5_checksums.get(
            fixed_filename
        )

        sha1 = sha1_checksums.get(
            fixed_filename
        )

        valid = (
            md5 is not None
            and sha1 is not None
        )

        if not valid:
            missing_checksums += 1

        fixed_url = (
            snapshot_url
            + fixed_filename
        )

        validated_segments.append(
            {
                "sequence": position,
                "start_page": (
                    segment["start_page"]
                ),
                "end_page": (
                    segment["end_page"]
                ),
                "filename": (
                    fixed_filename
                ),
                "url": fixed_url,
                "size_bytes": (
                    segment[
                        "size_bytes"
                    ]
                ),
                "md5": md5,
                "sha1": sha1,
                "checksum_available": (
                    valid
                ),
                "status": "PENDING",
            }
        )

        print(
            f"{position:>3}. "
            f"p{segment['start_page']:<8}"
            f" -> "
            f"p{segment['end_page']:<8}"
            f" | "
            f"{'OK' if valid else 'SIN CHECKSUM'}"
        )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "lexicorpus_version": "1.4",
        "source_code": (
            "wikipedia_es"
        ),
        "wiki_code": WIKI_CODE,
        "snapshot_date": (
            snapshot_date
        ),
        "snapshot_url": (
            snapshot_url
        ),
        "md5_url": md5_url,
        "sha1_url": sha1_url,
        "segment_count": (
            len(
                validated_segments
            )
        ),
        "segments_with_checksums": (
            len(validated_segments)
            - missing_checksums
        ),
        "segments_without_checksums": (
            missing_checksums
        ),
        "segments": (
            validated_segments
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 88)
    print("Resultado")
    print("-" * 88)

    print(
        "Snapshot fijado      : "
        f"{snapshot_date}"
    )

    print(
        "Segmentos            : "
        f"{len(validated_segments)}"
    )

    print(
        "Con MD5 + SHA1       : "
        f"{len(validated_segments) - missing_checksums}"
    )

    print(
        "Sin checksum         : "
        f"{missing_checksums}"
    )

    print(
        "Archivo validación   : "
        f"{OUTPUT_PATH}"
    )

    if missing_checksums:
        print()
        print(
            "ERROR: existen segmentos "
            "sin checksum oficial."
        )

        return 1

    print()
    print(
        "Snapshot fijado correctamente."
    )

    print(
        "Todavía no se descargaron "
        "archivos del dump."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())