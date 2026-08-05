from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class QualityProfileLoader:
    def __init__(self, configuration_directory: Path) -> None:
        self.configuration_directory = configuration_directory.resolve()

        self.base_path = (
            self.configuration_directory
            / "base.yaml"
        )

        self.map_path = (
            self.configuration_directory
            / "profile_map.yaml"
        )

        self.profiles_directory = (
            self.configuration_directory
            / "profiles"
        )

        self.base_configuration = self._load_yaml(
            self.base_path
        )

        self.profile_map = self._load_yaml(
            self.map_path
        )

    def resolve(
        self,
        document_type: str | None,
    ) -> dict[str, Any]:
        normalized_document_type = (
            document_type or ""
        ).strip().lower()

        mappings = self.profile_map.get(
            "document_type_profiles",
            {},
        )

        default_profile = self.profile_map.get(
            "default_profile",
            "default",
        )

        profile_code = mappings.get(
            normalized_document_type,
            default_profile,
        )

        profile_path = (
            self.profiles_directory
            / f"{profile_code}.yaml"
        )

        if not profile_path.exists():
            raise FileNotFoundError(
                f"No existe el perfil de calidad "
                f"'{profile_code}': {profile_path}"
            )

        profile_configuration = self._load_yaml(
            profile_path
        )

        resolved_configuration = self._deep_merge(
            self.base_configuration,
            profile_configuration,
        )

        resolved_configuration[
            "resolved_document_type"
        ] = normalized_document_type or None

        return resolved_configuration

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el archivo: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as yaml_file:
            content = yaml.safe_load(yaml_file)

        if not isinstance(content, dict):
            raise ValueError(
                f"La configuración no es válida: {path}"
            )

        return content

    @classmethod
    def _deep_merge(
        cls,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        result = deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = cls._deep_merge(
                    result[key],
                    value,
                )
            else:
                result[key] = deepcopy(value)

        return result