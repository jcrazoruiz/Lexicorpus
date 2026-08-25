from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WIKIMEDIA_BASE_URL = "https://dumps.wikimedia.org"
WIKI_CODE = "eswiki"

LATEST_URL = (
    f"{WIKIMEDIA_BASE_URL}/{WIKI_CODE}/latest/"
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

REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def format_bytes(size_bytes: int) -> str:
    units = (
        "B",
        "KiB",
        "MiB",
        "GiB",
        "TiB",
    )

    size = float(size_bytes)

    for unit in units:
        if size < 1024.0:
            return f"{size:,.2f} {unit}"

        size /= 1024.0

    return f"{size:,.2f} PiB"


def get_remote_file_size(
    session: requests.Session,
    url: str,
) -> int | None:

    try:
        response = session.head(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        if response.status_code != 200:
            return None

        value = response.headers.get(
            "Content-Length"
        )

        if not value:
            return None

        return int(value)

    except (
        requests.RequestException,
        ValueError,
    ):
        return None


def extract_page_range(
    filename: str,
) -> tuple[int, int] | None:

    match = re.search(
        r"\.xml-p(\d+)p(\d+)\.bz2$",
        filename,
    )

    if not match:
        return None

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def calculate_manifest_hash(
    segments: list[dict],
) -> str:

    content = json.dumps(
        segments,
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")

    return hashlib.sha256(
        content
    ).hexdigest()


# ---------------------------------------------------------------------------
# Selección de segmentos
# ---------------------------------------------------------------------------

def select_valid_segments(
    discovered_segments: list[dict],
) -> tuple[
    list[dict],
    list[dict],
]:

    # ---------------------------------------------------------------
    # Agrupamos por página inicial.
    #
    # Si Wikimedia dejó dos archivos que comienzan exactamente
    # en la misma página, conservamos el que llegue más lejos.
    #
    # Ejemplo:
    #
    # p10294873p11545445
    # p10294873p11566741  <- conservar
    # ---------------------------------------------------------------

    by_start: dict[int, list[dict]] = {}

    for segment in discovered_segments:
        start_page = segment[
            "start_page"
        ]

        by_start.setdefault(
            start_page,
            [],
        ).append(segment)

    candidates: list[dict] = []
    rejected: list[dict] = []

    for start_page in sorted(by_start):
        group = by_start[start_page]

        group.sort(
            key=lambda item: (
                item["end_page"],
                item["size_bytes"] or 0,
            ),
            reverse=True,
        )

        selected = group[0]

        candidates.append(
            selected
        )

        for obsolete in group[1:]:
            obsolete = dict(obsolete)

            obsolete["status"] = (
                "REJECTED_OVERLAP"
            )

            obsolete["rejection_reason"] = (
                "Existe otro segmento con "
                "la misma página inicial y "
                "mayor cobertura."
            )

            rejected.append(
                obsolete
            )

    # ---------------------------------------------------------------
    # Ordenamos por rango.
    # ---------------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item["start_page"],
            item["end_page"],
        )
    )

    # ---------------------------------------------------------------
    # Validamos continuidad.
    # ---------------------------------------------------------------

    selected_segments: list[dict] = []

    expected_start = 1

    for segment in candidates:
        start_page = segment[
            "start_page"
        ]

        end_page = segment[
            "end_page"
        ]

        if start_page < expected_start:
            obsolete = dict(segment)

            obsolete["status"] = (
                "REJECTED_OVERLAP"
            )

            obsolete["rejection_reason"] = (
                "El rango se solapa con un "
                "segmento previamente "
                "seleccionado."
            )

            rejected.append(
                obsolete
            )

            continue

        if start_page > expected_start:
            raise ValueError(
                "Se detectó un hueco en los "
                "segmentos del dump. "
                f"Se esperaba p{expected_start} "
                f"pero el siguiente segmento "
                f"comienza en p{start_page}."
            )

        selected = dict(segment)

        selected["status"] = "SELECTED"

        selected_segments.append(
            selected
        )

        expected_start = (
            end_page + 1
        )

    return (
        selected_segments,
        rejected,
    )


# ---------------------------------------------------------------------------
# Descubrimiento
# ---------------------------------------------------------------------------

def discover_segmented_dump(
    session: requests.Session,
) -> tuple[
    list[dict],
    list[dict],
]:

    print(
        "Consultando índice oficial..."
    )

    print(
        f"URL: {LATEST_URL}"
    )

    response = session.get(
        LATEST_URL,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    links: set[str] = set()

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = anchor.get(
            "href",
            "",
        ).strip()

        filename = href.rsplit(
            "/",
            1,
        )[-1]

        if filename:
            links.add(filename)

    segment_pattern = re.compile(
        r"^eswiki-latest-"
        r"pages-articles-"
        r"multistream\d+"
        r"\.xml-p\d+p\d+"
        r"\.bz2$"
    )

    segment_filenames = sorted(
        filename
        for filename in links
        if segment_pattern.match(
            filename
        )
    )

    discovered_segments: list[dict] = []

    print()
    print(
        "Segmentos publicados"
    )
    print("-" * 88)

    for position, filename in enumerate(
        segment_filenames,
        start=1,
    ):
        page_range = extract_page_range(
            filename
        )

        if page_range is None:
            continue

        start_page, end_page = (
            page_range
        )

        url = urljoin(
            LATEST_URL,
            filename,
        )

        size = get_remote_file_size(
            session,
            url,
        )

        segment = {
            "discovery_sequence": position,
            "filename": filename,
            "url": url,
            "size_bytes": size,
            "start_page": start_page,
            "end_page": end_page,
            "status": "DISCOVERED",
        }

        discovered_segments.append(
            segment
        )

        size_text = (
            format_bytes(size)
            if size is not None
            else "desconocido"
        )

        print(
            f"{position:>3}. "
            f"p{start_page:<8}"
            f" -> "
            f"p{end_page:<8} | "
            f"{size_text:>12}"
        )

    return (
        discovered_segments,
        sorted(links),
    )


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

def save_manifest(
    discovered_segments: list[dict],
    selected_segments: list[dict],
    rejected_segments: list[dict],
) -> None:

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_size = sum(
        segment["size_bytes"] or 0
        for segment in selected_segments
    )

    manifest = {
        "lexicorpus_version": "1.4",
        "source_code": "wikipedia_es",
        "source_name": (
            "Wikipedia en español"
        ),
        "wiki_code": WIKI_CODE,
        "snapshot_reference": "latest",
        "dump_type": (
            "pages-articles-multistream"
        ),
        "distribution": "segmented",
        "discovery_url": LATEST_URL,
        "discovered_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "published_segment_count": (
            len(discovered_segments)
        ),
        "selected_segment_count": (
            len(selected_segments)
        ),
        "rejected_segment_count": (
            len(rejected_segments)
        ),
        "total_selected_size_bytes": (
            total_size
        ),
        "total_selected_size_human": (
            format_bytes(total_size)
        ),
        "coverage_start_page": (
            selected_segments[0][
                "start_page"
            ]
            if selected_segments
            else None
        ),
        "coverage_end_page": (
            selected_segments[-1][
                "end_page"
            ]
            if selected_segments
            else None
        ),
        "selected_segments": (
            selected_segments
        ),
        "rejected_segments": (
            rejected_segments
        ),
    }

    manifest[
        "manifest_sha256"
    ] = calculate_manifest_hash(
        selected_segments
    )

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main() -> int:

    print()
    print(
        "LexiCorpus v1.4 - "
        "Validación del dump "
        "segmentado de Wikipedia"
    )

    print("=" * 88)

    session = get_session()

    try:
        (
            discovered_segments,
            _,
        ) = discover_segmented_dump(
            session
        )

        if not discovered_segments:
            print()
            print(
                "ERROR: no se detectaron "
                "segmentos."
            )

            return 1

        (
            selected_segments,
            rejected_segments,
        ) = select_valid_segments(
            discovered_segments
        )

    except (
        requests.RequestException,
        ValueError,
    ) as exc:

        print()
        print("ERROR:")
        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    print()
    print("=" * 88)
    print(
        "Segmentos seleccionados"
    )
    print("-" * 88)

    for position, segment in enumerate(
        selected_segments,
        start=1,
    ):
        print(
            f"{position:>3}. "
            f"p{segment['start_page']:<8}"
            f" -> "
            f"p{segment['end_page']:<8}"
            f" | "
            f"{format_bytes(segment['size_bytes'] or 0):>12}"
        )

    if rejected_segments:
        print()
        print(
            "Segmentos descartados"
        )
        print("-" * 88)

        for segment in rejected_segments:
            print(
                f"p{segment['start_page']}"
                f" -> "
                f"p{segment['end_page']} "
                f"| {segment['filename']}"
            )

            print(
                "    Motivo: "
                f"{segment['rejection_reason']}"
            )

    total_size = sum(
        segment["size_bytes"] or 0
        for segment in selected_segments
    )

    print()
    print("=" * 88)
    print("Resultado")
    print("-" * 88)

    print(
        "Segmentos publicados : "
        f"{len(discovered_segments)}"
    )

    print(
        "Segmentos válidos    : "
        f"{len(selected_segments)}"
    )

    print(
        "Segmentos descartados: "
        f"{len(rejected_segments)}"
    )

    print(
        "Tamaño seleccionado  : "
        f"{format_bytes(total_size)}"
    )

    if selected_segments:
        print(
            "Cobertura            : "
            f"p{selected_segments[0]['start_page']}"
            " -> "
            f"p{selected_segments[-1]['end_page']}"
        )

    save_manifest(
        discovered_segments=(
            discovered_segments
        ),
        selected_segments=(
            selected_segments
        ),
        rejected_segments=(
            rejected_segments
        ),
    )

    print(
        "Manifiesto           : "
        f"{MANIFEST_PATH}"
    )

    print()
    print(
        "Validación completada. "
        "No se descargaron segmentos."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())