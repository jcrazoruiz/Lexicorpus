from __future__ import annotations

from dataclasses import dataclass

from lexicorpus.acquisition.remote_record import RemoteRecord


@dataclass(frozen=True, slots=True)
class FilterResult:
    accepted: bool
    status: str
    reason: str | None = None


class MetadataFilter:
    """
    Evalúa si un registro remoto cumple los criterios
    documentales mínimos para continuar con la adquisición.

    Este componente no descarga archivos ni modifica
    el registro recibido.
    """

    def __init__(
        self,
        accepted_languages: set[str],
        accepted_resource_types: set[str],
        require_pdf: bool = True,
    ) -> None:
        self.accepted_languages = {
            value.strip().lower()
            for value in accepted_languages
        }

        self.accepted_resource_types = {
            value.strip().lower()
            for value in accepted_resource_types
        }

        self.require_pdf = require_pdf

    def evaluate(
        self,
        record: RemoteRecord,
    ) -> FilterResult:
        language_result = self._validate_language(
            record.language
        )

        if not language_result.accepted:
            return language_result

        type_result = self._validate_resource_type(
            record.resource_type
        )

        if not type_result.accepted:
            return type_result

        if self.require_pdf and not record.pdf_url:
            return FilterResult(
                accepted=False,
                status="REJECTED_WITHOUT_PDF",
                reason=(
                    "No se identificó una URL candidata "
                    "para recuperar el PDF."
                ),
            )

        return FilterResult(
            accepted=True,
            status="ACCEPTED_METADATA",
        )

    def _validate_language(
        self,
        language: str | None,
    ) -> FilterResult:
        if not language:
            return FilterResult(
                accepted=False,
                status="REJECTED_LANGUAGE",
                reason="El registro no informa el idioma.",
            )

        normalized = language.strip().lower()

        accepted = (
            normalized in self.accepted_languages
            or normalized.startswith("es-")
        )

        if not accepted:
            return FilterResult(
                accepted=False,
                status="REJECTED_LANGUAGE",
                reason=f"Idioma no aceptado: {language}",
            )

        return FilterResult(
            accepted=True,
            status="ACCEPTED_LANGUAGE",
        )

    def _validate_resource_type(
        self,
        resource_type: str | None,
    ) -> FilterResult:
        # Algunos registros Dublin Core no informan el tipo.
        # Se aceptan para clasificarlos posteriormente.
        if not resource_type:
            return FilterResult(
                accepted=True,
                status="ACCEPTED_UNKNOWN_TYPE",
            )

        normalized = resource_type.strip().lower()

        accepted = (
            normalized in self.accepted_resource_types
            or "article" in normalized
            or "artículo" in normalized
            or "articulo" in normalized
        )

        if not accepted:
            return FilterResult(
                accepted=False,
                status="REJECTED_TYPE",
                reason=(
                    "Tipo documental no aceptado: "
                    f"{resource_type}"
                ),
            )

        return FilterResult(
            accepted=True,
            status="ACCEPTED_TYPE",
        )