"""Tests for the offline portions of the icon repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from icon_fonts import IconFont
from icon_repository import IconRepository


class RecordingFontSource:
    """Test helper that records download attempts and writes fixture payloads."""

    def __init__(self, identifier: str, payload: str) -> None:
        self.identifier = identifier
        self._payload = payload
        self.download_requests: list[str] = []

    def download_codepoints(self, font: IconFont, destination: Path) -> None:
        self.download_requests.append(font.identifier)
        destination.write_text(self._payload, encoding="utf-8")


@pytest.fixture
def sample_font() -> IconFont:
    return IconFont(
        identifier="material-symbols-sample",
        source_id="sample-source",
        display_name="Material Symbols",
        style_label="Outlined",
        font_family="Material Symbols Outlined",
        codepoints_resource="unused",
        font_files=(),
        default_enabled=True,
    )


@pytest.fixture
def codepoints_payload(fixtures_path: Path) -> str:
    return (fixtures_path / "material_symbols_outlined_sample.codepoints").read_text(
        encoding="utf-8"
    )


@pytest.fixture
def recording_source(codepoints_payload: str) -> RecordingFontSource:
    return RecordingFontSource(identifier="sample-source", payload=codepoints_payload)


@pytest.fixture
def repository(
    tmp_path: Path, sample_font: IconFont, recording_source: RecordingFontSource
) -> IconRepository:
    return IconRepository(
        cache_dir=tmp_path,
        fonts=(sample_font,),
        font_sources=(recording_source,),
    )


class TestIconRepository:
    def test_get_glyphs_downloads_and_parses(
        self, repository: IconRepository, sample_font: IconFont
    ) -> None:
        glyphs = repository.get_glyphs([sample_font.identifier])
        assert [glyph.name for glyph in glyphs] == [
            "10k",
            "10mp",
            "360",
            "ac_unit",
            "bolt",
        ]
        first = glyphs[0]
        assert first.font_id == sample_font.identifier
        assert first.character == chr(int("e951", 16))

    def test_search_respects_query_tokens(
        self, repository: IconRepository, sample_font: IconFont
    ) -> None:
        matches = repository.search([sample_font.identifier], "outlined unit")
        assert [match.name for match in matches] == ["ac_unit"]

    def test_empty_query_returns_all_sorted(
        self, repository: IconRepository, sample_font: IconFont
    ) -> None:
        matches = repository.search([sample_font.identifier], "")
        assert [match.name for match in matches] == [
            "10k",
            "10mp",
            "360",
            "ac_unit",
            "bolt",
        ]

    def test_cached_glyphs_avoid_redownload(
        self,
        repository: IconRepository,
        sample_font: IconFont,
        recording_source: RecordingFontSource,
    ) -> None:
        assert repository.ensure_font(sample_font.identifier)
        assert repository.ensure_font(sample_font.identifier)
        assert recording_source.download_requests.count(sample_font.identifier) == 1

    def test_refresh_forces_redownload(
        self,
        repository: IconRepository,
        sample_font: IconFont,
        recording_source: RecordingFontSource,
    ) -> None:
        assert repository.ensure_font(sample_font.identifier)
        assert repository.ensure_font(sample_font.identifier, refresh=True)
        assert recording_source.download_requests.count(sample_font.identifier) == 2

    def test_ensure_font_returns_false_for_unknown_font(self, repository: IconRepository) -> None:
        assert repository.ensure_font("unknown-font") is False


@pytest.mark.download
class TestIconRepositoryDownload:
    def test_material_symbols_outlined_can_download(self, tmp_path: Path) -> None:
        repository = IconRepository(cache_dir=tmp_path)
        assert repository.ensure_font("material-symbols-outlined", refresh=True)

    def test_material_symbols_sharp_can_download(self, tmp_path: Path) -> None:
        repository = IconRepository(cache_dir=tmp_path)
        assert repository.ensure_font("material-symbols-sharp", refresh=True)

    def test_material_design_icons_regular_can_download(self, tmp_path: Path) -> None:
        repository = IconRepository(cache_dir=tmp_path)
        assert repository.ensure_font("material-design-icons-regular", refresh=True)

    def test_search_after_download_uses_live_data(self, tmp_path: Path) -> None:
        repository = IconRepository(cache_dir=tmp_path)
        assert repository.ensure_font("material-symbols-rounded", refresh=True)
        matches = repository.search(["material-symbols-rounded"], "alarm")
        assert matches, "expected at least one alarm glyph"
