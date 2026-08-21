from __future__ import annotations

import json
import requests


ARTICLE_ID = "61544821012"

BASE_URL = "https://www.redalyc.org"

ARTICLE_ENDPOINT = (
    f"{BASE_URL}/"
    f"service/r2020/getArticleByID/{ARTICLE_ID}"
)


def main() -> int:
    response = requests.get(
        ARTICLE_ENDPOINT,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
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
        f"Bytes       : "
        f"{len(response.content):,}"
    )

    print(
        f"URL final   : "
        f"{response.url}"
    )

    if response.status_code != 200:
        return 1

    try:
        data = response.json()

    except Exception:
        print("\nRespuesta no JSON:")
        print(response.text[:2000])
        return 1

    print("\nDatos principales")
    print("-" * 80)

    fields = (
        "cveArticulo",
        "cveRevista",
        "numero",
        "nomArticulo",
        "nomRevista",
        "anioArticulo",
        "idioma",
        "paginas",
        "resumen",
        "palabras",
        "jatspdf",
    )

    for field in fields:
        value = data.get(field)

        print(
            f"{field:<20}: "
            f"{value}"
        )

    print("\nClaves disponibles")
    print("-" * 80)

    for key in sorted(data.keys()):
        print(key)

    output_path = (
        "reports/redalyc_article_api.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            data,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"\nJSON guardado en: "
        f"{output_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())