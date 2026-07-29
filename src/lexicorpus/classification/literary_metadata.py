from pathlib import Path

from lexicorpus.domain.document import Document


KNOWN_WORKS: dict[str, dict[str, str]] = {
    "quijote": {
        "title": (
            "El ingenioso hidalgo don Quijote de la Mancha"
        ),
        "author": "Miguel de Cervantes Saavedra",
        "document_type": "novela",
    },
    "lazarillo": {
        "title": (
            "La vida de Lazarillo de Tormes "
            "y de sus fortunas y adversidades"
        ),
        "author": "Anónimo",
        "document_type": "novela_picaresca",
    },
    "burlador": {
        "title": (
            "El burlador de Sevilla "
            "y convidado de piedra"
        ),
        "author": "Atribuido a Tirso de Molina",
        "document_type": "obra_dramatica",
    },
    "celestina": {
        "title": "La Celestina",
        "author": "Fernando de Rojas",
        "document_type": "obra_dialogada",
    },
}


class LiteraryMetadataClassifier:
    def classify(self, document: Document) -> None:
        normalized_name = self._normalize_filename(
            document.original_path
        )

        document.language = "es"
        document.thematic_domain = "literatura"
        document.document_type = "obra_literaria"

        for key, metadata in KNOWN_WORKS.items():
            if key not in normalized_name:
                continue

            document.title = metadata["title"]
            document.author = metadata["author"]
            document.document_type = metadata["document_type"]
            break

        if document.title is None:
            document.title = document.original_path.stem

    @staticmethod
    def _normalize_filename(file_path: Path) -> str:
        return (
            file_path.stem
            .lower()
            .replace("_", " ")
            .replace("-", " ")
        )