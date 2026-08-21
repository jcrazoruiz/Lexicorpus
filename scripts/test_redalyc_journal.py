from __future__ import annotations

import requests


BASE_URL = "https://www.redalyc.org"
JOURNAL_ID = "615"

JOURNAL_ENDPOINT = (
    f"{BASE_URL}/service/r2020/"
    f"getJournalByID/{JOURNAL_ID}"
)


def main() -> int:
    response = requests.get(
        JOURNAL_ENDPOINT,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "LexiCorpus/1.3"
            )
        },
    )

    response.encoding = "utf-8"

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

    data = response.json()

    print("\nDatos de revista")
    print("-" * 80)

    for key in (
        "cveRevista",
        "nomRevista",
        "paisRevista",
        "issnrev",
        "issnelerev",
    ):
        print(
            f"{key:<20}: "
            f"{data.get(key)}"
        )

    anios_numeros = (
        data.get("aniosNumeros")
        or ""
    )

    print(
        "\nNúmeros detectados"
    )
    print("-" * 80)

    issues = []

    rows = anios_numeros.split(">>>")

    for row in rows:
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

            volume = elements[index]
            issue_label = elements[index + 1]
            issue_type = elements[index + 2]
            issue_id = elements[index + 3]
            jats_status = elements[index + 4]

            issues.append(
                {
                    "year": year,
                    "volume": volume,
                    "issue_label": issue_label,
                    "issue_type": issue_type,
                    "issue_id": issue_id,
                    "jats_status": jats_status,
                }
            )

    for issue in issues:
        print(
            f"{issue['year']} | "
            f"vol={issue['volume']} | "
            f"num={issue['issue_label']} | "
            f"clave={issue['issue_id']} | "
            f"jats={issue['jats_status']}"
        )

    print("-" * 80)

    print(
        f"Total de números: "
        f"{len(issues)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())