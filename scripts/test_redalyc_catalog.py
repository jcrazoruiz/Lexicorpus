from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.redalyc.org/"


def main() -> int:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        }
    )

    response = session.get(
        BASE_URL,
        timeout=30,
    )

    response.encoding = "utf-8"
    response.raise_for_status()

    print("\nPágina principal")
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

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    scripts: list[str] = []

    for script in soup.find_all(
        "script",
        src=True,
    ):
        src = script.get(
            "src",
            "",
        ).strip()

        if not src:
            continue

        script_url = urljoin(
            response.url,
            src,
        )

        scripts.append(
            script_url
        )

    print("\nScripts encontrados")
    print("-" * 88)

    for script_url in scripts:
        print(script_url)

    print("-" * 88)

    print(
        f"Total scripts: "
        f"{len(scripts)}"
    )

    keywords = (
        "$http",
        "service/",
        "/service",
        "journal",
        "journals",
        "revista",
        "revistas",
        "collection",
        "coleccion",
        "area",
        "areas",
        "getjournal",
        "getjournals",
        "getrevista",
        "getrevistas",
    )

    excluded_scripts = (
        "googletagmanager",
        "angular.js",
        "angular-route",
        "angular-sanitize",
        "jquery",
    )

    print(
        "\nReferencias potenciales "
        "al catálogo"
    )

    print("-" * 88)

    total_matches = 0
    inspected_scripts = 0

    for script_url in scripts:

        # Ignoramos scripts que no sean propios
        # de RedALyC.
        if "redalyc.org" not in script_url.lower():
            continue

        # Ignoramos librerías genéricas que
        # producen demasiados falsos positivos.
        lower_script_url = (
            script_url.lower()
        )

        if any(
            excluded
            in lower_script_url
            for excluded in excluded_scripts
        ):
            continue

        inspected_scripts += 1

        try:
            script_response = (
                session.get(
                    script_url,
                    timeout=30,
                )
            )

            if (
                script_response.status_code
                != 200
            ):
                print(
                    f"\nSCRIPT NO DISPONIBLE: "
                    f"{script_url}"
                )

                print(
                    f"Status: "
                    f"{script_response.status_code}"
                )

                continue

            script_response.encoding = (
                "utf-8"
            )

            matches = []

            for (
                line_number,
                line,
            ) in enumerate(
                script_response.text.splitlines(),
                start=1,
            ):
                lower_line = (
                    line.lower()
                )

                if any(
                    keyword.lower()
                    in lower_line
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

            if not matches:
                continue

            print(
                f"\nSCRIPT: "
                f"{script_url}"
            )

            print("-" * 88)

            for (
                line_number,
                line,
            ) in matches:
                print(
                    f"{line_number:>5}: "
                    f"{line[:1200]}"
                )

                total_matches += 1

        except requests.RequestException as exc:
            print(
                f"\nNo se pudo inspeccionar "
                f"{script_url}"
            )

            print(
                f"Error: {exc}"
            )

    print("\n" + "-" * 88)

    print(
        f"Scripts propios inspeccionados: "
        f"{inspected_scripts}"
    )

    print(
        f"Coincidencias totales         : "
        f"{total_matches}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())