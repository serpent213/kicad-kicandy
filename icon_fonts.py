"""Metadata describing available icon font sources."""

from __future__ import annotations

import os
import platform
import shutil
import ssl
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


@dataclass(frozen=True)
class IconFontFile:
    """Downloadable font file that may be offered to the user later on."""

    url: str
    format: str


@dataclass(frozen=True)
class IconFont:
    identifier: str
    source_id: str
    display_name: str
    style_label: str
    font_family: str
    codepoints_resource: str
    font_files: tuple[IconFontFile, ...]
    default_enabled: bool = True


class IconFontSource(ABC):
    """Provide font metadata plus helpers for codepoint/font downloads."""

    identifier: str
    install_url: str | None = None

    def __init__(self) -> None:
        self._fonts = self._build_fonts()

    @property
    def fonts(self) -> tuple[IconFont, ...]:
        return self._fonts

    @abstractmethod
    def _build_fonts(self) -> tuple[IconFont, ...]: ...

    @abstractmethod
    def download_codepoints(self, font: IconFont, destination: Path) -> None: ...

    def install_fonts(self) -> None:
        _install_ttf_fonts(self.identifier, self.fonts, self.install_url)


_USER_AGENT = "kicandy-icon-fetcher"
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _download_to_path(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
            destination.write_bytes(response.read())
    except (URLError, HTTPError) as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Unable to download {url}: {exc}") from exc


def _install_ttf_fonts(
    source_label: str, fonts: tuple[IconFont, ...], download_url: str | None
) -> None:
    ttf_targets: list[tuple[IconFont, IconFontFile]] = []
    for font in fonts:
        for font_file in font.font_files:
            if font_file.format.lower() == "ttf":
                ttf_targets.append((font, font_file))
    if not ttf_targets:
        raise RuntimeError(f"No TTF downloads defined for {source_label}.")

    system = platform.system().lower()
    if system == "darwin":
        dest_dir = Path.home() / "Library" / "Fonts"
        _copy_font_files(ttf_targets, dest_dir)
        return
    if system == "windows":
        dest_dir = _resolve_windows_font_dir()
        _copy_font_files(ttf_targets, dest_dir)
        for font, font_file in ttf_targets:
            _register_windows_font(font.font_family, Path(font_file.url).name)
        return
    _show_manual_install_message(source_label, download_url)


def _copy_font_files(targets: list[tuple[IconFont, IconFontFile]], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        for _, font_file in targets:
            filename = Path(font_file.url).name
            temp_path = temp_root / filename
            _download_to_path(font_file.url, temp_path)
            shutil.copy2(temp_path, destination / filename)


def _resolve_windows_font_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; cannot install fonts.")
    target = Path(local_app_data) / "Microsoft" / "Windows" / "Fonts"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _register_windows_font(display_name: str, filename: str) -> None:
    registry_value = f"{display_name} (TrueType)"
    subprocess.run(
        [
            "reg",
            "add",
            "HKCU\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
            "/v",
            registry_value,
            "/t",
            "REG_SZ",
            "/d",
            filename,
            "/f",
        ],
        check=True,
    )


def _show_manual_install_message(source_label: str, download_url: str | None) -> None:
    try:
        import wx
    except ImportError:  # pragma: no cover - wx not available in tests
        return

    message = f"{source_label} fonts must be installed manually on this platform."
    if download_url:
        message = f"{message}\nDownload from: {download_url}"
    wx.MessageBox(message, "Font installation required", parent=None)


def _font_files(filename: str) -> tuple[IconFontFile, ...]:
    base = "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
    return (
        IconFontFile(url=f"{base}{filename}.ttf", format="ttf"),
        IconFontFile(url=f"{base}{filename}.woff2", format="woff2"),
    )


class MaterialSymbolsFontSource(IconFontSource):
    identifier = "material-symbols"
    install_url = "https://github.com/google/material-design-icons/tree/master/variablefont"

    def _build_fonts(self) -> tuple[IconFont, ...]:
        return (
            IconFont(
                identifier="material-symbols-outlined",
                source_id=self.identifier,
                display_name="Material Symbols",
                style_label="Outlined",
                font_family="Material Symbols Outlined",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
                    "MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.codepoints"
                ),
                font_files=_font_files("MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D"),
                default_enabled=True,
            ),
            IconFont(
                identifier="material-symbols-rounded",
                source_id=self.identifier,
                display_name="Material Symbols",
                style_label="Rounded",
                font_family="Material Symbols Rounded",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
                    "MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D.codepoints"
                ),
                font_files=_font_files("MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D"),
                default_enabled=True,
            ),
            IconFont(
                identifier="material-symbols-sharp",
                source_id=self.identifier,
                display_name="Material Symbols",
                style_label="Sharp",
                font_family="Material Symbols Sharp",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
                    "MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D.codepoints"
                ),
                font_files=_font_files("MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D"),
                default_enabled=True,
            ),
        )

    def download_codepoints(self, font: IconFont, destination: Path) -> None:
        _download_to_path(font.codepoints_resource, destination)


