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


from lexicorpus.acquisition.redalyc_harvester import (
    RedalycHarvester,
)


def main() -> int:
    harvester = RedalycHarvester(
        project_root=PROJECT_ROOT,
        maximum_documents_to_download=10,
    )

    statistics = harvester.run()

    print("\nResultado RedALyC")
    print("-" * 80)

    print(
        f"Revistas inspeccionadas : "
        f"{statistics.inspected_journals}"
    )

    print(
        f"Números inspeccionados  : "
        f"{statistics.inspected_issues}"
    )

    print(
        f"Artículos inspeccionados: "
        f"{statistics.inspected_articles}"
    )

    print(
        f"Metadatos aceptados     : "
        f"{statistics.accepted_metadata}"
    )

    print(
        f"Descargados             : "
        f"{statistics.downloaded}"
    )

    print(
        f"Rechazados por idioma   : "
        f"{statistics.rejected_language}"
    )

    print(
        f"Sin PDF                 : "
        f"{statistics.rejected_without_pdf}"
    )

    print(
        f"Errores                 : "
        f"{statistics.download_errors}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())