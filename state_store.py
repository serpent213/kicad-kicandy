"""Save and restore dialog state across plugin invocations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from kipy.board_types import BoardLayer

import settings
from icon_fonts import DEFAULT_FONT_WEIGHT, FONT_WEIGHT_NAMES, ICON_FONTS


@dataclass
class DialogState:
    search: str = ""
    layer: int = BoardLayer.BL_F_SilkS
    enabled_fonts: dict[str, bool] = field(
        default_factory=lambda: {font.identifier: font.default_enabled for font in ICON_FONTS}
    )
    font_size_mm: int = settings.DEFAULT_FONT_SIZE_MM
    font_weight: str = DEFAULT_FONT_WEIGHT


class PluginState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.model = DialogState()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return

        self.model.search = data.get("search", "")
        layer_value = data.get("layer")
        if isinstance(layer_value, int):
            self.model.layer = layer_value

        stored_fonts = data.get("enabled_fonts", {})
        for identifier in self.model.enabled_fonts.keys():
            if identifier in stored_fonts:
                self.model.enabled_fonts[identifier] = bool(stored_fonts[identifier])

        stored_font_size = data.get("font_size_mm")
        if isinstance(stored_font_size, int):
            clamped = max(
                settings.FONT_SIZE_MIN_MM,
                min(settings.FONT_SIZE_MAX_MM, stored_font_size),
            )
            self.model.font_size_mm = clamped

        stored_weight = data.get("font_weight")
        if isinstance(stored_weight, str) and stored_weight in FONT_WEIGHT_NAMES:
            self.model.font_weight = stored_weight

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "search": self.model.search,
            "layer": self.model.layer,
            "enabled_fonts": self.model.enabled_fonts,
            "font_size_mm": self.model.font_size_mm,
            "font_weight": self.model.font_weight,
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def update(
        self,
        *,
        search: str,
        layer: int,
        enabled_fonts: dict[str, bool],
        font_size_mm: int,
        font_weight: str,
    ) -> None:
        self.model.search = search
        self.model.layer = layer
        self.model.enabled_fonts = enabled_fonts
        clamped_size = max(
            settings.FONT_SIZE_MIN_MM,
            min(settings.FONT_SIZE_MAX_MM, font_size_mm),
        )
        self.model.font_size_mm = clamped_size
        if font_weight in FONT_WEIGHT_NAMES:
            self.model.font_weight = font_weight
        else:
            self.model.font_weight = DEFAULT_FONT_WEIGHT
        self.save()
