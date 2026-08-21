from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIRECTORY),
    )


from lexicorpus.acquisition.redalyc_client import (
    RedalycClient,
)


TEST_ARTICLE_ID = "61544821012"


def main() -> int:
    client = RedalycClient()

    print("\nPRUEBA 1 - Catálogo")
    print("-" * 80)

    data = client.get_journals_page()

    print(
        "Total revistas:",
        data.get("totalResultados"),
    )

    print(
        "Revistas página:",
        len(
            data.get(
                "resultados",
                [],
            )
        ),
    )

    print(
        "\nPRUEBA 2 - Primera revista utilizable"
    )
    print("-" * 80)

    first_journal = None

    for journal in client.iter_journals():
        if journal.issues:
            first_journal = journal
            break

    if first_journal is None:
        raise RuntimeError(
            "No se encontró una revista "
            "con números disponibles."
        )

    print(
        "ID      :",
        first_journal.journal_id,
    )

    print(
        "Nombre  :",
        first_journal.name,
    )

    print(
        "País    :",
        first_journal.country,
    )

    print(
        "Área    :",
        first_journal.thematic_area,
    )

    print(
        "Idioma  :",
        first_journal.language,
    )

    print(
        "Números :",
        len(first_journal.issues),
    )

    first_issue = (
        first_journal.issues[0]
    )

    print(
        "\nPrimer número:",
        first_issue,
    )

    print(
        "\nPRUEBA 3 - Artículos del número"
    )
    print("-" * 80)

    article_ids = (
        client.get_issue_article_ids(
            journal_id=(
                first_journal.journal_id
            ),
            issue_id=(
                first_issue.issue_id
            ),
        )
    )

    print(
        "Artículos encontrados:",
        len(article_ids),
    )

    for article_id in article_ids[:5]:
        print(article_id)

    print(
        "\nPRUEBA 4 - Artículo conocido"
    )
    print("-" * 80)

    article = client.get_article(
        TEST_ARTICLE_ID
    )

    print(
        "ID      :",
        article.get("cveArticulo"),
    )

    print(
        "Revista :",
        article.get("nomRevista"),
    )

    print(
        "Idioma  :",
        article.get("idiomaArticulo"),
    )

    print(
        "Título  :",
        article.get("titulo"),
    )

    print(
        "\nPRUEBA 5 - PDF"
    )
    print("-" * 80)

    pdf_url = client.get_pdf_url(
        article
    )

    print(
        "PDF URL :",
        pdf_url,
    )

    if not pdf_url:
        raise RuntimeError(
            "No fue posible resolver el PDF."
        )

    pdf_content = (
        client.download_pdf(
            pdf_url
        )
    )

    print(
        "PDF bytes:",
        f"{len(pdf_content):,}",
    )

    print(
        "\nTODAS LAS PRUEBAS COMPLETADAS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())