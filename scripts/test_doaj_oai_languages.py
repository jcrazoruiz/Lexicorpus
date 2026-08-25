from __future__ import annotations

from collections import Counter
import xml.etree.ElementTree as ET

import requests


BASE_URL = "https://doaj.org/oai.article"

# 20 lotes x aproximadamente 300 registros
# nos permitirá inspeccionar alrededor de 6,000 artículos.
MAX_BATCHES = 20


OAI_NS = "http://www.openarchives.org/OAI/2.0/"

DOAJ_NS = "http://doaj.org/features/oai_doaj/1.0/"

NS = {
    "oai": OAI_NS,
    "doaj": DOAJ_NS,
}


def main() -> int:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "LexiCorpus/1.4"
        }
    )

    token: str | None = None

    languages = Counter()

    records_total = 0

    spanish_candidates = []

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
            f"{len(articles):,} registros"
        )

        for article in articles:
            records_total += 1

            language = (
                article.findtext(
                    "doaj:language",
                    default="",
                    namespaces=NS,
                )
                or ""
            ).strip().lower()

            languages[
                language or "(vacío)"
            ] += 1

            if language in {
                "spa",
                "es",
                "español",
                "spanish",
            }:
                title = (
                    article.findtext(
                        "doaj:title",
                        default="",
                        namespaces=NS,
                    )
                    or ""
                ).strip()

                doi = (
                    article.findtext(
                        "doaj:doi",
                        default="",
                        namespaces=NS,
                    )
                    or ""
                ).strip()

                urls = []

                for element in article.findall(
                    "doaj:fullTextUrl",
                    NS,
                ):
                    urls.append(
                        {
                            "format": (
                                element.get(
                                    "format"
                                )
                                or ""
                            ).strip(),
                            "url": (
                                element.text
                                or ""
                            ).strip(),
                        }
                    )

                spanish_candidates.append(
                    {
                        "title": title,
                        "doi": doi,
                        "urls": urls,
                    }
                )

        token_element = root.find(
            ".//oai:resumptionToken",
            NS,
        )

        token = None

        if token_element is not None:
            token = (
                token_element.text
                or ""
            ).strip()

        if not token:
            print(
                "\nNo existe otro "
                "resumptionToken."
            )
            break

    print("\nResumen")
    print("-" * 80)

    print(
        "Registros inspeccionados: "
        f"{records_total:,}"
    )

    print(
        "Idiomas encontrados     : "
        f"{languages}"
    )

    print(
        "Candidatos español      : "
        f"{len(spanish_candidates):,}"
    )

    print(
        "\nPrimeros candidatos"
    )
    print("-" * 80)

    for article in spanish_candidates[:10]:
        print(
            f"Título: {article['title']}"
        )

        print(
            f"DOI   : {article['doi']}"
        )

        print(
            f"URLs  : {article['urls']}"
        )

        print("-" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())