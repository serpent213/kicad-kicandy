from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import wx
import wx.grid as grid


@dataclass
class IconListRow:
    glyph: str
    name: str
    font_label: str
    font_family: str
    payload: object


class IconGridTable(grid.GridTableBase):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[IconListRow] = []
        self._columns = 1
        self._row_count = 0
        self._view: grid.Grid | None = None

    def GetNumberRows(self) -> int:  # noqa: N802 - wx override
        return self._row_count

    def GetNumberCols(self) -> int:  # noqa: N802 - wx override
        return self._columns

    def IsEmptyCell(self, row: int, col: int) -> bool:  # noqa: N802 - wx override
        return self.get_row_for_cell(row, col) is None

    def GetValue(self, row: int, col: int) -> str:  # noqa: N802 - wx override
        item = self.get_row_for_cell(row, col)
        if item is None:
            return ""
        return item.name

    def SetValue(self, row: int, col: int, value: str) -> None:  # noqa: N802 - wx override
        return

    def SetView(self, grid_view: grid.Grid) -> None:  # noqa: N802 - wx override
        super().SetView(grid_view)
        self._view = grid_view

    def update(self, rows: Sequence[IconListRow], columns: int) -> None:
        old_rows = self._row_count
        old_cols = self._columns
        self._rows = list(rows)
        self._columns = max(1, columns)
        self._row_count = self._calculate_row_count()
        self._refresh_view(old_rows, old_cols)

    def get_row_for_cell(self, row: int, col: int) -> IconListRow | None:
        index = row * self._columns + col
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def _calculate_row_count(self) -> int:
        if not self._rows:
            return 0
        return math.ceil(len(self._rows) / self._columns)

    def _refresh_view(self, old_rows: int, old_cols: int) -> None:
        if self._view is None:
            return
        self._view.BeginBatch()
        try:
            if self._columns != old_cols:
                diff = abs(self._columns - old_cols)
                if diff > 0:
                    if self._columns < old_cols:
                        msg = grid.GridTableMessage(
                            self,
                            grid.GRIDTABLE_NOTIFY_COLS_DELETED,
                            self._columns,
                            diff,
                        )
                    else:
                        msg = grid.GridTableMessage(
                            self,
                            grid.GRIDTABLE_NOTIFY_COLS_APPENDED,
                            diff,
                        )
                    self._view.ProcessTableMessage(msg)
            if self._row_count != old_rows:
                diff = abs(self._row_count - old_rows)
                if diff > 0:
                    if self._row_count < old_rows:
                        msg = grid.GridTableMessage(
                            self,
                            grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
                            self._row_count,
                            diff,
                        )
                    else:
                        msg = grid.GridTableMessage(
                            self,
                            grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                            diff,
                        )
                    self._view.ProcessTableMessage(msg)
            msg = grid.GridTableMessage(self, grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
            self._view.ProcessTableMessage(msg)
        finally:
            self._view.EndBatch()
            self._view.ForceRefresh()


class IconCellRenderer(grid.GridCellRenderer):
    def __init__(self, font_lookup: Callable[[str, int], wx.Font | None]) -> None:
        super().__init__()
        self._font_lookup = font_lookup

    def Draw(  # noqa: N802 - wx override
        self,
        grid_view: grid.Grid,
        attr: grid.GridCellAttr,
        dc: wx.DC,
        rect: wx.Rect,
        row: int,
        col: int,
        isSelected: bool,
    ) -> None:
        table = grid_view.GetTable()
        if not isinstance(table, IconGridTable):
            return
        item = table.get_row_for_cell(row, col)
        if isSelected:
            background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            foreground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            background = grid_view.GetBackgroundColour()
            foreground = grid_view.GetForegroundColour()
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(background))
        dc.DrawRectangle(rect)
        if item is None:
            return
        font_size = max(24, int(rect.Height * 0.7))
        font = self._font_lookup(item.font_family, font_size)
        if font is None:
            font = wx.Font(wx.FontInfo(font_size))
        dc.SetFont(font)
        dc.SetTextForeground(foreground)
        dc.DrawLabel(item.glyph, rect, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)

    def GetBestSize(  # noqa: N802 - wx override
        self,
        grid_view: grid.Grid,
        attr: grid.GridCellAttr,
        dc: wx.DC,
        row: int,
        col: int,
    ) -> wx.Size:
        size = grid_view.GetDefaultRowSize()
        return wx.Size(size, size)

    def Clone(self) -> IconCellRenderer:  # noqa: N802 - wx override
        return IconCellRenderer(self._font_lookup)


