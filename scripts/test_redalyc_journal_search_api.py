from __future__ import annotations

import requests


SCRIPT_URL = (
    "https://www.redalyc.org/"
    "js/busquedaRevistaAngularJS.js"
)


def main() -> int:
    response = requests.get(
        SCRIPT_URL,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    response.encoding = "utf-8"
    response.raise_for_status()

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

    keywords = (
        "$http",
        ".get(",
        ".post(",
        "service/",
        "/service",
        "revista",
        "journal",
        "q=",
        "buscar",
        "search",
    )

    print(
        "\nReferencias relevantes"
    )
    print("-" * 88)

    matches = []

    for line_number, line in enumerate(
        response.text.splitlines(),
        start=1,
    ):
        lower_line = line.lower()

        if any(
            keyword.lower() in lower_line
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
            f"{line[:1200]}"
        )

    print("-" * 88)

    print(
        f"Coincidencias: "
        f"{len(matches)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())