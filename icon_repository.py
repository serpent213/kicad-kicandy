"""Resolve icon glyph metadata from downloadable codepoint files."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from icon_fonts import ICON_FONT_SOURCES, ICON_FONTS, IconFont, IconFontSource


class IconRepositoryError(RuntimeError):
    pass


class IconDownloadError(IconRepositoryError):
    pass


@dataclass
class IconGlyph:
    font_id: str
    font_family: str
    font_label: str
    name: str
    codepoint: str
    character: str
    search_target: str


def resolve_cache_dir(cache_dir: Path | None = None) -> Path:
    if cache_dir is None:
        cache_home = os.environ.get("KICAD_CACHE_HOME")
        if cache_home:
            plugin_env_dir = Path(cache_home) / "python-environments" / "de.reactor.kicandy"
            if not plugin_env_dir.exists():
                raise IconRepositoryError(f"Missing KiCad plugin cache directory: {plugin_env_dir}")
            resolved_cache_dir = plugin_env_dir / "local"
        else:
            resolved_cache_dir = Path(__file__).parent / "cache"
    else:
        resolved_cache_dir = Path(cache_dir)
    resolved_cache_dir.mkdir(parents=True, exist_ok=True)
    return resolved_cache_dir


class IconRepository:
    def __init__(
        self,
        cache_dir: Path | None = None,
        fonts: Sequence[IconFont] | None = None,
        font_sources: Sequence[IconFontSource] | None = None,
    ) -> None:
        resolved_cache_dir = resolve_cache_dir(cache_dir)
        self.cache_dir = resolved_cache_dir
        resolved_sources = font_sources or ICON_FONT_SOURCES
        self.sources: dict[str, IconFontSource] = {
            source.identifier: source for source in resolved_sources
        }
        resolved_fonts = fonts or ICON_FONTS
        self.fonts = {font.identifier: font for font in resolved_fonts}
        self._glyph_cache: dict[str, list[IconGlyph]] = {}

    def _cache_path(self, font: IconFont) -> Path:
        safe_identifier = font.identifier.replace("/", "_")
        return self.cache_dir / f"{safe_identifier}.codepoints"

    def _download(self, font: IconFont, destination: Path) -> None:
        source = self.sources.get(font.source_id)
        if source is None:
            raise IconDownloadError(
                f"No font source registered for {font.identifier} ({font.source_id})"
            )
        try:
            source.download_codepoints(font, destination)
        except IconDownloadError:
            raise
        except IconRepositoryError:
            raise
        except Exception as exc:  # pragma: no cover - provider specific failure
            raise IconDownloadError(
                f"Unable to download codepoints for {font.identifier}: {exc}"
            ) from exc

    def _parse_codepoints(self, data: str, font: IconFont) -> list[IconGlyph]:
        glyphs: list[IconGlyph] = []
        for line in data.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) != 2:
                continue
            name, codepoint = parts
            character = chr(int(codepoint, 16))
            search_target = " ".join(
                [name.replace("_", " "), font.style_label, font.display_name]
            ).lower()
            glyphs.append(
                IconGlyph(
                    font_id=font.identifier,
                    font_family=font.font_family,
                    font_label=f"{font.display_name} {font.style_label}",
                    name=name,
                    codepoint=codepoint,
                    character=character,
                    search_target=search_target,
                )
            )
        return glyphs

    def _load_glyphs(self, font: IconFont, force_refresh: bool = False) -> list[IconGlyph]:
        if not force_refresh and font.identifier in self._glyph_cache:
            return self._glyph_cache[font.identifier]

        cache_path = self._cache_path(font)
        if force_refresh or not cache_path.exists():
            self._download(font, cache_path)

        data = cache_path.read_text(encoding="utf-8")
        glyphs = self._parse_codepoints(data, font)
        self._glyph_cache[font.identifier] = glyphs
        return glyphs

    def ensure_fonts(self, refresh: bool = False) -> None:
        for font in self.fonts.values():
            self._load_glyphs(font, force_refresh=refresh)

    def ensure_font(self, font_id: str, refresh: bool = False) -> bool:
        font = self.fonts.get(font_id)
        if font is None:
            return False
        try:
            self._load_glyphs(font, force_refresh=refresh)
        except IconDownloadError:
            return False
        return True

    def get_glyphs(self, font_ids: Iterable[str]) -> list[IconGlyph]:
        glyphs: list[IconGlyph] = []
        for font_id in font_ids:
            font = self.fonts.get(font_id)
            if not font:
                continue
            glyphs.extend(self._load_glyphs(font))
        return glyphs

    def get_cache_path(self, font_id: str) -> Path | None:
        font = self.fonts.get(font_id)
        if font is None:
            return None
        return self._cache_path(font)

    def has_cached_font(self, font_id: str) -> bool:
        cache_path = self.get_cache_path(font_id)
        if cache_path is None:
            return False
        return cache_path.exists()

    def cached_glyph_count(self, font_id: str) -> int:
        font = self.fonts.get(font_id)
        if font is None:
            return 0
        cached_rows = self._glyph_cache.get(font.identifier)
        if cached_rows is not None:
            return len(cached_rows)
        cache_path = self._cache_path(font)
        if not cache_path.exists():
            return 0
        try:
            data = cache_path.read_text(encoding="utf-8")
        except OSError:
            return 0
        glyphs = self._parse_codepoints(data, font)
        self._glyph_cache[font.identifier] = glyphs
        return len(glyphs)

    def search(self, font_ids: Iterable[str], query: str) -> list[IconGlyph]:
        glyphs = self.get_glyphs(font_ids)
        tokens = [token for token in query.lower().split() if token]
        if not tokens:
            return sorted(glyphs, key=lambda item: item.name)
        filtered: list[IconGlyph] = []
        for glyph in glyphs:
            if all(token in glyph.search_target for token in tokens):
                filtered.append(glyph)
        return sorted(filtered, key=lambda item: item.name)
