import os
from enum import Enum
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, Prompt, TextContent, Tool

from mcp_server_code_assist.prompts.prompt_manager import get_prompts, handle_prompt
from mcp_server_code_assist.tools.models import AskInternet, CreateDirectory, FileCreate, FileDelete, FileModify, FileRead, FileRewrite, FileTree, GitDiff, GitLog, GitShow, GitStatus, ListDirectory
from mcp_server_code_assist.tools.tools_manager import get_dir_tools, get_file_tools, get_git_tools, get_internet_tools


class CodeAssistTools(str, Enum):
    # Directory operations
    LIST_DIRECTORY = "list_directory"
    CREATE_DIRECTORY = "create_directory"

    # File operations
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    MODIFY_FILE = "modify_file"
    REWRITE_FILE = "rewrite_file"
    READ_FILE = "read_file"
    FILE_TREE = "file_tree"

    # Git operations
    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"
    GIT_LOG = "git_log"
    GIT_SHOW = "git_show"
    ASK_INTERNET = "ask_internet"


async def process_instruction(instruction: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    file_tools = get_file_tools([str(repo_path)])
    dir_tools = get_dir_tools([str(repo_path)])
    git_tools = get_git_tools([str(repo_path)])
    try:
        match instruction["type"]:
            case "read_file":
                return {"content": await file_tools.read_file(instruction["path"])}
            case "read_multiple":
                return {"contents": await file_tools.read_multiple_files(instruction["paths"])}
            case "create_file":
                return {"message": await file_tools.create_file(instruction["path"], instruction["content"])}
            case "modify_file":
                return {"diff": await file_tools.modify_file(instruction["path"], instruction["replacements"])}
            case "rewrite_file":
                return {"diff": await file_tools.rewrite_file(instruction["path"], instruction["content"])}
            case "delete_file":
                return {"message": await file_tools.delete_file(instruction["path"])}
            case "file_tree":
                tree, dirs, files = await file_tools.file_tree(instruction["path"])
                return {"tree": tree, "directories": dirs, "files": files}
            case "list_directory":
                return {"content": await dir_tools.list_directory(instruction["path"])}
            case "git_status":
                return {"status": git_tools.status(str(repo_path))}
            case "git_diff":
                return {"diff": git_tools.diff(str(repo_path), instruction.get("target"))}
            case "git_log":
                return {"log": git_tools.log(str(repo_path), instruction.get("max_count", 10))}
            case "git_show":
                return {"show": git_tools.show(str(repo_path), instruction["commit"])}
            case _:
                raise ValueError(f"Unknown instruction type: {instruction['type']}")
    except Exception as e:
        return {"error": str(e)}


async def serve(working_dir: Path | None) -> None:
    server = Server("mcp-code-assist")
    allowed_paths = [str(working_dir)] if working_dir else []

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = [
            # Directory operations
            Tool(
                name=CodeAssistTools.LIST_DIRECTORY,
                description="Lists directory contents using system ls/dir command",
                inputSchema=ListDirectory.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.CREATE_DIRECTORY,
                description="Creates a new directory",
                inputSchema=CreateDirectory.model_json_schema(),
            ),
            # File operations
            Tool(
                name=CodeAssistTools.CREATE_FILE,
                description="Creates a new file with content",
                inputSchema=FileCreate.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.DELETE_FILE,
                description="Deletes a file",
                inputSchema=FileDelete.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.MODIFY_FILE,
                description="Modifies parts of a file using string replacements",
                inputSchema=FileModify.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.REWRITE_FILE,
                description="Rewrites entire file content",
                inputSchema=FileRewrite.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.READ_FILE,
                description="Reads file content",
                inputSchema=FileRead.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.FILE_TREE,
                description="Lists directory tree structure with git tracking support",
                inputSchema=ListDirectory.model_json_schema(),
            ),
            # Git operations
            Tool(
                name=CodeAssistTools.GIT_STATUS,
                description="Shows git repository status",
                inputSchema=GitStatus.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.GIT_DIFF,
                description="Shows git diff",
                inputSchema=GitDiff.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.GIT_LOG,
                description="Shows git commit history",
                inputSchema=GitLog.model_json_schema(),
            ),
            Tool(
                name=CodeAssistTools.GIT_SHOW,
                description="Shows git commit details",
                inputSchema=GitShow.model_json_schema(),
            ),
        ]
        if os.getenv("PERPLEXITY_API_KEY"):
            tools.append(
                Tool(
                    name=CodeAssistTools.ASK_INTERNET,
                    description="Asks questions to Internet and returns answer with citations",
                    inputSchema=AskInternet.model_json_schema(),
                )
            )
        return tools

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return get_prompts()

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        return await handle_prompt(name, arguments)

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        repo_path = arguments.get("repo_path", "")
        paths = [repo_path] if repo_path else allowed_paths
        file_tools = get_file_tools(paths)
        dir_tools = get_dir_tools(paths)
        git_tools = get_git_tools(paths)

        match name:
            # Directory operations
            case CodeAssistTools.LIST_DIRECTORY:
                model = ListDirectory(path=arguments["path"])
                result = await dir_tools.list_directory(model.path)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.CREATE_DIRECTORY:
                model = CreateDirectory(path=arguments["path"])
                result = await dir_tools.create_directory(model.path)
                return [TextContent(type="text", text=result)]

            # File operations
            case CodeAssistTools.READ_FILE:
                model = FileRead(path=arguments["path"])
                result = await file_tools.read_file(model.path)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.CREATE_FILE:
                model = FileCreate(path=arguments["path"], content=arguments["content"])
                result = await file_tools.create_file(model.path, model.content)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.MODIFY_FILE:
                model = FileModify(path=arguments["path"], replacements=arguments["replacements"])
                result = await file_tools.modify_file(model.path, model.replacements)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.REWRITE_FILE:
                model = FileRewrite(path=arguments["path"], content=arguments["content"])
                result = await file_tools.rewrite_file(model.path, model.content)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.DELETE_FILE:
                model = FileDelete(path=arguments["path"])
                result = await file_tools.delete_file(model.path)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.FILE_TREE:
                model = FileTree(path=arguments["path"])
                result = await file_tools.file_tree(model.path)
                return [TextContent(type="text", text=result)]

            # Git operations
            case CodeAssistTools.GIT_STATUS:
                model = GitStatus(repo_path=arguments["repo_path"])
                result = await git_tools.status(model.repo_path)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.GIT_DIFF:
                model = GitDiff(repo_path=arguments["repo_path"], target=arguments.get("target", ""))
                result = await git_tools.diff(model.repo_path, model.target)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.GIT_LOG:
                model = GitLog(repo_path=arguments["repo_path"], max_count=arguments.get("max_count", 10))
                result = await git_tools.log(model.repo_path, model.max_count)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.GIT_SHOW:
                model = GitShow(repo_path=arguments["repo_path"], revision=arguments["commit"])
                result = await git_tools.show(model.repo_path, model.revision)
                return [TextContent(type="text", text=result)]
            case CodeAssistTools.ASK_INTERNET:
                model = AskInternet(query=arguments["query"])
                internet_tools = get_internet_tools()
                result = await internet_tools.ask(model.query)
                return [TextContent(type="text", text=result)]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
