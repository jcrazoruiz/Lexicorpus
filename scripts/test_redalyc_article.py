from __future__ import annotations

import requests
from bs4 import BeautifulSoup


ARTICLE_URL = (
    "https://www.redalyc.org/"
    "articulo.oa?id=61544821012"
)


def main() -> int:
    response = requests.get(
        ARTICLE_URL,
        timeout=30,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    print(f"Status      : {response.status_code}")
    print(
        "Content-Type: "
        f"{response.headers.get('Content-Type')}"
    )
    print(f"URL final   : {response.url}")
    print(f"Bytes       : {len(response.content):,}")

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    print("\nTítulo HTML:")
    print(
        soup.title.get_text(
            " ",
            strip=True,
        )
        if soup.title
        else "(sin título)"
    )

    print("\nReferencias relevantes encontradas")
    print("-" * 88)

    keywords = (
        "pdf",
        "xml",
        "jats",
        "epub",
        "download",
        "descarga",
    )

    html_lines = response.text.splitlines()

    matches = []

    for line_number, line in enumerate(
        html_lines,
        start=1,
    ):
        lower_line = line.lower()

        if any(
            keyword in lower_line
            for keyword in keywords
        ):
            clean_line = " ".join(
                line.strip().split()
            )

            matches.append(
                (
                    line_number,
                    clean_line,
                )
            )

    for line_number, line in matches:
        print(
            f"{line_number:>5}: "
            f"{line[:500]}"
        )

    print("-" * 88)
    print(
        f"Referencias encontradas: "
        f"{len(matches)}"
    )


    print("-" * 80)

    found = 0

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link["href"]

        if "pdf" in href.lower():
            found += 1

            print(href)

    print("-" * 80)
    print(f"Total: {found}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())