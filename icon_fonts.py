"""Metadata describing available icon font sources."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


@dataclass(frozen=True)
class IconFontFile:
    """Downloadable font file that may be offered to the user later on."""

    url: str
    format: str


FONT_WEIGHT_NAMES: tuple[str, ...] = (
    "Thin",
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "Semibold",
    "Bold",
)

DEFAULT_FONT_WEIGHT = "Regular"
BOLD_FONT_WEIGHT = "Bold"
_FONT_WEIGHT_INDEX = {name: index for index, name in enumerate(FONT_WEIGHT_NAMES, start=1)}


def weight_name_for_position(position: int) -> str:
    clamped = max(1, min(len(FONT_WEIGHT_NAMES), position))
    return FONT_WEIGHT_NAMES[clamped - 1]


def weight_position_for_name(name: str) -> int:
    return _FONT_WEIGHT_INDEX.get(name, _FONT_WEIGHT_INDEX[DEFAULT_FONT_WEIGHT])


def resolve_weight_choice(desired: str, available: Sequence[str]) -> str:
    desired_pos = weight_position_for_name(desired)
    best_name = desired
    best_pos = None
    best_distance = None
    for name in available:
        if name not in _FONT_WEIGHT_INDEX:
            continue
        candidate_pos = _FONT_WEIGHT_INDEX[name]
        distance = abs(candidate_pos - desired_pos)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_pos = candidate_pos
            best_name = name
            continue
        if distance == best_distance and best_pos is not None and candidate_pos > best_pos:
            best_pos = candidate_pos
            best_name = name
    if best_distance is None:
        return desired
    return best_name


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
    available_weights: tuple[str, ...] = (DEFAULT_FONT_WEIGHT,)
    info_url: str | None = None
    license_text: str | None = None


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


def _download_text_resource(url: str) -> str:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
            return response.read().decode("utf-8")
    except (URLError, HTTPError) as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Unable to download {url}: {exc}") from exc


def _install_ttf_fonts(
    source_label: str, fonts: tuple[IconFont, ...], download_url: str | None
) -> None:
    install_font_files(fonts, source_label=source_label, download_url=download_url)


def _copy_font_files(
    targets: list[tuple[IconFont, IconFontFile]],
    destination: Path,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    total = len(targets)
    completed = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        for _, font_file in targets:
            filename = Path(font_file.url).name
            temp_path = temp_root / filename
            _download_to_path(font_file.url, temp_path)
            shutil.copy2(temp_path, destination / filename)
            completed += 1
            if progress_cb is not None:
                progress_cb(completed, total)


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


def install_font_files(
    fonts: Sequence[IconFont],
    *,
    source_label: str | None = None,
    download_url: str | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> bool:
    targets = _collect_ttf_targets(fonts)
    label = source_label or "Selected fonts"
    if not targets:
        raise RuntimeError(f"No TTF downloads defined for {label}.")

    destination = _resolve_install_destination(create=True)
    if destination is None:
        _show_manual_install_message(label, download_url)
        return False

    dest_dir, platform_name = destination
    _copy_font_files(targets, dest_dir, progress_cb=progress_cb)
    if platform_name == "windows":
        for font, font_file in targets:
            _register_windows_font(font.font_family, Path(font_file.url).name)
    if platform_name == "linux":
        _refresh_font_cache(dest_dir)
    return True


def remove_font_files(fonts: Sequence[IconFont]) -> bool:
    destination = _resolve_install_destination(create=False)
    if destination is None:
        return False

    dest_dir, platform_name = destination
    removed = False
    for font in fonts:
        for path in get_font_install_paths(font, dest_dir):
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    continue
                removed = True
    if not removed:
        return False
    if platform_name == "windows":
        for font in fonts:
            _unregister_windows_font(font.font_family)
    if platform_name == "linux":
        _refresh_font_cache(dest_dir)
    return True


def get_font_install_paths(font: IconFont, destination: Path | None = None) -> list[Path]:
    if destination is None:
        resolved = _resolve_install_destination(create=False)
        if resolved is None:
            return []
        destination, _ = resolved
    paths: list[Path] = []
    for font_file in font.font_files:
        if font_file.format.lower() != "ttf":
            continue
        paths.append(destination / Path(font_file.url).name)
    return paths


def _collect_ttf_targets(fonts: Sequence[IconFont]) -> list[tuple[IconFont, IconFontFile]]:
    targets: list[tuple[IconFont, IconFontFile]] = []
    for font in fonts:
        for font_file in font.font_files:
            if font_file.format.lower() == "ttf":
                targets.append((font, font_file))
    return targets


def _resolve_install_destination(create: bool = True) -> tuple[Path, str] | None:
    system = platform.system().lower()
    if system == "darwin":
        dest_dir = Path.home() / "Library" / "Fonts"
        if create:
            dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir, "darwin"
    if system == "windows":
        dest_dir = _resolve_windows_font_dir()
        return dest_dir, "windows"
    if system == "linux":
        dest_dir = Path.home() / ".local" / "share" / "fonts"
        if create:
            dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir, "linux"
    return None


def _refresh_font_cache(destination: Path) -> None:
    try:
        subprocess.run(["fc-cache", "-f", str(destination)], check=False)
    except FileNotFoundError:
        pass


def _unregister_windows_font(display_name: str) -> None:
    registry_value = f"{display_name} (TrueType)"
    subprocess.run(
        [
            "reg",
            "delete",
            "HKCU\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
            "/v",
            registry_value,
            "/f",
        ],
        check=False,
    )


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
                available_weights=FONT_WEIGHT_NAMES,
                info_url="https://fonts.google.com/icons",
                license_text="Apache License 2.0",
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
                available_weights=FONT_WEIGHT_NAMES,
                info_url="https://fonts.google.com/icons",
                license_text="Apache License 2.0",
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
                available_weights=FONT_WEIGHT_NAMES,
                info_url="https://fonts.google.com/icons",
                license_text="Apache License 2.0",
            ),
        )

    def download_codepoints(self, font: IconFont, destination: Path) -> None:
        _download_to_path(font.codepoints_resource, destination)


class MaterialDesignIconsFontSource(IconFontSource):
    identifier = "material-design-icons"
    install_url = "https://github.com/Templarian/MaterialDesign-Font"

    def _build_fonts(self) -> tuple[IconFont, ...]:
        return (
            IconFont(
                identifier="material-design-icons-regular",
                source_id=self.identifier,
                display_name="Material Design Icons",
                style_label="Regular",
                font_family="Material Design Icons Desktop",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/meta.json"
                ),
                font_files=(
                    IconFontFile(
                        url=(
                            "https://raw.githubusercontent.com/Templarian/MaterialDesign-Font/master/"
                            "MaterialDesignIconsDesktop.ttf"
                        ),
                        format="ttf",
                    ),
                ),
                default_enabled=True,
                info_url="https://pictogrammers.com/library/mdi/",
                license_text="Apache License 2.0",
            ),
        )

    def download_codepoints(self, font: IconFont, destination: Path) -> None:
        payload = _download_text_resource(font.codepoints_resource)
        try:
            metadata = json.loads(payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - malformed upstream data
            raise RuntimeError("Invalid Material Design Icons metadata") from exc

        if not isinstance(metadata, list):
            raise RuntimeError("Unexpected Material Design Icons metadata structure")

        lines: list[str] = []
        for entry in metadata:
            if not isinstance(entry, dict):
                continue
            if entry.get("deprecated"):
                continue
            name = entry.get("name")
            codepoint = entry.get("codepoint")
            if not isinstance(name, str) or not isinstance(codepoint, str):
                continue
            if not name or not codepoint:
                continue
            lines.append(f"{name} {codepoint}")

        if not lines:
            raise RuntimeError("No Material Design Icons glyphs were extracted")

        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


class RemixIconFontSource(IconFontSource):
    identifier = "remix-icon"
    install_url = "https://github.com/Remix-Design/RemixIcon"
    _CSS_GLYPH_PATTERN = re.compile(
        r"""
        \.ri-([a-z0-9-]+):before\s*\{\s*content:\s*['\"]\\([0-9a-fA-F]+)['\"];?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def _build_fonts(self) -> tuple[IconFont, ...]:
        return (
            IconFont(
                identifier="remix-icon-regular",
                source_id=self.identifier,
                display_name="Remix Icon",
                style_label="Regular",
                font_family="Remix Icon",
                codepoints_resource=(
                    "https://raw.githubusercontent.com/Remix-Design/RemixIcon/refs/heads/master/fonts/remixicon.css"
                ),
                font_files=(
                    IconFontFile(
                        url=(
                            "https://raw.githubusercontent.com/Remix-Design/RemixIcon/refs/heads/master/fonts/remixicon.ttf"
                        ),
                        format="ttf",
                    ),
                ),
                default_enabled=True,
                info_url="https://remixicon.com",
                license_text="Apache License 2.0",
            ),
        )

    def download_codepoints(self, font: IconFont, destination: Path) -> None:
        payload = _download_text_resource(font.codepoints_resource)
        lines: list[str] = []
        for match in self._CSS_GLYPH_PATTERN.finditer(payload):
            name, codepoint = match.groups()
            if not name or not codepoint:
                continue
            lines.append(f"{name} {codepoint.lower()}")

        if not lines:
            raise RuntimeError("No Remix Icon glyphs were extracted")

        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
