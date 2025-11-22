from __future__ import annotations

import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import wx
from kipy import KiCad
from kipy.board import BoardLayerClass
from kipy.board_types import BoardLayer, BoardText
from kipy.geometry import Vector2

from icon_fonts import BOLD_FONT_WEIGHT, ICON_FONTS, IconFont
from icon_repository import IconDownloadError, IconGlyph, IconRepository, resolve_cache_dir
from state_store import PluginState
from ui.icon_picker_dialog import IconListRow, IconPickerDialog

LAYER_CHOICES = [
    ("Front Silkscreen (F.SilkS)", BoardLayer.BL_F_SilkS),
    ("Back Silkscreen (B.SilkS)", BoardLayer.BL_B_SilkS),
]

STATE_PATH = resolve_cache_dir() / "kicandy_state.json"
PROFILE_TXT_OUTPUT_PATH = Path("/tmp/kicandy_profile.txt")
PROFILE_HTML_OUTPUT_PATH = Path("/tmp/kicandy_profile.html")
_WX_APP: wx.App | None = None


@dataclass
class FontDetectionResult:
    offered_fonts: list[IconFont]
    missing_fonts: list[str]
    failed_fonts: list[str]


def _detect_available_fonts(repository: IconRepository) -> FontDetectionResult:
    enumerator = wx.FontEnumerator()
    offered: list[IconFont] = []
    missing: list[str] = []
    failed: list[str] = []
    for font in ICON_FONTS:
        label = f"{font.display_name} {font.style_label}"
        if not enumerator.IsValidFacename(font.font_family):
            missing.append(label)
            continue
        if not repository.ensure_font(font.identifier):
            failed.append(label)
            continue
        offered.append(font)
    return FontDetectionResult(
        offered_fonts=offered,
        missing_fonts=missing,
        failed_fonts=failed,
    )


