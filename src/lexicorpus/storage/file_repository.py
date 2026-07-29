from pathlib import Path


class FileRepository:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def write_stage_text(
        self,
        stage_directory: str,
        source_code: str,
        document_id: str,
        text: str,
    ) -> Path:
        output_directory = (
            self.project_root
            / "data"
            / stage_directory
            / source_code
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = output_directory / f"{document_id}.txt"
        output_path.write_text(text, encoding="utf-8")

        return output_path