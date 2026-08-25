from __future__ import annotations

import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://doaj.org/oai.article"

MAX_BATCHES = 20
MAX_CANDIDATES = 20

OAI_NS = (
    "http://www.openarchives.org/OAI/2.0/"
)

DOAJ_NS = (
    "http://doaj.org/features/oai_doaj/1.0/"
)

NS = {
    "oai": OAI_NS,
    "doaj": DOAJ_NS,
}


def clean_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value.split()
    )


def main() -> int:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.4"
            )
        }
    )

    token: str | None = None

    candidates: list[dict] = []

    for batch_number in range(
        1,
        MAX_BATCHES + 1,
    ):
        if token:
            params = {
                "verb": "ListRecords",
                "resumptionToken": token,
            }

        else:
            params = {
                "verb": "ListRecords",
                "metadataPrefix": "oai_doaj",
            }

        response = session.get(
            BASE_URL,
            params=params,
            timeout=60,
        )

        response.raise_for_status()

        root = ET.fromstring(
            response.content
        )

        articles = root.findall(
            ".//doaj:doajArticle",
            NS,
        )

        print(
            f"Lote {batch_number:>2}: "
            f"{len(articles):,}"
        )

        for article in articles:
            language = clean_text(
                article.findtext(
                    "doaj:language",
                    default="",
                    namespaces=NS,
                )
            ).lower()

            if language != "spa":
                continue

            title = clean_text(
                article.findtext(
                    "doaj:title",
                    default="",
                    namespaces=NS,
                )
            )

            journal = clean_text(
                article.findtext(
                    "doaj:journalTitle",
                    default="",
                    namespaces=NS,
                )
            )

            doi = clean_text(
                article.findtext(
                    "doaj:doi",
                    default="",
                    namespaces=NS,
                )
            )

            full_text_urls = []

            for element in article.findall(
                "doaj:fullTextUrl",
                NS,
            ):
                url = clean_text(
                    element.text
                )

                if not url:
                    continue

                full_text_urls.append(
                    {
                        "format": clean_text(
                            element.get(
                                "format"
                            )
                        ),
                        "url": url,
                    }
                )

            if not full_text_urls:
                continue

            candidates.append(
                {
                    "title": title,
                    "journal": journal,
                    "doi": doi,
                    "urls": full_text_urls,
                }
            )

            if (
                len(candidates)
                >= MAX_CANDIDATES
            ):
                break

        if (
            len(candidates)
            >= MAX_CANDIDATES
        ):
            break

        token_element = root.find(
            ".//oai:resumptionToken",
            NS,
        )

        token = None

        if token_element is not None:
            token = clean_text(
                token_element.text
            )

        if not token:
            break

    print("\nCandidatos encontrados")
    print("-" * 88)

    print(
        f"Total: {len(candidates)}"
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print("\n" + "=" * 88)

        print(
            f"CANDIDATO {index}"
        )

        print(
            f"Título DOAJ : "
            f"{candidate['title']}"
        )

        print(
            f"Revista     : "
            f"{candidate['journal']}"
        )

        print(
            f"DOI         : "
            f"{candidate['doi']}"
        )

        full_text = candidate[
            "urls"
        ][0]

        print(
            f"Formato DOAJ: "
            f"{full_text['format']}"
        )

        print(
            f"URL DOAJ    : "
            f"{full_text['url']}"
        )

        try:
            response = session.get(
                full_text["url"],
                timeout=45,
                allow_redirects=True,
            )

            print(
                f"Status      : "
                f"{response.status_code}"
            )

            print(
                f"URL final   : "
                f"{response.url}"
            )

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )

            print(
                f"Content-Type: "
                f"{content_type}"
            )

            if (
                "html"
                not in content_type.lower()
            ):
                continue

            response.encoding = (
                response.apparent_encoding
                or "utf-8"
            )

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            html_tag = soup.find(
                "html"
            )

            html_language = ""

            if html_tag:
                html_language = (
                    html_tag.get(
                        "lang",
                        "",
                    )
                    or ""
                )

            page_title = ""

            if soup.title:
                page_title = clean_text(
                    soup.title.get_text(
                        " ",
                        strip=True,
                    )
                )

            for tag in soup(
                [
                    "script",
                    "style",
                    "noscript",
                ]
            ):
                tag.decompose()

            visible_text = clean_text(
                soup.get_text(
                    " ",
                    strip=True,
                )
            )

            print(
                f"HTML lang   : "
                f"{html_language}"
            )

            print(
                f"Título HTML : "
                f"{page_title[:300]}"
            )

            print(
                f"Texto visible: "
                f"{len(visible_text):,} "
                f"caracteres"
            )

            print(
                f"Muestra     : "
                f"{visible_text[:350]}"
            )

        except requests.RequestException as exc:
            print(
                f"ERROR HTTP  : "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())