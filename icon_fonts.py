"""Metadata describing available icon font sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IconFontFile:
    """Downloadable font file that may be offered to the user later on."""

    url: str
    format: str


@dataclass(frozen=True)
class IconFont:
    identifier: str
    display_name: str
    style_label: str
    font_family: str
    codepoints_url: str
    font_files: tuple[IconFontFile, ...]
    default_enabled: bool = True


def _font_files(filename: str) -> tuple[IconFontFile, ...]:
    base = "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
    return (
        IconFontFile(url=f"{base}{filename}.ttf", format="ttf"),
        IconFontFile(url=f"{base}{filename}.woff2", format="woff2"),
    )


ICON_FONTS: tuple[IconFont, ...] = (
    IconFont(
        identifier="material-symbols-outlined",
        display_name="Material Symbols",
        style_label="Outlined",
        font_family="Material Symbols Outlined",
        codepoints_url=(
            "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
            "MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.codepoints"
        ),
        font_files=_font_files("MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D"),
        default_enabled=True,
    ),
    IconFont(
        identifier="material-symbols-rounded",
        display_name="Material Symbols",
        style_label="Rounded",
        font_family="Material Symbols Rounded",
        codepoints_url=(
            "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
            "MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D.codepoints"
        ),
        font_files=_font_files("MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D"),
        default_enabled=True,
    ),
    IconFont(
        identifier="material-symbols-sharp",
        display_name="Material Symbols",
        style_label="Sharp",
        font_family="Material Symbols Sharp",
        codepoints_url=(
            "https://raw.githubusercontent.com/google/material-design-icons/master/variablefont/"
            "MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D.codepoints"
        ),
        font_files=_font_files("MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D"),
        default_enabled=True,
    ),
)


ICON_FONTS_BY_ID: dict[str, IconFont] = {font.identifier: font for font in ICON_FONTS}


def ordered_fonts(font_ids: list[str] | None = None) -> list[IconFont]:
    if not font_ids:
        return list(ICON_FONTS)
    return [
        ICON_FONTS_BY_ID[identifier] for identifier in font_ids if identifier in ICON_FONTS_BY_ID
    ]
