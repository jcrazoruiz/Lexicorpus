from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


BASE_URL = "https://www.redalyc.org"
JOURNAL_ID = "615"

MAX_ISSUES = 2


def get_json(url: str) -> dict:
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
    response.raise_for_status()

    return response.json()


def get_journal_issues(
    journal_id: str,
) -> list[dict]:
    url = (
        f"{BASE_URL}/service/r2020/"
        f"getJournalByID/{journal_id}"
    )

    data = get_json(url)

    anios_numeros = (
        data.get("aniosNumeros")
        or ""
    )

    issues = []

    for row in anios_numeros.split(">>>"):
        row = row.strip()

        if not row:
            continue

        elements = row.split("-")

        if len(elements) < 6:
            continue

        year = elements[0]

        for index in range(
            1,
            len(elements),
            5,
        ):
            if index + 4 >= len(elements):
                break

            issues.append(
                {
                    "year": year,
                    "volume": elements[index],
                    "issue_label": (
                        elements[index + 1]
                    ),
                    "issue_type": (
                        elements[index + 2]
                    ),
                    "issue_id": (
                        elements[index + 3]
                    ),
                    "jats_status": (
                        elements[index + 4]
                    ),
                }
            )

    return issues


def get_issue_article_ids(
    journal_id: str,
    issue_id: str,
) -> list[str]:
    url = (
        f"{BASE_URL}/toc.oa"
        f"?id={journal_id}"
        f"&numero={issue_id}"
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
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    article_ids = set()

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link["href"].strip()

        if not href.startswith(
            "articulo.oa?id="
        ):
            continue

        parsed = urlparse(href)

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

    return sorted(article_ids)


def get_article_metadata(
    article_id: str,
) -> dict:
    url = (
        f"{BASE_URL}/service/r2020/"
        f"getArticleByID/{article_id}"
    )

    return get_json(url)


def main() -> int:
    issues = get_journal_issues(
        JOURNAL_ID
    )

    print(
        f"Números disponibles: "
        f"{len(issues):,}"
    )

    selected_issues = issues[
        :MAX_ISSUES
    ]

    total_articles = 0

    for issue in selected_issues:
        print("\n" + "=" * 88)

        print(
            f"Año      : "
            f"{issue['year']}"
        )

        print(
            f"Volumen  : "
            f"{issue['volume']}"
        )

        print(
            f"Número   : "
            f"{issue['issue_label']}"
        )

        print(
            f"Clave    : "
            f"{issue['issue_id']}"
        )

        article_ids = (
            get_issue_article_ids(
                JOURNAL_ID,
                issue["issue_id"],
            )
        )

        print(
            f"Artículos: "
            f"{len(article_ids)}"
        )

        for article_id in article_ids:
            metadata = (
                get_article_metadata(
                    article_id
                )
            )

            title = (
                metadata.get("titulo")
                or "(sin título)"
            )

            language = (
                metadata.get(
                    "idiomaArticulo"
                )
                or metadata.get(
                    "cveIdioma"
                )
                or "(sin idioma)"
            )

            print(
                f"  {article_id} | "
                f"{language} | "
                f"{title}"
            )

        total_articles += len(
            article_ids
        )

    print("\n" + "-" * 88)

    print(
        f"Números inspeccionados: "
        f"{len(selected_issues)}"
    )

    print(
        f"Artículos encontrados : "
        f"{total_articles}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())