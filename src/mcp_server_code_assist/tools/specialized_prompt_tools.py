import platform
from pathlib import Path

from mcp_server_code_assist.base_tools import BaseTools
from mcp_server_code_assist.tools.git_tools import GitTools


class SpecializedPromptTools(BaseTools):
    def is_valid_operation(self, path: Path) -> bool:
        return True  # Always valid for prompt operations

    async def generate_git_commands(self, repo_path: str, operation: str) -> str:
        system_info = f"{platform.system()} {platform.machine()}"

        git_tools = GitTools([repo_path])
        before_status = git_tools.status(repo_path)

        user_prompt = (
            f"Please help with the following git operation in {repo_path}:\n{operation}\n\n"
            f"Current status:\n{before_status}\n\n"
            f"System info:\n{system_info}\n\n"
            "After you provide the commands and I execute them, I'll respond with 'done'. Then use git_tools to verify the changes."
        )

        return user_prompt

    async def generate_cli_commands(self, operation: str) -> str:
        system_info = f"{platform.system()} {platform.machine()}"

        user_prompt = f"Please help with the following command:\n{operation}\n\nSystem info:\n{system_info}\n\n" "After you provide the commands and I execute them, I'll respond with 'done'."

        return user_prompt
