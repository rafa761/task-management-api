#!/usr/bin/env python3
"""
File Path Comment Automation Tool

This script automatically adds/updates file path comments on the first line
of Python files within the 'src' directory structure.

Usage:
    python scripts/add_file_paths.py check          # Check consistency only
    python scripts/add_file_paths.py fix            # Add/update comments
    python scripts/add_file_paths.py fix --verbose  # With detailed output
"""

import re
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    help="Automatically add/update file path comments in Python files",
    add_completion=False,
)


class FilePathCommenter:
    """Handles adding and updating file path comments in Python files."""

    def __init__(self, src_dir: str = "src", verbose: bool = False):
        self.src_dir = Path(src_dir).resolve()
        self.verbose = verbose
        self.modified_files: list[str] = []
        self.errors: list[str] = []

        # Pattern to match existing path comments
        self.path_comment_pattern = re.compile(r"^#\s+[\w\/\.]+\s*$")

    def log(self, message: str, level: str = "INFO") -> None:
        """Log messages if verbose mode is enabled."""
        if self.verbose:
            typer.echo(f"[{level}] {message}")

    def get_relative_path(self, file_path: Path) -> str:
        """
        Get the relative path from src directory, formatted for comment.

        Args:
            file_path: Path to the Python file

        Returns:
            Relative path string (e.g., "app/core/config")
        """
        try:
            # Get path relative to src directory
            relative_path = file_path.relative_to(self.src_dir)
            # Convert to forward slashes for comment
            return str(relative_path).replace("\\", "/")
        except ValueError as e:
            self.log(f"Error getting relative path for {file_path}: {e}", "ERROR")
            self.errors.append(f"Path error: {file_path}")
            return ""

    def should_process_file(self, file_path: Path) -> bool:
        """
        Determine if a Python file should be processed.

        Args:
            file_path: Path to the file

        Returns:
            True if file should be processed
        """
        # Skip if not a Python file
        if file_path.suffix != ".py":
            return False

        # Skip common files that shouldn't have path comments
        skip_files = {"__init__.py"}
        if file_path.name in skip_files:
            self.log(f"Skipping {file_path.name} (excluded file)", "DEBUG")
            return False

        # Skip if file is empty or very small
        try:
            if file_path.stat().st_size < 10:  # Less than 10 bytes
                self.log(f"Skipping {file_path} (too small)", "DEBUG")
                return False
        except OSError:
            return False

        return True

    def read_file_lines(self, file_path: Path) -> list[str] | None:
        """
        Read file lines with proper encoding handling.

        Args:
            file_path: Path to the file

        Returns:
            List of lines or None if error
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return f.readlines()
        except (UnicodeDecodeError, OSError) as e:
            self.log(f"Error reading {file_path}: {e}", "ERROR")
            self.errors.append(f"Read error: {file_path}")
            return None

    def write_file_lines(self, file_path: Path, lines: list[str]) -> bool:
        """
        Write file lines with proper encoding.

        Args:
            file_path: Path to the file
            lines: Lines to write

        Returns:
            True if successful
        """
        try:
            with file_path.open("w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        except OSError as e:
            self.log(f"Error writing {file_path}: {e}", "ERROR")
            self.errors.append(f"Write error: {file_path}")
            return False

    def get_expected_comment(self, file_path: Path) -> str:
        """
        Generate the expected path comment for a file.

        Args:
            file_path: Path to the file

        Returns:
            Expected comment line
        """
        relative_path = self.get_relative_path(file_path)
        return f"# {relative_path}\n"

    def process_file(
        self, file_path: Path, fix_mode: bool = False
    ) -> tuple[bool, bool]:
        """
        Process a single Python file to check/update path comment.

        Args:
            file_path: Path to the Python file
            fix_mode: Whether to actually modify the file

        Returns:
            Tuple of (needs_fix, was_modified)
        """
        if not self.should_process_file(file_path):
            return False, False

        lines = self.read_file_lines(file_path)
        if lines is None:
            return False, False

        if not lines:  # Empty file
            return False, False

        expected_comment = self.get_expected_comment(file_path)
        if not expected_comment.strip():  # Couldn't generate valid path
            return False, False

        needs_fix = False
        first_line = lines[0]

        # Check if first line is already the correct path comment
        if first_line.strip() == expected_comment.strip():
            self.log(f"✓ {file_path.name} - correct comment", "DEBUG")
            return False, False

        # Check if first line is a different path comment
        if self.path_comment_pattern.match(first_line.strip()):
            self.log(f"⚠ {file_path.name} - incorrect path comment", "INFO")
            needs_fix = True
            if fix_mode:
                lines[0] = expected_comment
                if self.write_file_lines(file_path, lines):
                    self.modified_files.append(str(file_path))
                    self.log(f"✓ Updated comment in {file_path.name}", "INFO")
                    return True, True
        else:
            # No path comment exists, add one
            self.log(f"⚠ {file_path.name} - missing path comment", "INFO")
            needs_fix = True
            if fix_mode:
                lines.insert(0, expected_comment)
                if self.write_file_lines(file_path, lines):
                    self.modified_files.append(str(file_path))
                    self.log(f"✓ Added comment to {file_path.name}", "INFO")
                    return True, True

        return needs_fix, False

    def find_python_files(self) -> list[Path]:
        """
        Find all Python files in the src directory.

        Returns:
            List of Python file paths
        """
        if not self.src_dir.exists():
            self.log(f"Source directory {self.src_dir} does not exist", "ERROR")
            self.errors.append(f"Directory not found: {self.src_dir}")
            return []

        python_files = []
        for file_path in self.src_dir.rglob("*.py"):
            if file_path.is_file():
                python_files.append(file_path)

        self.log(f"Found {len(python_files)} Python files", "INFO")
        return python_files

    def run(self, check_mode: bool = False) -> int:
        """
        Run the file path comment automation.

        Args:
            check_mode: If True, only check for inconsistencies

        Returns:
            Exit code (0 = success, 1 = errors found)
        """
        python_files = self.find_python_files()
        if not python_files:
            typer.echo("No Python files found to process")
            return 0 if not self.errors else 1

        files_needing_fix = []
        fix_mode = not check_mode

        for file_path in python_files:
            needs_fix, was_modified = self.process_file(file_path, fix_mode)
            if needs_fix and not was_modified:
                files_needing_fix.append(file_path)

        # Report results
        if check_mode:
            if files_needing_fix:
                typer.echo(
                    f"\n❌ {len(files_needing_fix)} files need path comment fixes:"
                )
                for file_path in files_needing_fix:
                    typer.echo(f"  - {file_path}")
                typer.echo(
                    "\nRun 'python scripts/add_file_paths.py fix' to automatically update these files"
                )
                return 1
            typer.echo("✅ All files have correct path comments")
            return 0
        if self.modified_files:
            typer.echo(f"\n✅ Updated {len(self.modified_files)} files:")
            for file_path in self.modified_files:
                typer.echo(f"  - {file_path}")
        else:
            typer.echo("✅ No files needed updates")

        if self.errors:
            typer.echo(f"\n⚠ {len(self.errors)} errors occurred:")
            for error in self.errors:
                typer.echo(f"  - {error}")
            return 1

        return 0


@app.command()
def check(
    src_dir: Annotated[
        str, typer.Option("--src-dir", help="Source directory to process")
    ] = "src",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed progress information")
    ] = False,
):
    """Check if files have correct path comments without modifying them."""
    commenter = FilePathCommenter(src_dir=src_dir, verbose=verbose)
    exit_code = commenter.run(check_mode=True)
    raise typer.Exit(exit_code)


@app.command()
def fix(
    src_dir: Annotated[
        str, typer.Option("--src-dir", help="Source directory to process")
    ] = "src",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed progress information")
    ] = False,
):
    """Automatically add/update path comments in Python files."""
    commenter = FilePathCommenter(src_dir=src_dir, verbose=verbose)
    exit_code = commenter.run(check_mode=False)
    raise typer.Exit(exit_code)


@app.callback()
def main():
    """
    File Path Comment Automation Tool

    Automatically adds/updates file path comments on the first line
    of Python files within the 'src' directory structure.
    """


if __name__ == "__main__":
    app()
