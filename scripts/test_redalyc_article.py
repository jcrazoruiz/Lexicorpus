from __future__ import annotations

from pathlib import Path

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

    pdf_meta = soup.find(
        "meta",
        attrs={
            "name": "citation_pdf_url",
        },
    )

    print("\nPDF detectado")
    print("-" * 80)

    if pdf_meta is None:
        print(
            "No se encontró "
            "citation_pdf_url."
        )

    else:
        pdf_url = pdf_meta.get(
            "content"
        )

    print(
        f"URL PDF: {pdf_url}"
    )

    pdf_response = requests.get(
        pdf_url,
        timeout=30,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    print(
        f"Status      : "
        f"{pdf_response.status_code}"
    )

    print(
        f"Content-Type: "
        f"{pdf_response.headers.get('Content-Type')}"
    )

    print(
        f"Bytes       : "
        f"{len(pdf_response.content):,}"
    )

    print(
        f"URL final   : "
        f"{pdf_response.url}"
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

    output_path = (
        Path(__file__).resolve().parents[1]
        / "reports"
        / "redalyc_html_references.txt"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for line_number, line in matches:
            output_file.write(
                f"{line_number}: {line}\n"
            )

    print(
        f"\nReferencias guardadas en: "
        f"{output_path}"
    )

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
    print("\nEnlaces de navegación candidatos")
    print("-" * 88)

    navigation_keywords = (
        "journal",
        "revista",
        "numero",
        "issue",
        "articulo.oa?id=",
    )

    navigation_links = set()

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link["href"].strip()

        lower_href = href.lower()

        if any(
            keyword in lower_href
            for keyword in navigation_keywords
        ):
            navigation_links.add(
                href
            )

    for href in sorted(
        navigation_links
    ):
        print(href)

    print("-" * 88)
    print(
        f"Enlaces candidatos: "
        f"{len(navigation_links)}"
    )

    print("\nVariables de artículo encontradas")
    print("-" * 88)

    variable_keywords = (
        "cveRevista",
        "numero",
        "cveArticulo",
    )

    for line_number, line in enumerate(
        response.text.splitlines(),
        start=1,
    ):
        if any(
            keyword in line
            for keyword in variable_keywords
        ):
            clean_line = " ".join(
                line.strip().split()
            )

            print(
                f"{line_number:>5}: "
                f"{clean_line[:700]}"
            )

    print("-" * 88)


    print("\nScripts JavaScript de la página")
    print("-" * 88)

    script_sources = []

    for script in soup.find_all(
        "script",
        src=True,
    ):
        src = script.get("src", "").strip()

        if src:
            script_sources.append(src)

    for src in script_sources:
        print(src)

    print("-" * 88)
    print(
        f"Scripts encontrados: "
        f"{len(script_sources)}"
    )

    from urllib.parse import urljoin

    print("\nInspección de homeArticuloAngularJS.js")
    print("-" * 88)

    script_url = urljoin(
        response.url,
        "js/homeArticuloAngularJS.js",
    )

    script_response = requests.get(
        script_url,
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
        f"{script_response.status_code}"
    )

    print(
        f"Content-Type: "
        f"{script_response.headers.get('Content-Type')}"
    )

    print(
        f"Bytes       : "
        f"{len(script_response.content):,}"
    )

    keywords = (
        "$http",
        ".get(",
        ".post(",
        "cveArticulo",
        "cveRevista",
        "articulo",
        "service",
        "rest",
        "api",
    )

    matches = []

    for line_number, line in enumerate(
        script_response.text.splitlines(),
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
            f"{line[:900]}"
        )

    print("-" * 88)
    print(
        f"Coincidencias encontradas: "
        f"{len(matches)}"
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())