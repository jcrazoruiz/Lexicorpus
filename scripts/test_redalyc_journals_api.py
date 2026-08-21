from __future__ import annotations

from urllib.parse import quote

import requests


BASE_URL = "https://www.redalyc.org"

SEARCH_EXPRESSION = "[aA TO Zz]"
PAGE = 1
PAGE_SIZE = 15
ORDER_BY = "Nombre-0"


def main() -> int:
    encoded_expression = quote(
        SEARCH_EXPRESSION,
        safe="",
    )

    url = (
        f"{BASE_URL}/service/r2020/"
        f"getJournals/"
        f"{encoded_expression}/"
        f"{PAGE}/"
        f"{PAGE_SIZE}/"
        f"1/"
        f"{ORDER_BY}"
    )

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    response.encoding = "utf-8"

    print("\nCatálogo RedALyC")
    print("-" * 88)

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

    response.raise_for_status()

    data = response.json()

    print("\nEstructura principal")
    print("-" * 88)

    print(
        "Claves:"
    )

    for key in data.keys():
        print(
            f"  {key}"
        )

    total_results = (
        data.get("totalResultados")
        or 0
    )

    results = (
        data.get("resultados")
        or []
    )

    print("\nResumen")
    print("-" * 88)

    print(
        f"Total de revistas : "
        f"{total_results}"
    )

    print(
        f"Resultados página : "
        f"{len(results)}"
    )

    print(
        f"Página             : "
        f"{PAGE}"
    )

    print(
        f"Tamaño página      : "
        f"{PAGE_SIZE}"
    )

    print("\nPrimeras revistas")
    print("-" * 88)

    for index, journal in enumerate(
        results[:5],
        start=1,
    ):
        print(
            f"\nREVISTA {index}"
        )

        print("-" * 40)

        for key, value in journal.items():
            text = str(value)

            if len(text) > 500:
                text = (
                    text[:500]
                    + "..."
                )

            print(
                f"{key:<25}: "
                f"{text}"
            )

    print("\n" + "-" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())