from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lexicorpus.classification.base_classifier import (
    BaseClassifier,
)

from lexicorpus.classification.literary_metadata import (
    LiteraryMetadataClassifier,
)

from lexicorpus.classification.scientific_article_classifier import (
    ScientificArticleClassifier,
)

from lexicorpus.classification.wikipedia_metadata_classifier import (
    WikipediaMetadataClassifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SourceDefinition:

    code: str

    name: str

    acquisition_method: str

    acquisition_strategy: str

    raw_directory: str

    supported_extensions: set[str]

    classifier_factory: Callable[
        [Path],
        BaseClassifier,
    ]


def build_scielo_classifier(
    project_root: Path,
) -> BaseClassifier:

    return (
        ScientificArticleClassifier(
            acquisition_metadata_path=(
                project_root
                / "metadata"
                / "acquisition"
                / "scielo"
                / "scielo_acquisition.jsonl"
            )
        )
    )


def build_redalyc_classifier(
    project_root: Path,
) -> BaseClassifier:

    return (
        ScientificArticleClassifier(
            acquisition_metadata_path=(
                project_root
                / "metadata"
                / "acquisition"
                / "redalyc"
                / "redalyc_acquisition.jsonl"
            )
        )
    )


def build_wikipedia_classifier(
    project_root: Path,
) -> BaseClassifier:

    return (
        WikipediaMetadataClassifier(
            acquisition_metadata_path=(
                project_root
                / "metadata"
                / "acquisition"
                / "wikipedia_es"
                / "wikipedia_acquisition.jsonl"
            )
        )
    )


def build_literature_classifier(
    project_root: Path,
) -> BaseClassifier:

    return (
        LiteraryMetadataClassifier()
    )


SOURCE_REGISTRY: dict[
    str,
    SourceDefinition,
] = {

    "scielo": SourceDefinition(
        code="scielo",
        name="SciELO México",
        acquisition_method=(
            "oai_pmh"
        ),
        acquisition_strategy=(
            "oai_pmh"
        ),
        raw_directory=(
            "data/raw/scielo"
        ),
        supported_extensions={
            ".pdf",
        },
        classifier_factory=(
            build_scielo_classifier
        ),
    ),

    "redalyc": SourceDefinition(
        code="redalyc",
        name="RedALyC",
        acquisition_method=(
            "web_catalog"
        ),
        acquisition_strategy=(
            "redalyc_web"
        ),
        raw_directory=(
            "data/raw/redalyc"
        ),
        supported_extensions={
            ".pdf",
        },
        classifier_factory=(
            build_redalyc_classifier
        ),
    ),

    "wikipedia_es": SourceDefinition(
        code="wikipedia_es",
        name=(
            "Wikipedia en español"
        ),
        acquisition_method=(
            "wikimedia_dump"
        ),
        acquisition_strategy=(
            "local"
        ),
        raw_directory=(
            "data/raw/"
            "wikipedia_es/"
            "articles"
        ),
        supported_extensions={
            ".txt",
        },
        classifier_factory=(
            build_wikipedia_classifier
        ),
    ),

    "literatura_clasica": (
        SourceDefinition(
            code=(
                "literatura_clasica"
            ),
            name=(
                "Literatura clásica "
                "en español"
            ),
            acquisition_method=(
                "local_directory"
            ),
            acquisition_strategy=(
                "local"
            ),
            raw_directory=(
                "data/raw/"
                "literatura_clasica"
            ),
            supported_extensions={
                ".pdf",
                ".txt",
            },
            classifier_factory=(
                build_literature_classifier
            ),
        )
    ),
}