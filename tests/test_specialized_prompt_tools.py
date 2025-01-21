from pathlib import Path
from unittest.mock import patch

import pytest
from mcp_server_code_assist.tools.specialized_prompt_tools import SpecializedPromptTools


class TestSpecializedPromptTools(SpecializedPromptTools):
    def is_valid_operation(self, path: Path) -> bool:
        """Always return True for testing purposes"""
        return True


@pytest.fixture
def specialized_prompt_tools() -> TestSpecializedPromptTools:
    return TestSpecializedPromptTools()


class TestSpecializedPromptToolsTests:
    @pytest.mark.asyncio
    async def test_generate_git_commands_basic(self, specialized_prompt_tools: TestSpecializedPromptTools) -> None:
        with patch("mcp_server_code_assist.tools.specialized_prompt_tools.GitTools") as mock_git_tools:
            mock_git_tools.return_value.status.return_value = "On branch main\nNothing to commit"

            result = await specialized_prompt_tools.generate_git_commands("/path/to/repo", "commit -m 'Test commit'")

            # Verify the result contains all necessary components
            assert "On branch main" in result
            assert "Nothing to commit" in result
            assert "commit -m 'Test commit'" in result
            assert "/path/to/repo" in result

            # Verify GitTools was used correctly
            mock_git_tools.assert_called_once_with(["/path/to/repo"])
            mock_git_tools.return_value.status.assert_called_once_with("/path/to/repo")

    @pytest.mark.asyncio
    async def test_generate_git_commands_with_changes(self, specialized_prompt_tools: TestSpecializedPromptTools) -> None:
        with patch("mcp_server_code_assist.tools.specialized_prompt_tools.GitTools") as mock_git_tools:
            mock_status = """On branch main
Changes not staged for commit:
  modified: file1.txt
  modified: file2.txt
Untracked files:
  new_file.txt"""
            mock_git_tools.return_value.status.return_value = mock_status

            result = await specialized_prompt_tools.generate_git_commands("/path/to/repo", "add all changes and commit")

            # Verify result contains status details
            assert "Changes not staged for commit" in result
            assert "modified: file1.txt" in result
            assert "modified: file2.txt" in result
            assert "Untracked files" in result
            assert "new_file.txt" in result

    @pytest.mark.asyncio
    async def test_generate_cli_commands_basic(self, specialized_prompt_tools: TestSpecializedPromptTools) -> None:
        with patch("platform.system") as mock_system, patch("platform.machine") as mock_machine:
            mock_system.return_value = "Darwin"
            mock_machine.return_value = "arm64"

            result = await specialized_prompt_tools.generate_cli_commands("List all files in the current directory")

            # Verify system info and command are included
            assert "Darwin arm64" in result
            assert "List all files in the current directory" in result
            assert "After you provide the commands" in result

    @pytest.mark.asyncio
    async def test_generate_cli_commands_complex(self, specialized_prompt_tools: TestSpecializedPromptTools) -> None:
        with patch("platform.system") as mock_system, patch("platform.machine") as mock_machine:
            mock_system.return_value = "Darwin"
            mock_machine.return_value = "arm64"

            complex_operation = """
            1. Create a new directory
            2. Move all .py files into it
            3. Run pytest on the directory
            """
            result = await specialized_prompt_tools.generate_cli_commands(complex_operation)

            # Verify multi-line operation is properly included
            assert "Darwin arm64" in result
            assert "Create a new directory" in result
            assert "Move all .py files" in result
            assert "Run pytest" in result
