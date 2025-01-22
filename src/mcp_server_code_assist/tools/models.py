from pathlib import Path

from pydantic import BaseModel, model_validator


# File operations
# ====================================================================
class FileCreate(BaseModel):
    path: str | Path
    content: str | None = None
    xml_content: str | None = None

    @model_validator(mode="after")
    def check_content_or_xml(self) -> "FileCreate":
        if not self.content and not self.xml_content:
            raise ValueError("Must provide either content or xml_content")
        return self


class FileDelete(BaseModel):
    path: str | Path


class FileModify(BaseModel):
    path: str | Path
    replacements: dict[str, str] | None = None
    xml_content: str | None = None

    @model_validator(mode="after")
    def check_content_or_xml(self) -> "FileModify":
        if not self.content and not self.xml_content:
            raise ValueError("Must provide either content or xml_content")
        return self


class FileRead(BaseModel):
    path: str | Path


class FileRewrite(BaseModel):
    path: str | Path
    content: str | None = None
    xml_content: str | None = None

    @model_validator(mode="after")
    def check_content_or_xml(self) -> "FileRewrite":
        if not self.content and not self.xml_content:
            raise ValueError("Must provide either content or xml_content")
        return self


class FileTree(BaseModel):
    path: str


# Directory operations
# ====================================================================
class ListDirectory(BaseModel):
    path: str | Path


class CreateDirectory(BaseModel):
    path: str | Path


# Git operations
# ====================================================================
class GitBase(BaseModel):
    repo_path: str


class GitDiff(GitBase):
    path: str | None = None
    cached: bool = False
    staged: bool = False
    commit: str | None = None
    compare_to: str | None = None


class GitShow(BaseModel):
    repo_path: str
    revision: str


class GitLog(BaseModel):
    repo_path: str
    max_count: int = 10


class GitStatus(BaseModel):
    repo_path: str


class RepositoryOperation(BaseModel):
    path: str
    content: str | None = None
    replacements: dict[str, str] | None = None


# Internet operations
# ====================================================================
class AskInternet(BaseModel):
    query: str


# Specialized Prompt tools
# ====================================================================
class GenerateGitCommands(BaseModel):
    repo_path: str
    operation: str


class GenerateCliCommands(BaseModel):
    operation: str
