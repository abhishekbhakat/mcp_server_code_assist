from pathlib import Path

from pydantic import BaseModel


# File operations
# ====================================================================
class FileCreate(BaseModel):
    path: str | Path
    content: str = ""


class FileDelete(BaseModel):
    path: str | Path


class FileModify(BaseModel):
    path: str | Path
    replacements: dict[str, str]


class FileRead(BaseModel):
    path: str | Path


class FileRewrite(BaseModel):
    path: str | Path
    content: str


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


class GitDiff(BaseModel):
    repo_path: str
    target: str


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
