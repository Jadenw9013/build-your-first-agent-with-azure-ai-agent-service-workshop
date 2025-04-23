from pathlib import Path

class Utilities:
    @property
    def shared_files_path(self) -> Path:
        """
        Path to src/python/shared.
        """
        return Path(__file__).parents[1].resolve() / "shared"

    def load_instructions(self, instructions_file: str) -> str:
        """
        Load text from shared/instructions/<file>.
        """
        file_path = self.shared_files_path / "instructions" / instructions_file
        return file_path.read_text(encoding="utf-8")