class IconGrid(grid.Grid):
    def __init__(
        self,
        parent: wx.Window,
        font_lookup: Callable[[str, int], wx.Font | None],
        min_cell: int = 96,
    ) -> None:
        super().__init__(parent, style=wx.BORDER_THEME)
        self._font_lookup = font_lookup
        self._min_cell_size = min_cell
        self._cell_size = min_cell
        self._columns = 1
        self._rows: list[IconListRow] = []
        self._table = IconGridTable()
        self.SetTable(self._table, takeOwnership=True)
        self._configure_appearance()
        self.SetDefaultRenderer(IconCellRenderer(self._font_lookup))
        self.Bind(wx.EVT_SIZE, self._handle_resize)

    def set_rows(self, rows: Sequence[IconListRow]) -> None:
        self.Freeze()
        try:
            self._rows = list(rows)
            self._table.update(self._rows, self._columns)
            self.ClearSelection()
            if self._rows and self._table.GetNumberRows() > 0:
                self.SetGridCursor(0, 0)
        finally:
            self.Thaw()
        self._update_layout()

    def get_selected_row(self) -> IconListRow | None:
        row = self.GetGridCursorRow()
        col = self.GetGridCursorCol()
        if row < 0 or col < 0:
            return None
        item = self._table.get_row_for_cell(row, col)
        return item

    def get_row_count(self) -> int:
        return len(self._rows)

    def _configure_appearance(self) -> None:
        self.EnableEditing(False)
        self.EnableDragColSize(False)
        self.EnableDragRowSize(False)
        self.EnableGridLines(False)
        self.SetRowLabelSize(0)
        self.SetColLabelSize(0)
        self.SetMargins(0, 0)
        self.SetSelectionMode(grid.Grid.SelectCells)
        self.SetDefaultRowSize(self._cell_size, True)
        self.SetDefaultColSize(self._cell_size, True)

    def _handle_resize(self, event: wx.SizeEvent) -> None:
        event.Skip()
        wx.CallAfter(self._update_layout)

    def _update_layout(self) -> None:
        width = max(self.GetClientSize().width, self._min_cell_size)
        desired_columns = max(1, width // self._min_cell_size)
        if desired_columns != self._columns:
            self._columns = desired_columns
            self._table.update(self._rows, self._columns)
        if self._columns == 0:
            return
        cell_size = max(self._min_cell_size, width // self._columns)
        if cell_size != self._cell_size:
            self._cell_size = cell_size
        self.Freeze()
        try:
            self.SetDefaultColSize(self._cell_size, True)
            self.SetDefaultRowSize(self._cell_size, True)
            for col in range(self._columns):
                self.SetColSize(col, self._cell_size)
            for row in range(self._table.GetNumberRows()):
                self.SetRowSize(row, self._cell_size)
        finally:
            self.Thaw()


class IconPickerDialog(wx.Dialog):
    def __init__(
        self,
        fonts: Sequence[tuple[str, str]],
        layers: Sequence[tuple[str, object]],
        parent: wx.Window | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Kicandy Icon Picker",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.fonts = list(fonts)
        self.layers = list(layers)
        self._font_checkboxes: dict[str, wx.CheckBox] = {}
        self._font_render_map: dict[tuple[str, int], wx.Font] = {}
        self._default_preview_font = wx.Font(wx.FontInfo(96))

        self._build_ui()
        self._populate_fonts()
        self._populate_layers()

    def _build_ui(self) -> None:
        self.SetSizeHints(wx.Size(600, 480))
        self.SetSize(wx.Size(800, 600))
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        # Search controls
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search_ctrl = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_ctrl.SetDescriptiveText("Search icons…")
        search_sizer.Add(self.search_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        root_sizer.Add(search_sizer, 0, wx.EXPAND)

        # Font filters
        self.font_box = wx.StaticBox(self, label="Icon Sets")
        font_sizer = wx.StaticBoxSizer(self.font_box, wx.HORIZONTAL)
        self.font_grid = wx.FlexGridSizer(0, 2, 2, 10)
        self.font_grid.AddGrowableCol(0)
        font_sizer.Add(self.font_grid, 1, wx.ALL | wx.EXPAND, 5)
        root_sizer.Add(font_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # Icon list + preview panel
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.icon_grid = IconGrid(self, self._get_font_for_family)
        content_sizer.Add(self.icon_grid, 2, wx.EXPAND | wx.ALL, 5)

        preview_box = wx.StaticBox(self, label="Preview")
        preview_sizer = wx.StaticBoxSizer(preview_box, wx.VERTICAL)
        preview_content = wx.BoxSizer(wx.VERTICAL)
        preview_content.AddStretchSpacer()

        self.preview_glyph = wx.StaticText(
            preview_box,
            label="",
            style=wx.ALIGN_CENTER_HORIZONTAL,
        )
        self.preview_glyph.SetFont(self._default_preview_font)
        preview_content.Add(self.preview_glyph, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 10)

        self.preview_caption = wx.StaticText(
            preview_box,
            label="Select an icon",
            style=wx.ALIGN_CENTER_HORIZONTAL,
        )
        preview_content.Add(self.preview_caption, 0, wx.ALIGN_CENTER_HORIZONTAL)
        preview_content.AddStretchSpacer()

        preview_sizer.Add(preview_content, 1, wx.EXPAND | wx.ALL, 10)
        content_sizer.Add(preview_sizer, 1, wx.EXPAND | wx.ALL, 5)
        root_sizer.Add(content_sizer, 1, wx.EXPAND)

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
        self.add_button = wx.Button(self, id=wx.ID_OK, label="Add Icon")
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
        self.icon_grid.Bind(grid.EVT_GRID_SELECT_CELL, self._handle_grid_selection)
        self.icon_grid.Bind(grid.EVT_GRID_CELL_LEFT_DCLICK, self._handle_icon_activated)
        self.add_button.Bind(wx.EVT_BUTTON, self._handle_add)
        self.Bind(wx.EVT_CLOSE, self._handle_close)

    def _populate_fonts(self) -> None:
        for identifier, label in self.fonts:
            checkbox = wx.CheckBox(self.font_box, label=label)
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

    def _handle_grid_selection(self, event: grid.GridEvent) -> None:
        event.Skip()
        wx.CallAfter(self._update_icon_activated)

    def _handle_icon_activated(self, _: wx.Event) -> None:
        self.on_icon_activated()

    def _handle_add(self, _: wx.CommandEvent) -> None:
        self.on_add_requested()

    def _handle_close(self, event: wx.CloseEvent) -> None:
        self.on_close_requested()
        event.Skip()

    def _update_icon_activated(self) -> None:
        row = self.get_selected_row()
        self.add_button.Enable(row is not None)
        self._update_preview(row)

    def _update_preview(self, row: IconListRow | None) -> None:
        if row is None:
            self.preview_glyph.SetFont(self._default_preview_font)
            self.preview_glyph.SetLabel("")
            self.preview_caption.SetLabel("Select an icon to preview")
            self._refresh_preview_layout()
            return

        preview_font = self._get_font_for_family(row.font_family, 120)
        if preview_font is None:
            preview_font = self._default_preview_font
        self.preview_glyph.SetFont(preview_font)
        self.preview_glyph.SetLabel(row.glyph)
        self.preview_caption.SetLabel(row.name)
        self._refresh_preview_layout()

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

    def get_enabled_fonts(self) -> list[str]:
        result = []
        for font_id, checkbox in self._font_checkboxes.items():
            if checkbox.GetValue():
                result.append(font_id)
        return result

    def set_search_text(self, text: str) -> None:
        self.search_ctrl.SetValue(text)

    def set_layer_value(self, payload: object) -> None:
        for index in range(self.layer_choice.GetCount()):
            if self.layer_choice.GetClientData(index) == payload:
                self.layer_choice.SetSelection(index)
                return

    def get_layer_value(self) -> object | None:
        index = self.layer_choice.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        return self.layer_choice.GetClientData(index)

    def set_rows(self, rows: Sequence[IconListRow]) -> None:
        self.icon_grid.set_rows(rows)
        self._update_icon_activated()
        self.set_status(f"Showing {self.icon_grid.get_row_count()} icons")
        self._update_preview(None)

    def get_selected_row(self) -> IconListRow | None:
        return self.icon_grid.get_selected_row()

    def _get_font_for_family(self, family: str, size: int = 24) -> wx.Font | None:
        key = (family, size)
        if key not in self._font_render_map:
            info = wx.FontInfo(size).FaceName(family)
            font = wx.Font(info)
            if not font.IsOk():
                font = wx.Font(wx.FontInfo(size))
            self._font_render_map[key] = font
        return self._font_render_map[key]

    def _refresh_preview_layout(self) -> None:
        self.preview_glyph.InvalidateBestSize()
        self.preview_caption.InvalidateBestSize()
        sizer = self.preview_glyph.GetContainingSizer()
        if sizer is not None:
            sizer.Layout()
        self.Layout()
