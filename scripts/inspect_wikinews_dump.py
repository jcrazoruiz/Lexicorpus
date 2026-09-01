from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://dumps.wikimedia.org/eswikinews/"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

USER_AGENT = (
    "LexiCorpus/1.5 "
    "(https://github.com/jcrazoruiz/Lexicorpus; "
    "contact: jcrazoruiz@gmail.com)"
)


def main() -> int:

    print(
        "LexiCorpus v1.5 - Inspección de dumps "
        "de Wikinoticias"
    )
    print("=" * 80)

    print("Consultando snapshots oficiales...")
    print(f"URL: {BASE_URL}")
    print()

    response = requests.get(
        BASE_URL,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=60,
    )

    response.raise_for_status()

    # Los directorios de snapshots Wikimedia
    # utilizan normalmente formato YYYYMMDD.
    snapshots = sorted(
        set(
            re.findall(
                r'href="(\d{8})/"',
                response.text,
            )
        ),
        reverse=True,
    )

    print("Snapshots detectados")
    print("-" * 80)

    if not snapshots:
        print(
            "No se encontraron snapshots "
            "con formato YYYYMMDD."
        )
        return 1

    for index, snapshot in enumerate(
        snapshots[:20],
        start=1,
    ):
        try:
            snapshot_date = datetime.strptime(
                snapshot,
                "%Y%m%d",
            ).date()

            formatted_date = (
                snapshot_date.isoformat()
            )

        except ValueError:
            formatted_date = "fecha inválida"

        print(
            f"{index:>3}. "
            f"{snapshot} | "
            f"{formatted_date}"
        )

    newest_snapshot = snapshots[0]

    snapshot_url = (
        f"{BASE_URL}{newest_snapshot}/"
    )

    print()
    print("=" * 80)
    print("Snapshot candidato")
    print("-" * 80)

    print(
        f"Snapshot más reciente : "
        f"{newest_snapshot}"
    )

    print(
        f"URL                   : "
        f"{snapshot_url}"
    )

    print()
    print(
        "Inspeccionando archivos del snapshot..."
    )

    snapshot_response = requests.get(
        snapshot_url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=60,
    )

    snapshot_response.raise_for_status()

    html = snapshot_response.text

    expected_patterns = {
        "Multistream XML": (
            rf"eswikinews-{newest_snapshot}-"
            r"pages-articles-multistream\.xml\.bz2"
        ),
        "Multistream index": (
            rf"eswikinews-{newest_snapshot}-"
            r"pages-articles-multistream-index"
            r"\.txt\.bz2"
        ),
        "MD5": (
            rf"eswikinews-{newest_snapshot}-"
            r"md5sums\.txt"
        ),
        "SHA1": (
            rf"eswikinews-{newest_snapshot}-"
            r"sha1sums\.txt"
        ),
    }

    print()
    print("Archivos requeridos")
    print("-" * 80)

    all_present = True

    for label, pattern in (
        expected_patterns.items()
    ):
        present = bool(
            re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )
        )

        state = (
            "OK"
            if present
            else "NO DETECTADO"
        )

        print(
            f"{label:<25}: {state}"
        )

        if not present:
            all_present = False

    print()
    print("=" * 80)
    print("Resultado")
    print("-" * 80)

    if all_present:
        print(
            "El snapshot contiene los archivos "
            "necesarios para continuar."
        )
        print(
            "No se descargó ningún archivo."
        )
        return 0

    print(
        "El snapshot requiere revisión antes "
        "de continuar."
    )
    print(
        "No se descargó ningún archivo."
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())