from __future__ import annotations

import requests


CANDIDATE_URLS = [
    "https://www.redalyc.org/oai",
    "https://www.redalyc.org/oai/",
    "https://www.redalyc.org/oai/request",
    "https://www.redalyc.org/oai-pmh",
]


def main() -> int:
    for base_url in CANDIDATE_URLS:
        print("\n" + "=" * 88)
        print(base_url)
        print("-" * 88)

        try:
            response = requests.get(
                base_url,
                params={
                    "verb": "Identify",
                },
                timeout=20,
                allow_redirects=True,
            )

            print(f"Status      : {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            print(f"URL final   : {response.url}")
            print()

            text = response.text[:800]
            print(text)

        except Exception as exc:
            print(
                f"ERROR: {type(exc).__name__}: {exc}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())