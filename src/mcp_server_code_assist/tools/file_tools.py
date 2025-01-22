import difflib
import fnmatch
import os
import xml.etree.ElementTree as ET
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

    async def _write_file(self, path: str, content: str) -> str:
        path = await self.validate_path(path)
        try:
            path.write_text(content)
            return f"Written to file: {path}"
        except Exception as e:
            error_message = self.handle_error(e, {"operation": "write", "path": str(path)})
            return f"Error writing file: {error_message}"

    async def create_file(self, path: str, content: str | None = None, xml_content: str | None = None) -> str:
        path = await self.validate_path(path)
        try:
            actual_content = content or ""
            target_path = path

            if xml_content:
                root = ET.fromstring(xml_content)

                if root.tag == "file":
                    # Validate action name
                    action = root.get("action")
                    if action != "create_file":
                        raise ValueError(f"Invalid action '{action}'. Expected 'create_file' for create_file method.")

                    # Extract path from XML if specified
                    if xml_path := root.get("path"):
                        # Resolve relative to first allowed directory
                        base_path = Path(self.allowed_paths[0]) if self.allowed_paths else Path.cwd()
                        target_path = (base_path / xml_path).resolve()

                        # Re-validate with resolved path
                        target_path = await self.validate_path(str(target_path))

                        # Check if XML path matches parameter path
                        if str(target_path) != str(path):
                            raise ValueError(f"XML path '{xml_path}' does not match parameter path '{path}'")
                    else:
                        raise ValueError("Path not specified in XML")

                    # Extract content from all <change> elements
                    actual_content = ""
                    for change in root.findall("change"):
                        content_node = change.find("content")
                        if content_node is not None and content_node.text:
                            actual_content += content_node.text.strip() + "\n"

                    if not actual_content:
                        raise ValueError("No valid <content> found in <change> elements")

                else:
                    raise ValueError(f"Invalid XML root tag: {root.tag}")

                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(actual_content.strip())
                return f"Created file: {target_path}"
            else:
                # Handle regular file creation without XML
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(actual_content.strip())
                return f"Created file: {target_path}"
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

    async def modify_file(self, path: str, replacements: dict[str, str] | None = None, xml_content: str | None = None) -> str:
        path = await self.validate_path(path)
        try:
            target_path = path
            actual_content = backup_content = target_path.read_text()

            if xml_content:
                replacements = self._parse_xml_for_modify(xml_content, path)
            elif not replacements:
                raise ValueError("Either replacements or xml_content must be provided")

            actual_content = self._apply_replacements(actual_content, replacements)

            diff = self.generate_diff(backup_content, actual_content)
            if not diff:
                raise ValueError("No changes detected in the file content")

            await self._write_file(path, actual_content)
            return diff
        except Exception as e:
            error_message = self.handle_error(e, {"operation": "modify_file", "path": str(path)})
            return f"Error modifying file: {error_message}"

    def _parse_xml_for_modify(self, xml_content: str, path: str) -> dict[str, str]:
        root = ET.fromstring(xml_content)
        if root.tag != "file":
            raise ValueError(f"Invalid XML root tag: {root.tag}")

        action = root.get("action")
        if action != "modify_file":
            raise ValueError(f"Invalid action '{action}'. Expected 'modify_file' for modify_file method.")

        self._validate_xml_path(root, path)

        search_node = root.find("search")
        content_node = root.find("content")
        if not (search_node is not None and search_node.text and content_node is not None and content_node.text):
            raise ValueError("Both <search> and <content> tags are required for modify_file")

        return {search_node.text.strip(): content_node.text.strip()}

    def _validate_xml_path(self, root: ET.Element, path: str):
        if xml_path := root.get("path"):
            base_path = Path(self.allowed_paths[0]) if self.allowed_paths else Path.cwd()
            target_path = (base_path / xml_path).resolve()
            if str(target_path) != str(path):
                raise ValueError(f"XML path '{xml_path}' does not match parameter path '{path}'")
        else:
            raise ValueError("Path not specified in XML")

    def _apply_replacements(self, content: str, replacements: dict[str, str]) -> str:
        for old, new in replacements.items():
            content = content.replace(old, new)
        if not content:
            raise ValueError("No valid content after applying replacements")
        return content

    async def rewrite_file(self, path: str, content: str | None = None, xml_content: str | None = None) -> str:
        path = await self.validate_path(path)
        try:
            if xml_content:
                actual_content = self._parse_xml_for_rewrite(xml_content, path)
            elif content is not None:
                actual_content = content
            else:
                raise ValueError("Either content or xml_content must be provided")

            original_content = await self.read_file(path) if path.exists() else ""

            diff = self.generate_diff(original_content, actual_content)
            if not diff:
                raise ValueError("No changes detected in the file content")

            await self._write_file(path, actual_content)
            return diff
        except Exception as e:
            error_message = self.handle_error(e, {"operation": "rewrite_file", "path": str(path)})
            return f"Error rewriting file: {error_message}"

    def _parse_xml_for_rewrite(self, xml_content: str, path: str) -> str:
        root = ET.fromstring(xml_content)
        if root.tag != "file":
            raise ValueError(f"Invalid XML root tag: {root.tag}")

        action = root.get("action")
        if action != "rewrite_file":
            raise ValueError(f"Invalid action '{action}'. Expected 'rewrite_file' for rewrite_file method.")

        self._validate_xml_path(root, path)

        actual_content = ""
        for change in root.findall("change"):
            content_node = change.find("content")
            if content_node is not None and content_node.text:
                actual_content += content_node.text.strip() + "\n"

        if not actual_content:
            raise ValueError("No valid <content> found in <change> elements")

        return actual_content.strip()

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
