from __future__ import annotations

from collections.abc import Sequence
from typing import Callable

import wx
import wx.dataview as dv

from font_management import FontStatusRow


class ManageIconSetsDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window | None = None,
        *,
        on_install: Callable[[Sequence[str]], None] | None = None,
        on_uninstall: Callable[[Sequence[str]], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Manage Icon Sets",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._rows: list[FontStatusRow] = []
        self._selected_ids: set[str] = set()
        self._busy = False
        self._install_handler: Callable[[Sequence[str]], None] | None = None
        self._uninstall_handler: Callable[[Sequence[str]], None] | None = None
        self.set_install_handler(on_install)
        self.set_uninstall_handler(on_uninstall)
        self._build_ui()
        self.SetSize(wx.Size(900, 420))

    def _build_ui(self) -> None:
        root = wx.BoxSizer(wx.VERTICAL)

        description = wx.StaticText(
            self,
            label=(
                "Select icon sets to install or uninstall. Hidden icon sets stay "
                "disabled in the picker until reinstalled."
            ),
        )
        root.Add(description, 0, wx.ALL | wx.EXPAND, 10)

        self.list_ctrl = dv.DataViewListCtrl(
            self,
            style=dv.DV_ROW_LINES | dv.DV_VERT_RULES | wx.BORDER_THEME,
        )
        self.list_ctrl.AppendToggleColumn("Select", width=70)
        self.list_ctrl.AppendTextColumn("Family", width=200)
        self.list_ctrl.AppendTextColumn("Font installed", width=120)
        self.list_ctrl.AppendTextColumn("Font loaded", width=110)
        self.list_ctrl.AppendTextColumn("Weights", width=70)
        self.list_ctrl.AppendTextColumn("Glyphs", width=70)
        self.list_ctrl.AppendTextColumn("Website", width=180)
        self.list_ctrl.AppendTextColumn("License", width=140)

        # Multi-layered event binding for cross-platform checkbox support
        # EVT_DATAVIEW_ITEM_VALUE_CHANGED works reliably on Windows/Linux
        self.list_ctrl.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self._handle_item_changed)
        # EVT_DATAVIEW_SELECTION_CHANGED catches row switches on all platforms
        self.list_ctrl.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self._handle_selection_changed)
        # EVT_LEFT_DOWN with delayed sync is the macOS fallback for same-row toggles
        self.list_ctrl.Bind(wx.EVT_LEFT_DOWN, self._handle_list_click)
        # EVT_DATAVIEW_ITEM_ACTIVATED for launching website URLs
        self.list_ctrl.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self._handle_item_activated)

        root.Add(self.list_ctrl, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        controls = wx.BoxSizer(wx.HORIZONTAL)
        self.install_button = wx.Button(self, label="Install Fonts")
        self.uninstall_button = wx.Button(self, label="Uninstall Fonts")
        self.install_button.Bind(wx.EVT_BUTTON, self._handle_install)
        self.uninstall_button.Bind(wx.EVT_BUTTON, self._handle_uninstall)

        controls.Add(self.install_button, 0, wx.RIGHT, 5)
        controls.Add(self.uninstall_button, 0, wx.RIGHT, 5)
        controls.AddStretchSpacer()

        self.status_text = wx.StaticText(self, label="")
        controls.Add(self.status_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.close_button = wx.Button(self, id=wx.ID_CANCEL, label="Close")
        controls.Add(self.close_button, 0)

        root.Add(controls, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(root)

    def set_rows(self, rows: Sequence[FontStatusRow]) -> None:
        preserved = set(row.identifier for row in rows)
        self._selected_ids.intersection_update(preserved)
        self._rows = list(rows)
        self.list_ctrl.DeleteAllItems()
        for row in self._rows:
            is_selected = row.identifier in self._selected_ids
            ttf_status = self._font_installed_label(row)
            wx_status = "Yes" if row.wx_available else "No"
            website = row.info_url or "-"
            license_text = row.license_text or "-"
            self.list_ctrl.AppendItem(
                [
                    is_selected,
                    row.family,
                    ttf_status,
                    wx_status,
                    str(row.weights_count),
                    "?" if not row.wx_available else str(row.glyph_count),
                    website,
                    license_text,
                ]
            )
        self._update_button_states()

    def _font_installed_label(self, row: FontStatusRow) -> str:
        if row.is_installed:
            return "User"
        if row.wx_available:
            return "System"
        return "No"

    def set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        self.install_button.Enable(not busy)
        self.uninstall_button.Enable(not busy)
        self.list_ctrl.Enable(not busy)
        self.close_button.Enable(not busy)
        self.status_text.SetLabel(message)
        if not busy:
            self._update_button_states()

    def get_selected_ids(self) -> list[str]:
        return list(self._selected_ids)

    def _sync_checkbox_states(self) -> None:
        """
        Poll checkbox states directly from list control and sync with internal state.
        This is necessary on macOS where toggle column events are unreliable.
        """
        new_selected = set()
        for i, row in enumerate(self._rows):
            is_checked = self.list_ctrl.GetValue(i, 0)
            if is_checked:
                new_selected.add(row.identifier)

        if new_selected != self._selected_ids:
            self._selected_ids = new_selected
            self._update_button_states()

    def _update_button_states(self) -> None:
        if self._busy:
            self.install_button.Disable()
            self.uninstall_button.Disable()
            return

        install_ready = False
        uninstall_ready = False
        for row in self._rows:
            if row.identifier not in self._selected_ids:
                continue
            if not row.is_installed and row.installable:
                install_ready = True
            if row.uninstallable:
                uninstall_ready = True

        self.install_button.Enable(install_ready)
        self.uninstall_button.Enable(uninstall_ready)

    def _handle_item_changed(self, event: dv.DataViewEvent) -> None:
        """Handle checkbox value changes on platforms where the event fires reliably."""
        row_index = event.GetRow()
        column = event.GetColumn()
        if column != 0 or row_index < 0 or row_index >= len(self._rows):
            return

        identifier = self._rows[row_index].identifier
        is_checked = self.list_ctrl.GetValue(row_index, 0)
        if is_checked:
            self._selected_ids.add(identifier)
        else:
            self._selected_ids.discard(identifier)
        self._update_button_states()

    def _handle_selection_changed(self, event: dv.DataViewEvent) -> None:
        """
        Handle row selection changes.
        On macOS this catches checkbox clicks when switching between rows.
        """
        self._sync_checkbox_states()

    def _handle_list_click(self, event: wx.MouseEvent) -> None:
        """
        Handle mouse clicks on the list control.
        On macOS this is the fallback for detecting same-row checkbox toggles.
        Uses CallLater to allow the native control to update before reading state.
        """
        event.Skip()
        wx.CallLater(250, self._sync_checkbox_states)

    def _handle_item_activated(self, event: dv.DataViewEvent) -> None:
        """Handle double-click on website column to open URL in browser."""
        row_index = event.GetRow()
        column = event.GetColumn()
        if column != 6:
            return
        if row_index < 0 or row_index >= len(self._rows):
            return
        row = self._rows[row_index]
        if row.info_url:
            wx.LaunchDefaultBrowser(row.info_url)

    def _handle_install(self, _: wx.CommandEvent) -> None:
        if self._busy:
            return
        ids = self.get_selected_ids()
        if not ids:
            return
        if self._install_handler is not None:
            self._install_handler(ids)

    def _handle_uninstall(self, _: wx.CommandEvent) -> None:
        if self._busy:
            return
        ids = self.get_selected_ids()
        if not ids:
            return
        if self._uninstall_handler is not None:
            self._uninstall_handler(ids)

    def set_install_handler(self, handler: Callable[[Sequence[str]], None] | None) -> None:
        self._install_handler = handler

    def set_uninstall_handler(self, handler: Callable[[Sequence[str]], None] | None) -> None:
        self._uninstall_handler = handler