class MaterialDesignIconsFontSource(IconFontSource):
    identifier = "material-design-icons"
    install_url = "https://github.com/Templarian/MaterialDesign-Webfont"

    def _build_fonts(self) -> tuple[IconFont, ...]:
        return (
            IconFont(
                identifier="material-design-icons-regular",
                source_id=self.identifier,
                display_name="Material Design Icons",
                style_label="Regular",
                font_family="Material Design Icons",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/Templarian/MaterialDesign-Webfont/master/meta.json"
                ),
                font_files=(
                    IconFontFile(
                        url=(
                            "https://github.com/Templarian/MaterialDesign-Webfont/raw/master/fonts/"
                            "materialdesignicons-webfont.ttf"
                        ),
                        format="ttf",
                    ),
                ),
                default_enabled=True,
            ),
        )

    def download_codepoints(
        self, font: IconFont, destination: Path
    ) -> None:  # pragma: no cover - stub
        raise RuntimeError("Codepoint conversion for Material Design Icons is not implemented yet.")


class RemixIconFontSource(IconFontSource):
    identifier = "remix-icon"
    install_url = "https://github.com/Remix-Design/RemixIcon"

    def _build_fonts(self) -> tuple[IconFont, ...]:
        return (
            IconFont(
                identifier="remix-icon-regular",
                source_id=self.identifier,
                display_name="Remix Icon",
                style_label="Regular",
                font_family="remixicon",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/Remix-Design/RemixIcon/main/fonts/remixicon.woff2"
                ),
                font_files=(
                    IconFontFile(
                        url=(
                            "https://github.com/Remix-Design/RemixIcon/raw/main/fonts/remixicon.ttf"
                        ),
                        format="ttf",
                    ),
                ),
                default_enabled=True,
            ),
        )

    def download_codepoints(
        self, font: IconFont, destination: Path
    ) -> None:  # pragma: no cover - stub
        raise RuntimeError("Codepoint conversion for Remix Icon is not implemented yet.")


ICON_FONT_SOURCES: tuple[IconFontSource, ...] = (
    MaterialSymbolsFontSource(),
    MaterialDesignIconsFontSource(),
    RemixIconFontSource(),
)

ICON_FONT_SOURCES_BY_ID: dict[str, IconFontSource] = {
    source.identifier: source for source in ICON_FONT_SOURCES
}

ICON_FONTS: tuple[IconFont, ...] = tuple(
    font for source in ICON_FONT_SOURCES for font in source.fonts
)

ICON_FONTS_BY_ID: dict[str, IconFont] = {font.identifier: font for font in ICON_FONTS}


def ordered_fonts(font_ids: list[str] | None = None) -> list[IconFont]:
    if not font_ids:
        return list(ICON_FONTS)
    return [
        ICON_FONTS_BY_ID[identifier] for identifier in font_ids if identifier in ICON_FONTS_BY_ID
    ]
