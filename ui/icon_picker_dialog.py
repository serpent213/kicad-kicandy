from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import wx


@dataclass
class IconListRow:
    glyph: str
    name: str
    font_label: str
    font_family: str
    payload: Any


class IconPickerDialog(wx.Dialog):
    def __init__(
        self,
        fonts: Sequence[Tuple[str, str]],
        layers: Sequence[Tuple[str, Any]],
        parent: Optional[wx.Window] = None,
    ):
        super().__init__(
            parent,
            title="Kicandy Icon Picker",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.fonts = list(fonts)
        self.layers = list(layers)
        self._font_checkboxes: Dict[str, wx.CheckBox] = {}
        self._font_render_map: Dict[str, wx.Font] = {}
        self._rows: List[IconListRow] = []

        self._build_ui()
        self._populate_fonts()
        self._populate_layers()

    def _build_ui(self) -> None:
        self.SetSizeHints(wx.Size(600, 480))
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        # Search controls
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search_ctrl = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_ctrl.SetDescriptiveText("Search icons…")
        search_sizer.Add(self.search_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        root_sizer.Add(search_sizer, 0, wx.EXPAND)

        # Font filters
        font_box = wx.StaticBox(self, label="Icon Sets")
        font_sizer = wx.StaticBoxSizer(font_box, wx.HORIZONTAL)
        self.font_grid = wx.FlexGridSizer(0, 2, 2, 10)
        self.font_grid.AddGrowableCol(0)
        font_sizer.Add(self.font_grid, 1, wx.ALL | wx.EXPAND, 5)
        root_sizer.Add(font_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # Icon list
        self.icon_list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.LC_VRULES,
        )
        self.icon_list.InsertColumn(0, "Icon", width=100)
        self.icon_list.InsertColumn(1, "Name", width=300)
        self.icon_list.InsertColumn(2, "Font", width=160)
        root_sizer.Add(self.icon_list, 1, wx.EXPAND | wx.ALL, 5)

        # Status + layer selection
        status_row = wx.BoxSizer(wx.HORIZONTAL)
        self.status_text = wx.StaticText(self, label="Ready")
        status_row.Add(self.status_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        layer_label = wx.StaticText(self, label="Layer")
        status_row.Add(layer_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)

        self.layer_choice = wx.Choice(self)
        status_row.Add(self.layer_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        root_sizer.Add(status_row, 0, wx.EXPAND)

        # Buttons
        button_row = wx.StdDialogButtonSizer()
        self.add_button = wx.Button(self, label="Add Icon")
        self.cancel_button = wx.Button(self, id=wx.ID_CANCEL)
        self.add_button.Disable()
        button_row.AddButton(self.add_button)
        button_row.AddButton(self.cancel_button)
        button_row.Realize()
        root_sizer.Add(button_row, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(root_sizer)
        self.Layout()

        # Event wiring
        self.search_ctrl.Bind(wx.EVT_TEXT, self._handle_search)
        self.search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._handle_search)
        self.icon_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._update_add_button_state)
        self.icon_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._update_add_button_state)
        self.icon_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._handle_icon_activated)
        self.add_button.Bind(wx.EVT_BUTTON, self._handle_add)
        self.Bind(wx.EVT_CLOSE, self._handle_close)

    def _populate_fonts(self) -> None:
        for identifier, label in self.fonts:
            checkbox = wx.CheckBox(font_box, label=label)
            checkbox.SetValue(True)
            checkbox.Bind(
                wx.EVT_CHECKBOX,
                lambda event, font_id=identifier: self.on_font_toggled(font_id, event.IsChecked()),
            )
            self.font_grid.Add(checkbox, 0, wx.ALL, 2)
            self._font_checkboxes[identifier] = checkbox

    def _populate_layers(self) -> None:
        for label, payload in self.layers:
            self.layer_choice.Append(label, payload)
        if self.layer_choice.GetCount() > 0:
            self.layer_choice.SetSelection(0)

    def _handle_search(self, _: wx.Event) -> None:
        self.on_search_changed(self.search_ctrl.GetValue())

    def _handle_icon_activated(self, _: wx.ListEvent) -> None:
        self.on_icon_activated()

    def _handle_add(self, _: wx.CommandEvent) -> None:
        self.on_add_requested()

    def _handle_close(self, event: wx.CloseEvent) -> None:
        self.on_close_requested()
        event.Skip()

    def _update_add_button_state(self, _: Optional[wx.ListEvent] = None) -> None:
        self.add_button.Enable(self.icon_list.GetFirstSelected() != -1)

    # --- Hooks for subclasses -------------------------------------------------
    def on_search_changed(self, value: str) -> None:  # pragma: no cover - virtual
        pass

    def on_font_toggled(self, font_id: str, enabled: bool) -> None:  # pragma: no cover - virtual
        pass

    def on_icon_activated(self) -> None:  # pragma: no cover - virtual
        pass

    def on_add_requested(self) -> None:  # pragma: no cover - virtual
        pass

    def on_close_requested(self) -> None:  # pragma: no cover - virtual
        pass

    # --- Helpers for controller code -----------------------------------------
    def set_status(self, message: str) -> None:
        self.status_text.SetLabel(message)

    def set_font_selected(self, font_id: str, enabled: bool) -> None:
        checkbox = self._font_checkboxes.get(font_id)
        if checkbox is not None:
            checkbox.SetValue(enabled)

    def get_enabled_fonts(self) -> List[str]:
        result = []
        for font_id, checkbox in self._font_checkboxes.items():
            if checkbox.GetValue():
                result.append(font_id)
        return result

    def set_search_text(self, text: str) -> None:
        self.search_ctrl.SetValue(text)

    def set_layer_value(self, payload: Any) -> None:
        for index in range(self.layer_choice.GetCount()):
            if self.layer_choice.GetClientData(index) == payload:
                self.layer_choice.SetSelection(index)
                return

    def get_layer_value(self) -> Any:
        index = self.layer_choice.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        return self.layer_choice.GetClientData(index)

    def set_rows(self, rows: Sequence[IconListRow]) -> None:
        self._rows = list(rows)
        self.icon_list.DeleteAllItems()
        for idx, row in enumerate(self._rows):
            self.icon_list.InsertItem(idx, row.glyph)
            self.icon_list.SetItem(idx, 1, row.name)
            self.icon_list.SetItem(idx, 2, row.font_label)
            font = self._get_font_for_family(row.font_family)
            if font is not None:
                self.icon_list.SetItemFont(idx, font)
        self._update_add_button_state()
        self.set_status(f"Showing {len(self._rows)} icons")

    def get_selected_row(self) -> Optional[IconListRow]:
        index = self.icon_list.GetFirstSelected()
        if index == -1 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _get_font_for_family(self, family: str) -> Optional[wx.Font]:
        if family not in self._font_render_map:
            info = wx.FontInfo(24).Family(wx.FONTFAMILY_DEFAULT).FaceName(family)
            self._font_render_map[family] = wx.Font(info)
        return self._font_render_map[family]
