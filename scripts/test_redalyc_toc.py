from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


BASE_URL = "https://www.redalyc.org"

JOURNAL_ID = "615"
ISSUE_ID = "44821"

TOC_URL = (
    f"{BASE_URL}/toc.oa"
    f"?id={JOURNAL_ID}"
    f"&numero={ISSUE_ID}"
)


def main() -> int:
    response = requests.get(
        TOC_URL,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    response.encoding = "utf-8"

    print(
        f"Status      : "
        f"{response.status_code}"
    )

    print(
        f"Content-Type: "
        f"{response.headers.get('Content-Type')}"
    )

    print(
        f"Bytes       : "
        f"{len(response.content):,}"
    )

    print(
        f"URL final   : "
        f"{response.url}"
    )

    if response.status_code != 200:
        return 1

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    print("\nTítulo")
    print("-" * 80)

    if soup.title:
        print(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )
    else:
        print("(sin título)")

    print(
        "\nScripts JavaScript"
    )
    print("-" * 80)

    scripts = []

    for script in soup.find_all(
        "script",
        src=True,
    ):
        src = script.get(
            "src",
            "",
        ).strip()

        if src:
            scripts.append(src)

    for src in scripts:
        print(src)

    print("-" * 80)

    print(
        f"Scripts encontrados: "
        f"{len(scripts)}"
    )

    print(
        "\nArtículos únicos del número"
    )
    print("-" * 80)

    article_ids = set()

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link["href"].strip()

        # Solo aceptamos enlaces directos internos
        # de artículos de RedALyC.
        #
        # Esto evita contar enlaces de Facebook,
        # Twitter u otros sitios que contienen
        # "articulo.oa?id=" dentro de sus parámetros.
        if not href.startswith(
            "articulo.oa?id="
        ):
            continue

        parsed = urlparse(
            href
        )

        query = parse_qs(
            parsed.query
        )

        article_id = (
            query.get(
                "id",
                [None],
            )[0]
        )

        if article_id:
            article_ids.add(
                article_id
            )

    for article_id in sorted(
        article_ids
    ):
        print(
            article_id
        )

    print("-" * 80)

    print(
        f"Artículos únicos: "
        f"{len(article_ids)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())