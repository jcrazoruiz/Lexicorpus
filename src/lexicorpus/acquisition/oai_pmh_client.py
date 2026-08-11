from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Any

import requests


OAI_NAMESPACE = "http://www.openarchives.org/OAI/2.0/"

NAMESPACES = {
    "oai": OAI_NAMESPACE,
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


class OaiPmhError(RuntimeError):
    """Error producido durante una operación OAI-PMH."""


class OaiPmhClient:
    def __init__(
        self,
        base_url: str,
        metadata_prefix: str = "oai_dc",
        timeout_seconds: int = 45,
        delay_seconds: float = 1.0,
        user_agent: str = (
            "LexiCorpus/1.1 "
            "(academic corpus research; polite harvester)"
        ),
    ) -> None:
        if not base_url:
            raise ValueError(
                "Debe configurarse un endpoint OAI-PMH."
            )

        self.base_url = base_url
        self.metadata_prefix = metadata_prefix
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": (
                    "application/xml,"
                    "text/xml;q=0.9,"
                    "*/*;q=0.5"
                ),
            }
        )

    def identify(self) -> dict[str, str | None]:
        root = self._request(
            {
                "verb": "Identify",
            }
        )

        identify = root.find(
            "oai:Identify",
            NAMESPACES,
        )

        if identify is None:
            raise OaiPmhError(
                "La respuesta no contiene el bloque Identify."
            )

        return {
            "repository_name": self._text(
                identify.find(
                    "oai:repositoryName",
                    NAMESPACES,
                )
            ),
            "base_url": self._text(
                identify.find(
                    "oai:baseURL",
                    NAMESPACES,
                )
            ),
            "protocol_version": self._text(
                identify.find(
                    "oai:protocolVersion",
                    NAMESPACES,
                )
            ),
            "earliest_datestamp": self._text(
                identify.find(
                    "oai:earliestDatestamp",
                    NAMESPACES,
                )
            ),
            "deleted_record": self._text(
                identify.find(
                    "oai:deletedRecord",
                    NAMESPACES,
                )
            ),
            "granularity": self._text(
                identify.find(
                    "oai:granularity",
                    NAMESPACES,
                )
            ),
        }

    def list_records(
        self,
        maximum_records: int | None = None,
        set_spec: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
    ) -> Iterator[ET.Element]:
        parameters: dict[str, Any] = {
            "verb": "ListRecords",
            "metadataPrefix": self.metadata_prefix,
        }

        if set_spec:
            parameters["set"] = set_spec

        if from_date:
            parameters["from"] = from_date

        if until_date:
            parameters["until"] = until_date

        yielded = 0

        while True:
            root = self._request(parameters)

            error = root.find(
                "oai:error",
                NAMESPACES,
            )

            if error is not None:
                raise OaiPmhError(
                    f"{error.attrib.get('code')}: "
                    f"{self._text(error)}"
                )

            list_records = root.find(
                "oai:ListRecords",
                NAMESPACES,
            )

            if list_records is None:
                raise OaiPmhError(
                    "La respuesta no contiene ListRecords."
                )

            for record in list_records.findall(
                "oai:record",
                NAMESPACES,
            ):
                yield record
                yielded += 1

                if (
                    maximum_records is not None
                    and yielded >= maximum_records
                ):
                    return

            token_element = list_records.find(
                "oai:resumptionToken",
                NAMESPACES,
            )

            token = self._text(token_element)

            if not token:
                return

            parameters = {
                "verb": "ListRecords",
                "resumptionToken": token,
            }

    def _request(
        self,
        parameters: dict[str, Any],
    ) -> ET.Element:
        response = self.session.get(
            self.base_url,
            params=parameters,
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        try:
            root = ET.fromstring(
                response.content
            )
        except ET.ParseError as exc:
            raise OaiPmhError(
                "La respuesta OAI-PMH contiene XML inválido."
            ) from exc

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        return root

    @staticmethod
    def _text(
        element: ET.Element | None,
    ) -> str | None:
        if element is None or element.text is None:
            return None

        value = element.text.strip()
        return value or None