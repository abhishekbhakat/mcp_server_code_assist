import difflib
import fnmatch
import os
from pathlib import Path

import git

from mcp_server_code_assist.base_tools import BaseTools


class FileTools(BaseTools):
    def is_valid_operation(self, path: Path) -> bool:
        """Validate if operation can be performed on path"""
        return path.exists() and path.is_file()

    async def validate_path(self, path: str) -> Path:
        abs_path = os.path.abspath(path)
        if not any(abs_path.startswith(p) for p in self.allowed_paths):
            raise ValueError(f"Path {path} is outside allowed directories")
        return Path(abs_path)

    async def read_file(self, path: str) -> str:
        path = await self.validate_path(path)
        try:
            content = path.read_text()
            return content
        except Exception as e:
            error_message = self.handle_error(e, {"operation": "read", "path": str(path)})
            return f"Error reading file: {error_message}"

    async def create_file(self, path: str, content: str | None = None, xml_content: str | None = None) -> str:
        path = await self.validate_path(path)
        try:
            actual_content = xml_content or content or ""
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual_content)
            return f"Created file: {path}"
        except Exception as e:
            error_message = self.handle_error(e, {"operation": "create_file", "path": str(path)})
            return f"Error creating file: {error_message}"

    async def delete_file(self, path: str) -> str:
        path = await self.validate_path(path)
        if not path.is_file():
            return f"Path not found: {path}"

        # Create trash directory
        trash_dir = path.parent / ".mcp_server_code_assist_trash"
        trash_dir.mkdir(exist_ok=True)

        # Move file to trash with timestamp to avoid conflicts
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_path = trash_dir / f"{path.name}_{timestamp}"
        path.rename(trash_path)

        return f"Moved file to trash: {trash_path}"

    async def modify_file(self, path: str, replacements: dict[str, str]) -> str:
        path = await self.validate_path(path)
        original_content = await self.read_file(path)
        content = original_content

        for old, new in replacements.items():
            content = content.replace(old, new)

        diff = self.generate_diff(original_content, content)
        if not diff:
            raise ValueError("No changes detected in the file content")

        await self.write_file(path, content)
        return diff

    async def rewrite_file(self, path: str, content: str | None = None) -> str:
        path = await self.validate_path(path)
        original_content = await self.read_file(path) if path.exists() else ""

        if content is None:
            raise ValueError("Content must be provided")

        diff = self.generate_diff(original_content, content)
        if not diff:
            raise ValueError("No changes detected in the file content")

        await self.write_file(path, content)
        return diff

    @staticmethod
    def generate_diff(original: str, modified: str) -> str:
        diff = difflib.unified_diff(original.splitlines(keepends=True), modified.splitlines(keepends=True), fromfile="original", tofile="modified")
        return "".join(diff)

    async def file_tree(self, path: str) -> tuple[str, int, int]:
        """Generate tree view of directory structure.

        Args:
            path: Root directory path

        Returns:
            Tree view as string
        """
        path = await self.validate_path(path)
        base_path = path

        # Try git tracking first
        tracked_files = self._get_tracked_files(path)
        gitignore = self._load_gitignore(path) if tracked_files is None else []

        def gen_tree(path: Path, prefix: str = "") -> tuple[list[str], int, int]:
            entries = []
            dir_count = 0
            file_count = 0

            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for i, item in enumerate(items):
                rel_path = str(item.relative_to(base_path))

                # Skip if file should be ignored
                if tracked_files is not None:
                    if rel_path not in tracked_files and not any(str(p.relative_to(base_path)) in tracked_files for p in item.rglob("*") if p.is_file()):
                        continue
                else:
                    # Use gitignore
                    if self._should_ignore(rel_path, gitignore):
                        continue

                is_last = i == len(items) - 1
                curr_prefix = "└── " if is_last else "├── "
                curr_line = prefix + curr_prefix + item.name

                if item.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    subtree, sub_dirs, sub_files = gen_tree(item, next_prefix)
                    if tracked_files is not None and not subtree:
                        continue
                    entries.extend([curr_line] + subtree)
                    dir_count += 1 + sub_dirs
                    file_count += sub_files
                else:
                    if tracked_files is not None and rel_path not in tracked_files:
                        continue
                    entries.append(curr_line)
                    file_count += 1

            return entries, dir_count, file_count

        tree_lines, _, _ = gen_tree(path)
        return "\n".join(tree_lines)

    def _should_ignore(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches gitignore patterns.

        Args:
            path: Path to check
            patterns: List of gitignore patterns

        Returns:
            True if path should be ignored
        """
        if not patterns:
            return False

        parts = Path(path).parts
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue

            if pattern.endswith("/"):
                pattern = pattern.rstrip("/")
                if pattern in parts:
                    return True
            else:
                if fnmatch.fnmatch(parts[-1], pattern):  # Match basename
                    return True
                # Match full path
                if fnmatch.fnmatch(path, pattern):
                    return True

        return False

    def _load_gitignore(self, path: str) -> list[str]:
        """Load gitignore patterns from a directory.

        Args:
            path: Directory containing .gitignore

        Returns:
            List of gitignore patterns
        """
        gitignore_path = os.path.join(path, ".gitignore")
        patterns = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        return patterns

    def _get_tracked_files(self, repo_path: str) -> set[str] | None:
        """Get set of tracked files in a git repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Set of tracked file paths or None if not a git repo
        """
        try:
            repo = git.Repo(repo_path)
            return set(repo.git.ls_files().splitlines())
        except git.exc.InvalidGitRepositoryError:
            return None
