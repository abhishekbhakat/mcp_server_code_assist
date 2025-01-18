"""Tools manager for maintaining singleton instances of tools."""

from mcp_server_code_assist.tools.dir_tools import DirTools
from mcp_server_code_assist.tools.file_tools import FileTools
from mcp_server_code_assist.tools.git_tools import GitTools
from mcp_server_code_assist.tools.internet_tools import InternetTools

_file_tools: FileTools | None = None
_dir_tools: DirTools | None = None
_git_tools: GitTools | None = None
_internet_tools: InternetTools | None = None


def get_file_tools(allowed_paths: list[str]) -> FileTools:
    """Get or create FileTools instance with given allowed paths.

    Args:
        allowed_paths: List of paths that tools can operate on

    Returns:
        FileTools instance with updated paths
    """
    global _file_tools
    if not _file_tools or not all(path in _file_tools.allowed_paths for path in allowed_paths):
        _file_tools = FileTools(allowed_paths=allowed_paths)
    return _file_tools


def get_dir_tools(allowed_paths: list[str]) -> DirTools:
    """Get or create DirTools instance with given allowed paths.

    Args:
        allowed_paths: List of paths that tools can operate on

    Returns:
        DirTools instance with updated paths
    """
    global _dir_tools
    if not _dir_tools or not all(path in _dir_tools.allowed_paths for path in allowed_paths):
        _dir_tools = DirTools(allowed_paths=allowed_paths)
    return _dir_tools


def get_git_tools(allowed_paths: list[str]) -> GitTools:
    """Get or create GitTools instance with given allowed paths.

    Args:
        allowed_paths: List of paths that tools can operate on

    Returns:
        GitTools instance with updated paths
    """
    global _git_tools
    if not _git_tools or not all(path in _git_tools.allowed_paths for path in allowed_paths):
        _git_tools = GitTools(allowed_paths=allowed_paths)
    return _git_tools


def get_internet_tools() -> InternetTools:
    """Get or create InternetTools instance.

    Returns:
        InternetTools instance
    """
    global _internet_tools
    if not _internet_tools:
        _internet_tools = InternetTools()
    return _internet_tools