class _Profiler(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def output_text(self, unicode: bool = False, color: bool = False) -> str: ...

    def output_html(self) -> str: ...


class KicandyDialog(IconPickerDialog):
    def __init__(self) -> None:
        repository = IconRepository()
        detection = _detect_available_fonts(repository)
        font_choices = [
            (font.identifier, f"{font.display_name} ({font.style_label})")
            for font in detection.offered_fonts
        ]
        font_weights = {font.identifier: font.available_weights for font in detection.offered_fonts}

        super().__init__(
            fonts=font_choices,
            layers=LAYER_CHOICES,
            font_weights=font_weights,
            parent=None,
        )

        self.kicad = KiCad()
        self.board = self.kicad.get_board()
        self.repository = repository
        self.state = PluginState(STATE_PATH)
        self._font_detection = detection
        self._offered_font_ids = [font.identifier for font in detection.offered_fonts]
        self._last_download_failed = False
        self._disconnect_handled = False
        self._register_disconnect_handler()

        self._restore_state()
        # Initial refresh runs via the search control's EVT_TEXT fired during _restore_state.

    # --- Event hooks --------------------------------------------------------
    def on_search_changed(self, _: str) -> None:
        self._refresh_icons()

    def on_font_toggled(self, _: str, __: bool) -> None:
        self._refresh_icons()

    def on_icon_activated(self) -> None:
        self._add_selected_icon()

    def on_add_requested(self) -> None:
        self._add_selected_icon()

    def on_close_requested(self) -> None:
        self._persist_state()

    # --- Internal helpers ---------------------------------------------------
    def _restore_state(self) -> None:
        self.set_font_weight(self.state.model.font_weight)
        self.set_search_text(self.state.model.search)
        for font_id in self._offered_font_ids:
            enabled = self.state.model.enabled_fonts.get(font_id, True)
            self.set_font_selected(font_id, enabled)
        self.set_layer_value(self.state.model.layer)
        if self.layer_choice.GetSelection() == wx.NOT_FOUND and self.layer_choice.GetCount() > 0:
            self.layer_choice.SetSelection(0)
        self.set_font_size_mm(self.state.model.font_size_mm)

    def _persist_state(self) -> None:
        enabled_values = set(self.get_enabled_fonts())
        enabled_map = dict(self.state.model.enabled_fonts)
        for font_id in self._offered_font_ids:
            enabled_map[font_id] = font_id in enabled_values
        layer = self.get_layer_value() or BoardLayer.BL_F_SilkS
        self.state.update(
            search=self.search_ctrl.GetValue(),
            layer=layer,
            enabled_fonts=enabled_map,
            font_size_mm=self.get_font_size_mm(),
            font_weight=self.get_font_weight(),
        )

    def _refresh_icons(self) -> None:
        if not self._offered_font_ids:
            self.set_rows([])
            detail_parts: list[str] = []
            if self._font_detection.missing_fonts:
                detail_parts.append(
                    "Missing fonts: " + ", ".join(self._font_detection.missing_fonts)
                )
            if self._font_detection.failed_fonts:
                detail_parts.append(
                    "Metadata unavailable: " + ", ".join(self._font_detection.failed_fonts)
                )
            detail_suffix = f" ({' | '.join(detail_parts)})" if detail_parts else ""
            self.set_status(f"Install supported icon fonts to browse icons{detail_suffix}")
            return

        enabled_fonts = self.get_enabled_fonts()
        if not enabled_fonts:
            self.set_rows([])
            self.set_status("Enable at least one icon set to browse icons")
            return

        try:
            glyphs = self.repository.search(enabled_fonts, self.search_ctrl.GetValue())
            self._last_download_failed = False
        except IconDownloadError as exc:
            if not self._last_download_failed:
                wx.MessageBox(str(exc), "Icon download failed", parent=self)
            self._last_download_failed = True
            self.set_rows([])
            self.set_status("Unable to load icon metadata. Check network access.")
            return

        rows = [
            IconListRow(
                font_id=glyph.font_id,
                glyph=glyph.character,
                name=glyph.name.replace("_", " "),
                font_label=glyph.font_label,
                font_family=glyph.font_family,
                payload=glyph,
            )
            for glyph in glyphs
        ]
        self.set_rows(rows)

    def _add_selected_icon(self) -> None:
        row = self.get_selected_row()
        if row is None:
            return
        glyph = row.payload
        if not isinstance(glyph, IconGlyph):
            return

        layer = self.get_layer_value() or BoardLayer.BL_F_SilkS
        text = BoardText()
        text.layer = layer
        text.value = glyph.character
        text.position = Vector2.from_xy_mm(0.0, 0.0)
        defaults = self.board.get_graphics_defaults()[BoardLayerClass.BLC_SILKSCREEN]
        text.attributes = defaults.text
        text.attributes.font_name = glyph.font_family
        font_size_mm = self.get_font_size_mm()
        text.attributes.size = Vector2.from_xy_mm(font_size_mm, font_size_mm)
        resolved_weight = self.get_resolved_font_weight(glyph.font_id)
        text.attributes.bold = resolved_weight == BOLD_FONT_WEIGHT
        text.attributes.mirrored = layer == BoardLayer.BL_B_SilkS

        created = self.board.create_items(text)
        if created:
            created_text = created[0]
            if isinstance(created_text, BoardText):
                self.board.interactive_move(created_text.id)

        self._persist_state()
        self.EndModal(wx.ID_OK)

    def EndModal(self, ret_code: int) -> None:  # type: ignore[override]
        self._disconnect_handled = True
        super().EndModal(ret_code)

    def _register_disconnect_handler(self) -> None:
        on_disconnect = getattr(self.kicad, "on_disconnect", None)
        if not callable(on_disconnect):
            return

        dialog_ref = weakref.ref(self)

        def _handle_disconnect_callback() -> None:
            dialog = dialog_ref()
            if dialog is None:
                return
            if hasattr(dialog, "IsBeingDeleted") and dialog.IsBeingDeleted():
                return
            wx.CallAfter(dialog._handle_kicad_disconnect)

        try:
            on_disconnect(_handle_disconnect_callback)
        except Exception:
            pass

    def _handle_kicad_disconnect(self) -> None:
        if self._disconnect_handled:
            return
        if hasattr(self, "IsBeingDeleted") and self.IsBeingDeleted():
            return
        self._disconnect_handled = True
        self.set_status("Lost connection to KiCad; closing")
        self._persist_state()
        self.EndModal(wx.ID_CANCEL)


def _ensure_wx_app() -> wx.App:
    global _WX_APP
    app = wx.GetApp()
    if app is not None:
        return app
    if _WX_APP is None:
        _WX_APP = wx.App()
    return _WX_APP


def main() -> None:
    profiler = _start_profiler()
    try:
        _ensure_wx_app()
        dialog = KicandyDialog()
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()
    finally:
        _finalize_profiler(profiler)


def _start_profiler() -> _Profiler | None:
    try:
        from pyinstrument import Profiler
    except ModuleNotFoundError:
        return None

    profiler = Profiler()
    profiler.start()
    return profiler


def _finalize_profiler(profiler: _Profiler | None) -> None:
    if profiler is None:
        return

    try:
        profiler.stop()
        PROFILE_TXT_OUTPUT_PATH.write_text(
            profiler.output_text(unicode=True, color=False), encoding="utf-8"
        )
        PROFILE_HTML_OUTPUT_PATH.write_text(profiler.output_html(), encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    main()
