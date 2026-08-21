from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.redalyc.org/"
SEARCH_URL = urljoin(
    BASE_URL,
    "BusquedaRevistaPorNombre.oa",
)


def main() -> int:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        }
    )

    # Probamos con una letra frecuente para
    # descubrir cómo responde el buscador.
    search_term = "a"

    response = session.get(
        SEARCH_URL,
        params={
            "q": search_term,
        },
        timeout=30,
    )

    response.raise_for_status()
    response.encoding = "utf-8"

    print("\nBúsqueda de revistas RedALyC")
    print("-" * 88)

    print(
        f"Término     : {search_term}"
    )

    print(
        f"Status      : "
        f"{response.status_code}"
    )

    print(
        f"Content-Type: "
        f"{response.headers.get('Content-Type')}"
    )

    print(
        f"URL final   : "
        f"{response.url}"
    )

    print(
        f"Bytes       : "
        f"{len(response.content):,}"
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    if soup.title:
        print(
            f"Título HTML : "
            f"{soup.title.get_text(strip=True)}"
        )

    # -------------------------------------------------
    # Buscar enlaces que parezcan apuntar a revistas.
    # -------------------------------------------------

    journal_links: dict[str, str] = {}

    patterns = (
        r"revista\.oa\?id=(\d+)",
        r"idRevista=(\d+)",
        r"cveRevista[=:\"']+(\d+)",
    )

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = anchor.get(
            "href",
            "",
        ).strip()

        text = " ".join(
            anchor.get_text(
                " ",
                strip=True,
            ).split()
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                href,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            journal_id = match.group(1)

            if journal_id not in journal_links:
                journal_links[journal_id] = (
                    text
                    or "(sin nombre)"
                )

    # También inspeccionamos directamente
    # el HTML por si los IDs no están en <a>.
    html_ids: set[str] = set()

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            response.text,
            flags=re.IGNORECASE,
        ):
            html_ids.add(
                match.group(1)
            )

    print(
        "\nRevistas detectadas mediante enlaces"
    )
    print("-" * 88)

    for journal_id, name in sorted(
        journal_links.items(),
        key=lambda item: int(item[0]),
    ):
        print(
            f"{journal_id:<10} | {name}"
        )

    print("-" * 88)

    print(
        f"Revistas por enlaces: "
        f"{len(journal_links)}"
    )

    print(
        "\nIDs adicionales encontrados "
        "en el HTML"
    )
    print("-" * 88)

    additional_ids = sorted(
        html_ids - set(journal_links),
        key=int,
    )

    for journal_id in additional_ids:
        print(journal_id)

    print("-" * 88)

    print(
        f"IDs totales únicos: "
        f"{len(html_ids | set(journal_links))}"
    )

    # -------------------------------------------------
    # Buscar scripts específicos de esta página.
    # -------------------------------------------------

    scripts: list[str] = []

    for script in soup.find_all(
        "script",
        src=True,
    ):
        src = script.get(
            "src",
            "",
        ).strip()

        if not src:
            continue

        script_url = urljoin(
            response.url,
            src,
        )

        scripts.append(
            script_url
        )

    print(
        "\nScripts de la página"
    )
    print("-" * 88)

    for script_url in scripts:
        print(script_url)

    print("-" * 88)

    print(
        f"Scripts encontrados: "
        f"{len(scripts)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())