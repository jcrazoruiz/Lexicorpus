from __future__ import annotations

import re


class CanonicalCleaner:
    """
    Aplica transformaciones conservadoras antes de generar
    la representación canónica del documento.
    """

    HYPHENATED_LINE_BREAK_PATTERN = re.compile(
        r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)-\n"
        r"([a-záéíóúüñ]+)"
    )

    NUMERIC_ONLY_LINE_PATTERN = re.compile(
        r"^\s*\d+\s*$",
        flags=re.MULTILINE,
    )

    EXCESSIVE_BLANK_LINES_PATTERN = re.compile(
        r"\n{3,}"
    )

    def clean(self, text: str) -> str:
        cleaned = self._join_hyphenated_words(text)
        cleaned = self._remove_numeric_only_lines(cleaned)
        cleaned = self._normalize_blank_lines(cleaned)

        return cleaned.strip() + "\n"

    def _join_hyphenated_words(self, text: str) -> str:
        """
        Une palabras divididas por guion y salto de línea
        cuando la continuación comienza en minúscula.

        Ejemplo:
            caba-
            llero

        Resultado:
            caballero
        """
        return self.HYPHENATED_LINE_BREAK_PATTERN.sub(
            r"\1\2",
            text,
        )

    def _remove_numeric_only_lines(self, text: str) -> str:
        """
        Elimina líneas formadas únicamente por dígitos.

        Conserva números dentro de oraciones o encabezados.
        """
        return self.NUMERIC_ONLY_LINE_PATTERN.sub(
            "",
            text,
        )

    def _normalize_blank_lines(self, text: str) -> str:
        return self.EXCESSIVE_BLANK_LINES_PATTERN.sub(
            "\n\n",
            text,
        )