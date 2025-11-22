"""Shared pytest fixtures and options for kicandy tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-download",
        action="store_true",
        default=False,
        help="Run tests that perform live icon downloads.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-download"):
        return
    skip_download = pytest.mark.skip(reason="use --run-download to execute download tests")
    for item in items:
        if "download" in item.keywords:
            item.add_marker(skip_download)


@pytest.fixture
def fixtures_path() -> Path:
    return Path(__file__).parent / "fixtures"
