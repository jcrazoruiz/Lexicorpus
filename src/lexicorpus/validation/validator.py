from dataclasses import dataclass, field


@dataclass(slots=True)
class ValidationResult:
    accepted: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DocumentValidator:
    def __init__(
        self,
        minimum_characters: int = 1_000,
        minimum_words: int = 200,
    ) -> None:
        self.minimum_characters = minimum_characters
        self.minimum_words = minimum_words

    def validate(
        self,
        text: str,
        word_count: int,
    ) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not text.strip():
            errors.append("El texto está vacío.")

        if len(text) < self.minimum_characters:
            errors.append(
                "El texto no alcanza la longitud mínima de "
                f"{self.minimum_characters} caracteres."
            )

        if word_count < self.minimum_words:
            errors.append(
                "El texto no alcanza el mínimo de "
                f"{self.minimum_words} palabras."
            )

        replacement_character_count = text.count("\ufffd")

        if replacement_character_count:
            warnings.append(
                "Se encontraron caracteres de sustitución Unicode: "
                f"{replacement_character_count}."
            )

        null_count = text.count("\x00")

        if null_count:
            errors.append(
                f"Se encontraron {null_count} caracteres nulos."
            )

        return ValidationResult(
            accepted=not errors,
            errors=errors,
            warnings=warnings,
        )