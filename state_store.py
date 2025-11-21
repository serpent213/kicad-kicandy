"""Save and restore dialog state across plugin invocations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from kipy.board_types import BoardLayer

from icon_fonts import ICON_FONTS


@dataclass
class DialogState:
    search: str = ""
    layer: int = BoardLayer.BL_F_SilkS
    enabled_fonts: Dict[str, bool] = field(
        default_factory=lambda: {font.identifier: font.default_enabled for font in ICON_FONTS}
    )


class PluginState:
    def __init__(self, path: Path):
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

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "search": self.model.search,
            "layer": self.model.layer,
            "enabled_fonts": self.model.enabled_fonts,
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def update(self, *, search: str, layer: int, enabled_fonts: Dict[str, bool]) -> None:
        self.model.search = search
        self.model.layer = layer
        self.model.enabled_fonts = enabled_fonts
        self.save()

