# Kicandy Icon Picker

Kicandy is a KiCad 9 Python action plugin that inserts Material Symbols glyphs as
free silkscreen text. Instead of typing a Unicode character manually, you get a
searchable gallery of icons grouped by font style (Outlined, Rounded, Sharp).

## Features

- Downloads Material Symbols codepoint metadata for the three official styles
  directly from the upstream Google repository and caches it locally.
- Search-as-you-type filtering with live updates as you toggle icon sets.
- Preview icons rendered with the matching system font, so the glyph you place
  matches what you see.
- Layer picker for `F.SilkS` or `B.SilkS` and automatic use of the board's
  silkscreen text defaults.
- Persistent dialog state stored in `kicandy_state.json` so the plugin remembers
  the last search text, enabled icon sets, and chosen layer.

## Usage

1. Load a PCB in KiCad 9 and run the **Insert Icon Text** action.
2. Type to search or toggle the icon family checkboxes. The list updates as you
   type; enabling at least one font is required.
3. Select the target silkscreen layer, highlight an icon, and press **Add Icon**
   (or double-click the row).
4. A `BoardText` item containing the glyph is created and pushed into an
   interactive move session so you can place it immediately.

### Notes

- The plugin expects the Material Symbols fonts to be available on the host OS.
  Only the codepoint metadata is downloaded today, but the metadata in
  `icon_fonts.py` already includes the TTF/WOFF2 URLs so font installation can
  be added later.
- Codepoint files are cached under `cache/` within the plugin directory. Delete
  the folder if you need to force a refresh.
- Dialog state is stored in `kicandy_state.json` next to `kicandy_action.py`.
- If the KiCad scripting sandbox cannot reach GitHub, the dialog will show an
  error and stay empty until connectivity is available.

## Extending

To add new icon sets, append entries to `ICON_FONTS` in `icon_fonts.py`. Provide
the human-readable name, style label, system font family, and download URLs for
both the codepoint file and any font binaries you want to expose later. The
dialog builds its checkbox list directly from this metadata so new sets will
appear automatically.

