import os
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from mcp_server_code_assist.tools.internet_tools import InternetTools


@pytest.fixture
def internet_tools():
    with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test_key"}):
        return InternetTools()


def test_process_citations():
    tools = InternetTools()
    answer = "The latest version of aiohttp is **3.11.11**[1][4]. This version includes various bug fixes and performance improvements as detailed in the changelog[5]."
    citations = [
        "https://docs.aiohttp.org",
        "https://docs.aiohttp.org/en/v3.8.4/changes.html",
        "https://docs.aiohttp.org/en/v3.8.2/",
        "https://github.com/aio-libs/aiohttp/releases",
        "https://docs.aiohttp.org/en/stable/changes.html",
    ]

    processed_answer = tools._process_citations(answer, citations)

    expected_answer = (
        "The latest version of aiohttp is **3.11.11**. "
        "This version includes various bug fixes and performance "
        "improvements as detailed in the changelog.\n\n"
        "citations:\n"
        "https://docs.aiohttp.org\n"
        "https://github.com/aio-libs/aiohttp/releases\n"
        "https://docs.aiohttp.org/en/stable/changes.html"
    )
    assert processed_answer == expected_answer


def test_process_citations_with_invalid_indices():
    tools = InternetTools()
    answer = "The latest version is 1.0.0[1][10][3]"  # 10 is out of range
    citations = [
        "https://example1.com",
        "https://example2.com",
        "https://example3.com",
    ]

    processed_answer = tools._process_citations(answer, citations)

    expected_answer = "The latest version is 1.0.0\n\ncitations:\nhttps://example1.com\nhttps://example3.com"
    assert processed_answer == expected_answer


def test_process_citations_with_no_citations():
    tools = InternetTools()
    answer = "The latest version is 1.0.0"
    citations = []

    processed_answer = tools._process_citations(answer, citations)

    assert processed_answer == answer


@pytest.mark.asyncio
async def test_ask_success(internet_tools):
    mock_response = {
        "choices": [{"message": {"content": "The answer is here[1][2]"}}],
        "citations": [
            "https://citation1.com",
            "https://citation2.com",
        ],
    }

    with aioresponses() as m:
        m.post(internet_tools.base_url, status=200, payload=mock_response)

        answer = await internet_tools.ask("What is the question?")

        expected_answer = "The answer is here\n\ncitations:\nhttps://citation1.com\nhttps://citation2.com"
        assert answer == expected_answer


@pytest.mark.asyncio
async def test_ask_with_no_citations(internet_tools):
    mock_response = {"choices": [{"message": {"content": "The answer is here"}}], "citations": []}

    with aioresponses() as m:
        m.post(internet_tools.base_url, status=200, payload=mock_response)

        answer = await internet_tools.ask("What is the question?")

        assert answer == "The answer is here"
