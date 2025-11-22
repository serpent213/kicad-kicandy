from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from icon_fonts import (
    ICON_FONTS,
    IconFont,
    get_font_install_paths,
    install_font_files,
    remove_font_files,
)
from icon_repository import IconRepository
from state_store import PluginState

try:  # pragma: no cover - wx is unavailable in unit tests
    import wx
except ImportError:  # pragma: no cover - handled gracefully
    wx = None  # type: ignore[assignment]


_NEW_FONTS_INSTALLED = False


def mark_fonts_installed() -> None:
    global _NEW_FONTS_INSTALLED
    _NEW_FONTS_INSTALLED = True


def fonts_pending_restart() -> bool:
    return _NEW_FONTS_INSTALLED


@dataclass(frozen=True)
class FontStatusRow:
    identifier: str
    family: str
    display_name: str
    style_label: str
    weights_count: int
    glyph_count: int
    is_installed: bool
    codepoints_cached: bool
    wx_available: bool
    info_url: str | None
    license_text: str | None
    deleted: bool
    installable: bool
    uninstallable: bool


class FontManager:
    def __init__(
        self,
        repository: IconRepository,
        state: PluginState,
        fonts: Sequence[IconFont] | None = None,
    ) -> None:
        self.repository = repository
        self.state = state
        resolved_fonts = tuple(fonts) if fonts is not None else ICON_FONTS
        self._font_map: dict[str, IconFont] = {font.identifier: font for font in resolved_fonts}

    def available_fonts(self) -> list[IconFont]:
        deleted = self.state.model.deleted_fonts
        fonts = [font for font in self._font_map.values() if font.identifier not in deleted]
        return sorted(fonts, key=lambda item: item.display_name)

    def get_font(self, identifier: str) -> IconFont | None:
        return self._font_map.get(identifier)

    def font_status_rows(self) -> list[FontStatusRow]:
        enumerator = wx.FontEnumerator() if wx is not None else None
        deleted = self.state.model.deleted_fonts
        rows: list[FontStatusRow] = []
        for font in self._font_map.values():
            install_paths = get_font_install_paths(font)
            installable = bool(install_paths)
            installed = any(path.exists() for path in install_paths)
            uninstallable = bool(install_paths) and installed
            codepoints_cached = self.repository.has_cached_font(font.identifier)
            glyph_count = (
                self.repository.cached_glyph_count(font.identifier) if codepoints_cached else 0
            )
            rows.append(
                FontStatusRow(
                    identifier=font.identifier,
                    family=font.font_family,
                    display_name=font.display_name,
                    style_label=font.style_label,
                    weights_count=len(font.available_weights),
                    glyph_count=glyph_count,
                    is_installed=installed,
                    codepoints_cached=codepoints_cached,
                    wx_available=enumerator.IsValidFacename(font.font_family)
                    if enumerator is not None
                    else False,
                    info_url=font.info_url,
                    license_text=font.license_text,
                    deleted=font.identifier in deleted,
                    installable=installable,
                    uninstallable=uninstallable,
                )
            )
        rows.sort(key=lambda item: item.family.lower())
        return rows

    def install_fonts(
        self,
        font_ids: Sequence[str],
        *,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> None:
        fonts = [self._font_map[font_id] for font_id in font_ids if font_id in self._font_map]
        if not fonts:
            return
        installed = install_font_files(
            fonts, source_label="Selected fonts", progress_cb=progress_cb
        )
        if not installed:
            return
        mark_fonts_installed()
        deleted = set(self.state.model.deleted_fonts)
        updated = deleted.difference(font.identifier for font in fonts)
        if updated != deleted:
            self.state.update_deleted_fonts(updated)

    def uninstall_fonts(self, font_ids: Sequence[str]) -> list[str]:
        candidates: list[IconFont] = []
        for font_id in font_ids:
            font = self._font_map.get(font_id)
            if font is None:
                continue
            paths = get_font_install_paths(font)
            if not paths:
                continue
            if not any(path.exists() for path in paths):
                continue
            candidates.append(font)
        if not candidates:
            return []
        removed = remove_font_files(candidates)
        if not removed:
            return []
        deleted = set(self.state.model.deleted_fonts)
        for font in candidates:
            deleted.add(font.identifier)
        self.state.update_deleted_fonts(deleted)
        return [font.identifier for font in candidates]

    def deleted_fonts(self) -> set[str]:
        return set(self.state.model.deleted_fonts)
